"""
Tests for the Interactive Telegram Folder Manager (CleanerService, Keyboards, and Bot Handlers).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.types import DialogFilter, DialogFilterDefault, InputPeerChat, InputPeerUser

from app.bot.handlers import (
    cb_folder_mgr_confirm_delete,
    cb_folder_mgr_delete_prompt,
    cb_folder_mgr_list,
    msg_folder_mgr_rename_input,
)
from app.bot.keyboards import (
    get_folder_actions_kb,
    get_folder_delete_confirm_kb,
    get_folders_list_kb,
)
from app.bot.states import FolderManagerSG
from app.cleaner.schemas import UserFolderInfo
from app.cleaner.service import CleanerService

# --- 1. Service Layer Tests (get_user_folders, rename_folder, delete_folder) ---


@pytest.mark.asyncio
async def test_get_user_folders_parsing():
    """Test retrieving and parsing Telegram dialog filters into UserFolderInfo objects."""
    service = CleanerService()
    mock_client = AsyncMock()

    # Create dummy filters: one default (id=0), two custom filters
    default_filter = MagicMock(spec=DialogFilterDefault)
    default_filter.id = 0

    filter1 = MagicMock(spec=DialogFilter)
    filter1.id = 2
    filter1.title = "Work"
    filter1.emoticon = "💼"
    filter1.pinned_peers = [MagicMock(spec=InputPeerUser)]
    filter1.include_peers = [MagicMock(spec=InputPeerChat), MagicMock(spec=InputPeerUser)]

    filter2 = MagicMock(spec=DialogFilter)
    filter2.id = 5
    filter2.title = "Crypto"
    filter2.emoticon = None
    filter2.pinned_peers = []
    filter2.include_peers = [MagicMock(spec=InputPeerChat)]

    mock_client.side_effect = lambda req: (
        [default_filter, filter1, filter2] if isinstance(req, GetDialogFiltersRequest) else None
    )

    folders = await service.get_user_folders(mock_client)

    assert len(folders) == 2
    assert folders[0].id == 2
    assert folders[0].title == "Work"
    assert folders[0].emoticon == "💼"
    assert folders[0].chats_count == 3  # 1 pinned + 2 included

    assert folders[1].id == 5
    assert folders[1].title == "Crypto"
    assert folders[1].emoticon is None
    assert folders[1].chats_count == 1


@pytest.mark.asyncio
async def test_rename_folder_success():
    """Test renaming a folder with valid title <= 12 characters."""
    service = CleanerService()
    mock_client = AsyncMock()

    existing_filter = MagicMock(spec=DialogFilter)
    existing_filter.id = 3
    existing_filter.title = "Old Name"
    existing_filter.emoticon = "📁"
    existing_filter.pinned_peers = []
    existing_filter.include_peers = [MagicMock()]

    mock_client.side_effect = lambda req: (
        [existing_filter] if isinstance(req, GetDialogFiltersRequest) else True
    )

    renamed = await service.rename_folder(mock_client, folder_id=3, new_title="New Name")

    assert renamed.id == 3
    assert renamed.title == "New Name"
    title_text = (
        existing_filter.title.text
        if hasattr(existing_filter.title, "text")
        else existing_filter.title
    )
    assert title_text == "New Name"

    # Verify UpdateDialogFilterRequest was called
    called_requests = [call.args[0] for call in mock_client.call_args_list]
    update_reqs = [r for r in called_requests if isinstance(r, UpdateDialogFilterRequest)]
    assert len(update_reqs) == 1
    assert update_reqs[0].id == 3
    assert update_reqs[0].filter == existing_filter


@pytest.mark.asyncio
async def test_rename_folder_length_validation():
    """Test that renaming a folder with > 12 characters raises ValueError."""
    service = CleanerService()
    mock_client = AsyncMock()

    with pytest.raises(ValueError, match="exceeds 12 characters limit"):
        await service.rename_folder(mock_client, folder_id=1, new_title="ThisTitleIsWayTooLong")


@pytest.mark.asyncio
async def test_rename_folder_not_found():
    """Test that attempting to rename a non-existent folder raises ValueError."""
    service = CleanerService()
    mock_client = AsyncMock()

    mock_client.side_effect = lambda req: (
        [] if isinstance(req, GetDialogFiltersRequest) else None
    )

    with pytest.raises(ValueError, match="Folder with id 99 not found"):
        await service.rename_folder(mock_client, folder_id=99, new_title="ValidTitle")


@pytest.mark.asyncio
async def test_delete_folder_calls_update_dialog_filter_none():
    """Test that deleting a folder invokes UpdateDialogFilterRequest with filter=None."""
    service = CleanerService()
    mock_client = AsyncMock()

    await service.delete_folder(mock_client, folder_id=4)

    called_requests = [call.args[0] for call in mock_client.call_args_list]
    assert len(called_requests) == 1
    req = called_requests[0]
    assert isinstance(req, UpdateDialogFilterRequest)
    assert req.id == 4
    assert req.filter is None


# --- 2. Keyboards Tests ---


def test_folders_list_keyboard_structure():
    """Test get_folders_list_kb generates correct buttons for folders and actions."""
    folders = [
        UserFolderInfo(id=2, title="News", emoticon="📰", chats_count=5),
        UserFolderInfo(id=4, title="Work", emoticon="💼", chats_count=12),
    ]

    kb = get_folders_list_kb(folders, lang="ru")
    assert len(kb.inline_keyboard) == 3  # 2 folders + 1 control row

    assert kb.inline_keyboard[0][0].callback_data == "folder_mgr:view:2"
    assert "News" in kb.inline_keyboard[0][0].text
    assert "5" in kb.inline_keyboard[0][0].text

    assert kb.inline_keyboard[1][0].callback_data == "folder_mgr:view:4"
    assert "Work" in kb.inline_keyboard[1][0].text
    assert "12" in kb.inline_keyboard[1][0].text

    # Bottom control row
    bottom_row = kb.inline_keyboard[2]
    assert len(bottom_row) == 2
    assert bottom_row[0].callback_data == "folder_mgr:add_preset"
    assert bottom_row[1].callback_data == "back_to_start"


def test_folder_actions_keyboard_structure():
    """Test get_folder_actions_kb contains rename, delete, and back buttons."""
    kb = get_folder_actions_kb(folder_id=7, lang="en")
    assert len(kb.inline_keyboard) == 3
    assert kb.inline_keyboard[0][0].callback_data == "folder_mgr:rename:7"
    assert kb.inline_keyboard[1][0].callback_data == "folder_mgr:delete_prompt:7"
    assert kb.inline_keyboard[2][0].callback_data == "folder_mgr:list"


def test_folder_delete_confirm_keyboard_structure():
    """Test get_folder_delete_confirm_kb contains confirm and cancel buttons."""
    kb = get_folder_delete_confirm_kb(folder_id=9, lang="kk")
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "folder_mgr:confirm_delete:9"
    assert kb.inline_keyboard[1][0].callback_data == "folder_mgr:view:9"


# --- 3. Handler & FSM Tests ---


@pytest.mark.asyncio
async def test_folder_mgr_list_no_session():
    """Test that opening folder manager without active session warns user."""
    mock_cb = AsyncMock()
    mock_cb.from_user.id = 12345
    mock_cb.message.answer = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {}

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    await cb_folder_mgr_list(mock_cb, mock_state, redis=mock_redis, lang="ru")

    mock_cb.message.answer.assert_awaited_once()
    called_text = mock_cb.message.answer.call_args[0][0]
    assert "авторизоваться" in called_text


@pytest.mark.asyncio
async def test_folder_mgr_rename_input_too_long():
    """Test that entering a folder name > 12 characters rejects and prompts to shorten."""
    mock_msg = AsyncMock()
    mock_msg.text = "SuperLongFolderName"
    mock_msg.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"rename_folder_id": 3}

    await msg_folder_mgr_rename_input(mock_msg, mock_state, lang="ru")

    mock_msg.answer.assert_awaited_once()
    assert "Слишком длинное название" in mock_msg.answer.call_args[0][0]
    mock_state.clear.assert_not_awaited()


@pytest.mark.asyncio
async def test_folder_mgr_rename_input_success():
    """Test that valid input renames folder and updates list view."""
    mock_msg = AsyncMock()
    mock_msg.text = "ShortName"
    mock_msg.from_user.id = 99999
    mock_msg.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {
        "session_id": "test-sid",
        "rename_folder_id": 3,
    }

    mock_redis = AsyncMock()
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)

    renamed_info = UserFolderInfo(id=3, title="ShortName", emoticon=None, chats_count=2)
    all_folders = [renamed_info]

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.CleanerService") as mock_cs_cls,
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss.load.return_value = mock_client
        mock_ss_cls.return_value = mock_ss

        mock_cs = AsyncMock()
        mock_cs.rename_folder.return_value = renamed_info
        mock_cs.get_user_folders.return_value = all_folders
        mock_cs_cls.return_value = mock_cs

        await msg_folder_mgr_rename_input(mock_msg, mock_state, redis=mock_redis, lang="ru")

        mock_cs.rename_folder.assert_awaited_once_with(
            mock_client, folder_id=3, new_title="ShortName"
        )
        mock_state.set_state.assert_awaited_once_with(FolderManagerSG.viewing_list)
        mock_msg.answer.assert_awaited_once()
        assert "ShortName" in mock_msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_folder_mgr_delete_prompt():
    """Test delete prompt displays warning with target title and confirm buttons."""
    mock_cb = AsyncMock()
    mock_cb.data = "folder_mgr:delete_prompt:4"
    mock_cb.from_user.id = 88888
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"folder_title": "TestFolder"}

    mock_redis = AsyncMock()

    await cb_folder_mgr_delete_prompt(mock_cb, mock_state, redis=mock_redis, lang="ru")

    mock_state.set_state.assert_awaited_once_with(FolderManagerSG.confirm_delete)
    mock_state.update_data.assert_awaited_once_with(delete_folder_id=4)
    mock_cb.message.edit_text.assert_awaited_once()
    assert "TestFolder" in mock_cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_folder_mgr_confirm_delete():
    """Test confirming delete removes folder via service and refreshes list."""
    mock_cb = AsyncMock()
    mock_cb.data = "folder_mgr:confirm_delete:5"
    mock_cb.from_user.id = 77777
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {"session_id": "del-sid"}

    mock_redis = AsyncMock()
    mock_client = AsyncMock()
    mock_client.is_connected = MagicMock(return_value=True)

    with (
        patch("app.bot.handlers.SessionStore") as mock_ss_cls,
        patch("app.bot.handlers.CleanerService") as mock_cs_cls,
    ):
        mock_ss = AsyncMock()
        mock_ss.exists.return_value = True
        mock_ss.load.return_value = mock_client
        mock_ss_cls.return_value = mock_ss

        mock_cs = AsyncMock()
        mock_cs.get_user_folders.return_value = []
        mock_cs_cls.return_value = mock_cs

        await cb_folder_mgr_confirm_delete(mock_cb, mock_state, redis=mock_redis, lang="ru")

        mock_cs.delete_folder.assert_awaited_once_with(mock_client, folder_id=5)
        mock_state.set_state.assert_awaited_once_with(FolderManagerSG.viewing_list)
        mock_cb.message.edit_text.assert_awaited_once()
        assert "удалена" in mock_cb.message.edit_text.call_args[0][0]
