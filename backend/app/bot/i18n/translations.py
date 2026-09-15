"""
Comprehensive multilingual translations catalog for Tazala.
Supported languages: Kazakh (kk), Russian (ru), English (en).
"""
from enum import StrEnum


class SupportedLanguage(StrEnum):
    """Supported language codes."""

    KK = "kk"
    RU = "ru"
    EN = "en"


TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Start & Help ---
    "start_welcome": {
        "ru": (
            "🧘 **Добро пожаловать в Tazala!**\n\n"
            "Твой персональный инструмент для **инфо-детокса в Telegram**:\n"
            "• 🧹 Сброс 100k+ непрочитанных за секунды\n"
            "• 📁 Автоматическая сортировка по смарт-папкам\n"
            "• 🎁 Вирусная Wrapped-карточка в стиле Spotify\n"
            "• 🔒 **Zero-Knowledge**: вход через QR, сессия уничтожается сразу после очистки\n\n"
            "Нажмите кнопку ниже, чтобы начать очистку!"
        ),
        "kk": (
            "🧘 **Tazala ботына қош келдіңіз!**\n\n"
            "Telegram желісіндегі **цифрлық тазарту** құралы:\n"
            "• 🧹 100k+ оқылмаған хабарламаны бір сәтте тазарту\n"
            "• 📁 Смарт-папкаларға автоматты түрде реттеу\n"
            "• 🎁 Spotify үлгісіндегі Wrapped-статистика\n"
            "• 🔒 **Zero-Knowledge**: QR арқылы қауіпсіз кіру, сессия тазартудан соң жойылады\n\n"
            "Тазартуды бастау үшін төмендегі батырманы басыңыз!"
        ),
        "en": (
            "🧘 **Welcome to Tazala!**\n\n"
            "Your personal **Telegram info-detox tool**:\n"
            "• 🧹 Clear 100k+ unread messages in seconds\n"
            "• 📁 Automatic sorting into smart folders\n"
            "• 🎁 Spotify-style Wrapped stats card\n"
            "• 🔒 **Zero-Knowledge**: QR-code login, session destroyed right after cleanup\n\n"
            "Click the button below to start decluttering!"
        ),
    },

    # --- Security Info ---
    "security_info": {
        "ru": (
            "🔒 **Как устроена безопасность в Tazala:**\n\n"
            "1. **Вход по QR-коду:** Никаких паролей и номеров телефонов.\n"
            "2. **Оперативная память (RAM):** Строка сессии хранится исключительно в Redis "
            "с TTL 5 минут. Ни одного байта не записывается на диск.\n"
            "3. **Физическое уничтожение:** Сразу после очистки вызывается `log_out()`, "
            "что отзывает ключ авторизации на серверах самого Telegram.\n"
            "4. **Open Source:** Весь код открыт для аудита: "
            "https://github.com/DeadOutside1/tazala\n\n"
            "Готовы навести порядок?"
        ),
        "kk": (
            "🔒 **Tazala қауіпсіздігі қалай жұмыс істейді:**\n\n"
            "1. **QR-кодпен кіру:** Телефон нөмірі мен құпиясөз қажет емес.\n"
            "2. **Жедел жад (RAM):** Сессия тек Redis жадында 5 минут TTL-мен сақталады. "
            "Дискіге ешқандай дерек жазылмайды.\n"
            "3. **Толық жою:** Тазартудан кейін бірден `log_out()` шақырылып, "
            "Telegram серверлеріндегі кілт кері қайтарылады.\n"
            "4. **Open Source:** Код баршаға ашық: "
            "https://github.com/DeadOutside1/tazala\n\n"
            "Тазартуға дайынсыз ба?"
        ),
        "en": (
            "🔒 **How security works in Tazala:**\n\n"
            "1. **QR Login:** No phone numbers or passwords required.\n"
            "2. **RAM-only:** Session strings exist solely in Redis memory "
            "with a 5-minute TTL. Nothing is ever written to disk.\n"
            "3. **Revocation:** Right after cleanup, `log_out()` is called, "
            "invalidating the auth key on Telegram servers.\n"
            "4. **Open Source:** Complete transparency: "
            "https://github.com/DeadOutside1/tazala\n\n"
            "Ready to clear the clutter?"
        ),
    },

    # --- QR Flow ---
    "qr_generating": {
        "ru": "⏳ Генерация защищенного QR-кода...",
        "kk": "⏳ Қауіпсіз QR-код жасалуда...",
        "en": "⏳ Generating secure QR code...",
    },
    "qr_caption": {
        "ru": (
            "📲 **Отсканируйте QR-код для входа:**\n\n"
            "1. Откройте **Telegram** на телефоне\n"
            "2. Перейдите в **Настройки ➔ Устройства ➔ Подключить устройство**\n"
            "3. Наведите камеру на этот QR-код\n\n"
            "_Код обновляется автоматически каждые 25 секунд._"
        ),
        "kk": (
            "📲 **Кіру үшін QR-кодты сканерлеңіз:**\n\n"
            "1. Телефоныңыздан **Telegram** ашыңыз\n"
            "2. **Баптаулар ➔ Құрылғылар ➔ Құрылғыны қосу** бөліміне өтіңіз\n"
            "3. Камераны осы QR-кодқа бағыттаңыз\n\n"
            "_Код әр 25 секунд сайын автоматты түрде жаңарады._"
        ),
        "en": (
            "📲 **Scan QR code to log in:**\n\n"
            "1. Open **Telegram** on your phone\n"
            "2. Go to **Settings ➔ Devices ➔ Link Desktop Device**\n"
            "3. Point your camera at this QR code\n\n"
            "_Code refreshes automatically every 25 seconds._"
        ),
    },
    "qr_expired": {
        "ru": "⏱ Время действия QR-кода истекло. Начните заново: /start",
        "kk": "⏱ QR-кодтың уақыты аяқталды. Қайта бастаңыз: /start",
        "en": "⏱ QR code has expired. Please restart with /start",
    },
    "qr_authenticated": {
        "ru": (
            "✅ **Вы успешно вошли в аккаунт!**\n\n"
            "Сессия защищена в памяти Redis. Нажмите кнопку ниже, чтобы "
            "просканировать завал в Telegram:"
        ),
        "kk": (
            "✅ **Аккаунтқа сәтті кірдіңіз!**\n\n"
            "Сессия Redis жадында қорғалған. Telegram-дағы завалды "
            "бағалау үшін төмендегі батырманы басыңыз:"
        ),
        "en": (
            "✅ **Successfully logged in!**\n\n"
            "Session secured in Redis RAM. Click below to inspect your "
            "Telegram clutter:"
        ),
    },

    # --- 2FA ---
    "two_fa_prompt": {
        "ru": (
            "🔒 **Ваш аккаунт защищен 2FA.**\n\n"
            "Пожалуйста, пришлите ваш облачный пароль сообщением в этот чат.\n"
            "_(Сообщение с паролем будет немедленно удалено из чата)_"
        ),
        "kk": (
            "🔒 **Аккаунтыңызда екі сатылы қорғау (2FA) қосулы.**\n\n"
            "Бұлттық құпиясөзді осы чатқа жіберіңіз.\n"
            "_(Құпиясөз хабарламасы чаттан бірден өшіріледі)_"
        ),
        "en": (
            "🔒 **Your account has Two-Step Verification (2FA) enabled.**\n\n"
            "Please reply with your cloud password.\n"
            "_(Your password message will be deleted immediately for privacy)_"
        ),
    },
    "two_fa_success": {
        "ru": (
            "✅ **Пароль 2FA принят!**\n\n"
            "Вы успешно вошли. Запустите диагностику цифрового завала:"
        ),
        "kk": (
            "✅ **2FA құпиясөзі қабылданды!**\n\n"
            "Сәтті кірдіңіз. Цифрлық тазартуды бастаңыз:"
        ),
        "en": (
            "✅ **2FA password verified!**\n\n"
            "Successfully authenticated. Start your account diagnostics:"
        ),
    },
    "two_fa_error": {
        "ru": "❌ **Ошибка 2FA пароля.** Пожалуйста, отправьте пароль еще раз или начните с /start",
        "kk": "❌ **2FA құпиясөзі қате.** Қайта жіберіп көріңіз немесе /start басыңыз",
        "en": "❌ **Invalid 2FA password.** Please try again or restart with /start",
    },

    # --- Scanning ---
    "scan_starting": {
        "ru": "🔍 **Начинаем сканирование диалогов...**",
        "kk": "🔍 **Диалогтарды тексеру басталды...**",
        "en": "🔍 **Starting account diagnostics scan...**",
    },
    "scan_progress": {
        "ru": "🔍 Просканировано **{scanned}** диалогов...",
        "kk": "🔍 **{scanned}** диалог тексерілді...",
        "en": "🔍 Scanned **{scanned}** dialogs...",
    },
    "scan_report": {
        "ru": (
            "📊 **Результаты диагностики аккаунта:**\n\n"
            "💬 Всего диалогов: **{total_dialogs}**\n"
            "🔴 Непрочитанных сообщений: **{total_unread}**\n"
            "🗑 Неактивных каналов/групп: **{dead_total}** ({dead_percentage}%)\n"
            "📁 В архиве: **{archived_count}**\n\n"
            "🏆 **Главные источники завала:**\n{top_list}\n\n"
            "Выберите желаемый сценарий очистки:"
        ),
        "kk": (
            "📊 **Аккаунтты тексеру нәтижесі:**\n\n"
            "💬 Барлық диалогтар: **{total_dialogs}**\n"
            "🔴 Оқылмаған хабарламалар: **{total_unread}**\n"
            "🗑 Белсенді емес арна/топтар: **{dead_total}** ({dead_percentage}%)\n"
            "📁 Мұрағатта (архивте): **{archived_count}**\n\n"
            "🏆 **Негізгі завал көздері:**\n{top_list}\n\n"
            "Тазарту нұсқасын таңдаңыз:"
        ),
        "en": (
            "📊 **Account Diagnostic Results:**\n\n"
            "💬 Total dialogs: **{total_dialogs}**\n"
            "🔴 Unread messages: **{total_unread}**\n"
            "🗑 Inactive channels/groups: **{dead_total}** ({dead_percentage}%)\n"
            "📁 In archive: **{archived_count}**\n\n"
            "🏆 **Top clutter sources:**\n{top_list}\n\n"
            "Select your cleanup mode:"
        ),
    },
    "no_unread_chats": {
        "ru": "Нет непрочитанных чатов 🎉",
        "kk": "Оқылмаған чаттар жоқ 🎉",
        "en": "No unread chats 🎉",
    },
    "action_already_running": {
        "ru": "⏳ Операция уже выполняется, пожалуйста, подождите.",
        "kk": "⏳ Бұл әрекет қазір орындалуда, күте тұрыңыз.",
        "en": "⏳ Operation is already in progress, please wait.",
    },

    # --- Cleaning ---
    "clean_starting": {
        "ru": "🧹 **Наводим Дзен... Начинаем очистку.**",
        "kk": "🧹 **Дзен күйіне өтудеміз... Тазарту басталды.**",
        "en": "🧹 **Entering Zen mode... Starting cleanup.**",
    },
    "clean_progress": {
        "ru": "🧹 **{message}** ({current}/{total})...",
        "kk": "🧹 **{message}** ({current}/{total})...",
        "en": "🧹 **{message}** ({current}/{total})...",
    },
    "wrapped_caption": {
        "ru": (
            "🧘 **Дзен достигнут!**\n\n"
            "Твой архетип: **{archetype}**\n"
            "🧹 Очищено сообщений: **{messages}**\n"
            "⏳ Сэкономлено: **{hours} ч.**\n"
            "⭐ Zen Score: **{score} / 100**\n\n"
            "Поделитесь карточкой с друзьями или завершите сессию:"
        ),
        "kk": (
            "🧘 **Дзенге қол жеткіздіңіз!**\n\n"
            "Сіздің архетипіңіз: **{archetype}**\n"
            "🧹 Тазартылған хабарламалар: **{messages}**\n"
            "⏳ Үнемделген уақыт: **{hours} сағ.**\n"
            "⭐ Zen Score: **{score} / 100**\n\n"
            "Нәтижені достарыңызбен бөлісіңіз немесе сессияны жабыңыз:"
        ),
        "en": (
            "🧘 **Zen state achieved!**\n\n"
            "Your Archetype: **{archetype}**\n"
            "🧹 Messages cleared: **{messages}**\n"
            "⏳ Time saved: **{hours} hrs**\n"
            "⭐ Zen Score: **{score} / 100**\n\n"
            "Share your card or end your session:"
        ),
    },

    # --- Session & Logout ---
    "logout_confirmed": {
        "ru": (
            "🔒 **Сессия успешно уничтожена!**\n\n"
            "• Ключ авторизации отозван на серверах Telegram (`log_out`)\n"
            "• Временная сессия удалена из памяти Redis\n\n"
            "Ваш аккаунт в полной безопасности. Чтобы начать заново — отправьте /start."
        ),
        "kk": (
            "🔒 **Сессия сәтті жойылды!**\n\n"
            "• Авторизация кілті Telegram серверлерінен өшірілді (`log_out`)\n"
            "• Сессия Redis жадынан түгел тазартылды\n\n"
            "Аккаунтыңыз толық қауіпсіздікте. Қайта бастау үшін: /start."
        ),
        "en": (
            "🔒 **Session completely destroyed!**\n\n"
            "• Authorization key revoked on Telegram servers (`log_out`)\n"
            "• Ephemeral session purged from Redis RAM\n\n"
            "Your account is 100% safe. Send /start to begin a new session."
        ),
    },
    "session_not_found": {
        "ru": "Сессия не найдена или устарела. Начните с /start.",
        "kk": "Сессия табылмады немесе мерзімі өтті. /start арқылы қайта бастаңыз.",
        "en": "Session not found or expired. Please restart with /start.",
    },

    # --- Keyboard Buttons ---
    "btn_start_auth": {
        "ru": "🔑 Войти по QR-коду",
        "kk": "🔑 QR-кодпен кіру",
        "en": "🔑 Log in with QR code",
    },
    "btn_security": {
        "ru": "ℹ️ О безопасности (Zero-Knowledge)",
        "kk": "ℹ️ Қауіпсіздік туралы (Zero-Knowledge)",
        "en": "ℹ️ Security (Zero-Knowledge)",
    },
    "btn_choose_lang": {
        "ru": "🌐 Тіл / Язык / Language",
        "kk": "🌐 Тіл / Язык / Language",
        "en": "🌐 Language / Тіл / Язык",
    },
    "btn_run_scan": {
        "ru": "🔍 Запустить диагностику аккаунта",
        "kk": "🔍 Аккаунтты тексеруді бастау",
        "en": "🔍 Start Account Diagnostics",
    },
    "btn_clean_all": {
        "ru": "🧹 Навести Дзен ({unread} непрочитанных + папки)",
        "kk": "🧹 Дзенге өту ({unread} оқылмаған + папкалар)",
        "en": "🧹 Achieve Zen ({unread} unread + folders)",
    },
    "btn_clean_read_only": {
        "ru": "⚙️ Только сбросить непрочитанные",
        "kk": "⚙️ Тек оқылмағандарды белгілеу",
        "en": "⚙️ Clear unread messages only",
    },
    "btn_clean_folders_only": {
        "ru": "📁 Только создать смарт-папки",
        "kk": "📁 Тек смарт-папкаларды құру",
        "en": "📁 Create smart folders only",
    },
    "btn_logout": {
        "ru": "🔒 Выйти и удалить сессию",
        "kk": "🔒 Шығу және сессияны жою",
        "en": "🔒 Log out & destroy session",
    },
    "btn_share": {
        "ru": "📲 Поделиться в Stories / Чатах",
        "kk": "📲 Достармен / Stories-те бөлісу",
        "en": "📲 Share to Stories / Chats",
    },
    "btn_back": {
        "ru": "⬅️ Назад",
        "kk": "⬅️ Артқа",
        "en": "⬅️ Back",
    },
    "lang_changed": {
        "ru": "✅ Язык переключен на русский!",
        "kk": "✅ Тіл қазақшаға ауыстырылды!",
        "en": "✅ Language changed to English!",
    },
    "select_language": {
        "ru": "🌐 Выберите язык интерфейса:",
        "kk": "🌐 Тілді таңдаңыз:",
        "en": "🌐 Choose your language:",
    },

    # --- Phone Auth ---
    "btn_phone_auth": {
        "ru": "📱 Войти по номеру телефона",
        "kk": "📱 Телефон нөмірімен кіру",
        "en": "📱 Log in with phone number",
    },
    "phone_prompt": {
        "ru": (
            "📱 **Введите ваш номер телефона** в международном формате:\n\n"
            "Пример: `+77001234567`\n\n"
            "_Вы получите 5-значный код подтверждения в Telegram от аккаунта 777000._"
        ),
        "kk": (
            "📱 **Телефон нөміріңізді** халықаралық форматта жазыңыз:\n\n"
            "Мысалы: `+77001234567`\n\n"
            "_Telegram-дағы 777000 аккаунтынан 5 санды растау коды келеді._"
        ),
        "en": (
            "📱 **Enter your phone number** in international format:\n\n"
            "Example: `+77001234567`\n\n"
            "_You will receive a 5-digit verification code in Telegram from account 777000._"
        ),
    },
    "sms_code_prompt": {
        "ru": (
            "🔑 **Введите код подтверждения,** который пришёл в Telegram "
            "(от аккаунта 777000):\n\n"
            "_Код будет удалён из чата после обработки._"
        ),
        "kk": (
            "🔑 **Telegram-нан келген растау кодын жазыңыз** "
            "(777000 аккаунтынан):\n\n"
            "_Код өңделгеннен кейін чаттан өшіріледі._"
        ),
        "en": (
            "🔑 **Enter the verification code** sent via Telegram "
            "(from account 777000):\n\n"
            "_The code will be deleted from chat after processing._"
        ),
    },
    "phone_auth_success": {
        "ru": (
            "✅ **Вы успешно вошли по номеру телефона!**\n\n"
            "Сессия защищена в памяти Redis. Нажмите кнопку ниже, чтобы "
            "просканировать завал в Telegram:"
        ),
        "kk": (
            "✅ **Телефон нөмірі арқылы сәтті кірдіңіз!**\n\n"
            "Сессия Redis жадында қорғалған. Telegram-дағы завалды "
            "бағалау үшін төмендегі батырманы басыңыз:"
        ),
        "en": (
            "✅ **Successfully logged in with phone number!**\n\n"
            "Session secured in Redis RAM. Click below to inspect your "
            "Telegram clutter:"
        ),
    },
    "phone_auth_error": {
        "ru": "❌ **Ошибка входа.** Проверьте код и попробуйте снова, или начните с /start",
        "kk": "❌ **Кіру қатесі.** Кодты тексеріп, қайта жіберіңіз немесе /start басыңыз",
        "en": "❌ **Login error.** Please check the code and try again, or restart with /start",
    },
    "phone_invalid_format": {
        "ru": "❌ Номер должен начинаться с `+` и содержать цифры. Пример: `+77001234567`",
        "kk": "❌ Нөмір `+` белгісінен басталуы тиіс. Мысалы: `+77001234567`",
        "en": "❌ Number must start with `+` and contain digits. Example: `+77001234567`",
    },
    "btn_deeplink_login": {
        "ru": "📲 Войти в один клик",
        "kk": "📲 Бір басуда кіру",
        "en": "📲 One-click login",
    },
    "btn_main_menu": {
        "ru": "🏠 В главное меню",
        "kk": "🏠 Басты мәзір",
        "en": "🏠 Main menu",
    },
    "menu_btn_main": {
        "ru": "🏠 Главное меню",
        "kk": "🏠 Басты мәзір",
        "en": "🏠 Main menu",
    },
    "menu_btn_scan": {
        "ru": "⚡ Начать очистку",
        "kk": "⚡ Тазартуды бастау",
        "en": "⚡ Start cleaner",
    },
    "menu_btn_lang": {
        "ru": "🌐 Сменить язык",
        "kk": "🌐 Тілді ауыстыру",
        "en": "🌐 Change language",
    },
    "menu_btn_help": {
        "ru": "🔒 Безопасность",
        "kk": "🔒 Қауіпсіздік",
        "en": "🔒 Security",
    },
    "btn_resend_code": {
        "ru": "🔄 Отправить код повторно",
        "kk": "🔄 Кодты қайта жіберу",
        "en": "🔄 Resend code",
    },
    "btn_switch_to_qr": {
        "ru": "📲 Войти в 1 клик (без кода)",
        "kk": "📲 1 басуда кіру (кодсыз)",
        "en": "📲 1-click login (no code)",
    },
    "code_resent_alert": {
        "ru": "✅ Запрос на отправку кода повторен!",
        "kk": "✅ Қайта жіберу сұрауы жіберілді!",
        "en": "✅ Verification code resent!",
    },

    # --- Folder Selection ---
    "folder_selection_title": {
        "ru": (
            "📁 **Выберите категории для смарт-папок:**\n\n"
            "Нажимайте на кнопки, чтобы включить (✅) или выключить (⬜) категории.\n"
            "Затем нажмите «Создать папки»."
        ),
        "kk": (
            "📁 **Смарт-папка категорияларын таңдаңыз:**\n\n"
            "Батырмаларды басып, категорияларды қосыңыз (✅) немесе өшіріңіз (⬜).\n"
            "Содан кейін «Папкаларды құру» батырмасын басыңыз."
        ),
        "en": (
            "📁 **Select smart folder categories:**\n\n"
            "Tap buttons to enable (✅) or disable (⬜) categories.\n"
            "Then press «Create folders»."
        ),
    },
    "btn_confirm_folders": {
        "ru": "🧹 Создать выбранные папки",
        "kk": "🧹 Таңдалған папкаларды құру",
        "en": "🧹 Create selected folders",
    },
    "btn_select_all_folders": {
        "ru": "☑️ Все",
        "kk": "☑️ Барлық",
        "en": "☑️ All",
    },
    "btn_deselect_all_folders": {
        "ru": "🔲 Сброс",
        "kk": "🔲 Тазарту",
        "en": "🔲 None",
    },
}

# Archetype metadata for all languages
ARCHETYPES = {
    "digital_monk": {
        "title": {
            "ru": "Цифровой монах",
            "kk": "Цифрлық монах",
            "en": "Digital Monk",
        },
        "description": {
            "ru": "Абсолютный дзен и контроль над входящими.",
            "kk": "Толық дзен және кіріс хаттарды мінсіз басқару.",
            "en": "Absolute zen and complete control over inboxes.",
        },
    },
    "info_collector": {
        "title": {
            "ru": "Инфо-коллекционер",
            "kk": "Инфо-коллекционер",
            "en": "Info Collector",
        },
        "description": {
            "ru": "Любишь читать, но лента победила.",
            "kk": "Оқығанды жақсы көресіз, бірақ ақпарат тасқыны басым түсті.",
            "en": "Love to read, but the feed overwhelmed you.",
        },
    },
    "chaos_lord": {
        "title": {
            "ru": "Повелитель хаоса",
            "kk": "Хаос әміршісі",
            "en": "Chaos Lord",
        },
        "description": {
            "ru": "Красный бейдж Telegram управлял твоей жизнью.",
            "kk": "Telegram-ның қызыл белгішесі өміріңізді басқарды.",
            "en": "The red Telegram badge was controlling your life.",
        },
    },
    "digital_hoarder": {
        "title": {
            "ru": "Цифровой плюшкин",
            "kk": "Цифрлық плюшкин",
            "en": "Digital Hoarder",
        },
        "description": {
            "ru": "Копил каналы годами. Пришло время отпустить.",
            "kk": "Жылдар бойы арналарды жинадыңыз. Босататын уақыт келді.",
            "en": "Hoarded channels for years. Time to let go.",
        },
    },
}
