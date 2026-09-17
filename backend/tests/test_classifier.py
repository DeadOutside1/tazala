"""
Unit tests for SmartClassifier module:
- Regex whole-word boundaries (anti-substring false positive prevention)
- Specificity-weighted confidence scoring and cutoff
- Mutually exclusive folder assignment (1 chat = strictly 1 folder, 0 duplicates)
- Priority isolation for Dead/Zombie chats (🗑)
- Priority isolation for Personal user chats (💬)
- Peer uniqueness and candidate limit enforcement
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest

from app.cleaner.classifier import SmartClassifier
from app.cleaner.schemas import FolderRule
from app.cleaner.service import CleanerService, get_smart_folder_presets
from app.scanner.schemas import ChatStatus, ChatType, DialogInfo


def test_regex_boundaries_anti_substring():
    """
    Test whole-word regex matching prevents substring false positives:
    - 'Bitcoin Hodl' must NOT match 'it'
    - 'Красивые девушки' must NOT match 'dev'
    - 'IT & Development News' must match 'it' and 'dev'
    """
    # 1. Negative checks (substring false positives)
    assert not SmartClassifier.match_keyword("Bitcoin Hodl", "it")
    assert not SmartClassifier.match_keyword("Capital Bank", "it")
    assert not SmartClassifier.match_keyword("посетить мероприятие", "it")
    assert not SmartClassifier.match_keyword("Красивые девушки", "dev")
    assert not SmartClassifier.match_keyword("девушки и мода", "dev")

    # 2. Positive checks (isolated words)
    assert SmartClassifier.match_keyword("IT & Development News", "it")
    assert SmartClassifier.match_keyword("IT & Development News", "dev")
    assert SmartClassifier.match_keyword("Python dev community", "dev")
    assert SmartClassifier.match_keyword("Новости IT индустрии", "it")

    # 3. Multi-word phrase matching
    assert SmartClassifier.match_keyword(
        "Modern Machine Learning in Practice",
        "machine learning",
    )
    assert SmartClassifier.match_keyword(
        "Главные новости мира сегодня",
        "новости мира",
    )
    assert not SmartClassifier.match_keyword(
        "Learning machines guide",
        "machine learning",
    )

    # 4. Edge cases
    assert not SmartClassifier.match_keyword("", "dev")
    assert not SmartClassifier.match_keyword("Dev chat", "")
    assert not SmartClassifier.match_keyword("Dev chat", "   ")


def test_confidence_scoring_and_weights():
    """
    Test score calculation:
    - Single-word match gives base +1.0
    - Multi-word phrase match gives base +2.0
    - Multipliers: Finance (1.3x), Study (1.2x), Work (1.1x), News (1.0x)
    - Cutoff < 1.0 yields 0.0
    """
    finance_rule = FolderRule(
        title="💰 Финансы",
        emoji="💰",
        keywords=["крипта", "btc", "трейдинг", "crypto trading"],
    )
    study_rule = FolderRule(
        title="📚 Обучение",
        emoji="📚",
        keywords=["курс", "python course"],
    )
    work_rule = FolderRule(
        title="💼 Работа",
        emoji="💼",
        keywords=["dev", "remote work"],
    )
    news_rule = FolderRule(
        title="📰 Новости",
        emoji="📰",
        keywords=["новости", "world news"],
    )

    # Single-word match with multipliers
    assert SmartClassifier.score_dialog_for_rule("Канал про крипта", finance_rule) == round(
        1.0 * 1.3, 2
    )
    assert SmartClassifier.score_dialog_for_rule("Интенсивный курс", study_rule) == round(
        1.0 * 1.2, 2
    )
    assert SmartClassifier.score_dialog_for_rule("Python dev channel", work_rule) == round(
        1.0 * 1.1, 2
    )
    assert SmartClassifier.score_dialog_for_rule("Свежие новости", news_rule) == round(
        1.0 * 1.0, 2
    )

    # Multi-word phrase match gives base 2.0
    assert SmartClassifier.score_dialog_for_rule(
        "Best Crypto Trading Group", finance_rule
    ) == round(2.0 * 1.3, 2)
    assert SmartClassifier.score_dialog_for_rule(
        "Best Python Course Online", study_rule
    ) == round(2.0 * 1.2, 2)
    assert SmartClassifier.score_dialog_for_rule(
        "Senior Remote Work Offers", work_rule
    ) == round(2.0 * 1.1, 2)

    # Multiple matching keywords accumulate base scores:
    # 'dev' (+1) + 'remote work' (+2) = 3 * 1.1 = 3.3
    assert SmartClassifier.score_dialog_for_rule(
        "Remote Work for Dev", work_rule
    ) == round(3.0 * 1.1, 2)

    # No match yields 0.0
    assert SmartClassifier.score_dialog_for_rule("Случайный чат обо всём", finance_rule) == 0.0


def test_exclusive_distribution_no_duplicates():
    """
    Test channel with keywords in 3 categories is assigned exclusively to the best folder:
    'IT Новости и Криптотрейдинг' contains:
      - 'it' (Work, 1.1x)
      - 'новости' (News, 1.0x)
      - 'криптотрейдинг' (Finance, 1.3x)
    Must be assigned ONLY to '💰 Финансы', NEVER duplicated into Work or News.
    """
    now = datetime.now(UTC)
    presets = get_smart_folder_presets("ru")

    multi_theme_dialog = DialogInfo(
        id=777,
        title="IT Новости и Криптотрейдинг",
        type=ChatType.CHANNEL,
        unread_count=5,
        last_message_date=now,
        status=ChatStatus.ACTIVE,
    )

    classified = SmartClassifier.classify_dialogs([multi_theme_dialog], presets)

    # Must be in Finance
    assert any(d.id == 777 for d in classified.get("💰 Финансы", []))

    # Must NOT be in Work or News
    assert not any(d.id == 777 for d in classified.get("💼 Работа", []))
    assert not any(d.id == 777 for d in classified.get("📰 Новости", []))

    # Verify total assignment count across all folders is exactly 1
    total_assigned = sum(
        sum(1 for d in folder_chats if d.id == 777)
        for folder_chats in classified.values()
    )
    assert total_assigned == 1


def test_dead_chat_isolation():
    """
    Test inactive / dead channels are isolated to 🗑 Мёртвые with highest priority,
    even if their title contains keywords matching other active rules.
    """
    now = datetime.now(UTC)
    presets = get_smart_folder_presets("ru")

    dead_dialog = DialogInfo(
        id=101,
        title="Python Dev & Code Channel",
        type=ChatType.CHANNEL,
        unread_count=0,
        last_message_date=now,
        status=ChatStatus.DEAD,
    )
    zombie_dialog = DialogInfo(
        id=102,
        title="Crypto Finance Daily",
        type=ChatType.CHANNEL,
        unread_count=0,
        last_message_date=now,
        status=ChatStatus.ZOMBIE,
    )

    classified = SmartClassifier.classify_dialogs([dead_dialog, zombie_dialog], presets)

    dead_folder_chats = [d.id for d in classified.get("🗑 Мёртвые", [])]
    assert 101 in dead_folder_chats
    assert 102 in dead_folder_chats

    # Neither chat should be in Work or Finance
    work_folder_chats = [d.id for d in classified.get("💼 Работа", [])]
    finance_folder_chats = [d.id for d in classified.get("💰 Финансы", [])]
    assert 101 not in work_folder_chats
    assert 102 not in finance_folder_chats


def test_personal_chat_isolation():
    """
    Test personal user chats (ChatType.USER) are routed strictly to 💬 Личные,
    even if contact's name contains keywords (e.g. 'Денис Dev').
    """
    now = datetime.now(UTC)
    presets = get_smart_folder_presets("ru")

    user_dialog = DialogInfo(
        id=301,
        title="Денис Dev",
        type=ChatType.USER,
        unread_count=1,
        last_message_date=now,
        status=ChatStatus.ACTIVE,
    )

    classified = SmartClassifier.classify_dialogs([user_dialog], presets)

    personal_chats = [d.id for d in classified.get("💬 Личные", [])]
    work_chats = [d.id for d in classified.get("💼 Работа", [])]

    assert 301 in personal_chats
    assert 301 not in work_chats


@pytest.mark.asyncio
async def test_unique_peers_no_duplicates_in_service():
    """
    Test CleanerService.create_smart_folders ensures:
    - No duplicate peer IDs inside include_peers for any folder
    - Maximum limit of 100 peers per folder
    """
    service = CleanerService()
    now = datetime.now(UTC)

    # Create 120 work dialogs
    dialogs = [
        DialogInfo(
            id=1000 + i,
            title=f"Work Dev Chat {i}",
            type=ChatType.CHANNEL,
            unread_count=0,
            last_message_date=now,
            status=ChatStatus.ACTIVE,
        )
        for i in range(120)
    ]

    mock_client = AsyncMock()
    recorded_requests: list[UpdateDialogFilterRequest] = []

    async def fake_invoke(req):
        if isinstance(req, GetDialogFiltersRequest):
            resp = MagicMock()
            resp.filters = []
            return resp
        if isinstance(req, UpdateDialogFilterRequest):
            recorded_requests.append(req)
            return True
        return None

    mock_client.side_effect = fake_invoke
    # Mock get_input_entity returning an InputPeer-like mock with an id attribute
    mock_client.get_input_entity = AsyncMock(
        side_effect=lambda chat_id: MagicMock(id=chat_id, user_id=chat_id)
    )

    # Provide a peer_map with deliberate potential duplicate resolution
    peer_map = {d.id: MagicMock(id=d.id) for d in dialogs}

    with patch("asyncio.sleep", new_callable=AsyncMock):
        created = await service.create_smart_folders(
            mock_client,
            dialogs,
            peer_map=peer_map,
            selected_emojis={"💼"},
        )

    assert "💼 Работа" in created
    assert len(recorded_requests) == 1
    work_filter_req = recorded_requests[0]
    peers = work_filter_req.filter.include_peers

    # Check max limit 100
    assert len(peers) <= 100

    # Check peer uniqueness (no duplicate peer IDs)
    peer_ids = [p.id for p in peers]
    assert len(peer_ids) == len(set(peer_ids))
