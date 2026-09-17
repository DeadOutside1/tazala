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
            "📲 **Вход в аккаунт Tazala:**\n\n"
            "• **На телефоне:** Нажмите кнопку ниже «📲 Войти в один клик» для мгновенного входа!\n"
            "• **Или отсканируйте QR-код:** Настройки ➔ Устройства ➔ Подключить устройство.\n\n"
            "_Код обновляется автоматически каждые 25 секунд._"
        ),
        "kk": (
            "📲 **Tazala аккаунтына кіру:**\n\n"
            "• **Телефонда:** Бірден кіру үшін төмендегі «📲 Бір басуда кіру» батырмасын басыңыз!\n"
            "• **Немесе QR-кодты сканерлеңіз:** Баптаулар ➔ Құрылғылар ➔ Құрылғыны қосу.\n\n"
            "_Код әр 25 секунд сайын автоматты түрде жаңарады._"
        ),
        "en": (
            "📲 **Log in to Tazala:**\n\n"
            "• **On mobile:** Tap the «📲 One-click login» button below for instant login!\n"
            "• **Or scan QR code:** Settings ➔ Devices ➔ Link Desktop Device.\n\n"
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
            "🔑 **Введите код подтверждения:**\n\n"
            "_Код будет удалён из чата после обработки._"
        ),
        "kk": (
            "🔑 **Растау кодын енгізіңіз:**\n\n"
            "_Код өңделгеннен кейін чаттан өшіріледі._"
        ),
        "en": (
            "🔑 **Enter the verification code:**\n\n"
            "_The code will be deleted from chat after processing._"
        ),
    },
    "sms_code_prompt_app": {
        "ru": (
            "📱 **Код отправлен в официальное приложение Telegram (от 777000)!**\n\n"
            "Проверьте чат с официальным аккаунтом **«Telegram»** на телефоне или компьютере.\n\n"
            "💡 _Если код не пришёл в 777000, проверьте другие устройства, где открыт Telegram, "
            "или нажмите «📲 Войти в 1 клик» ниже._\n\n"
            "_Введите полученный код:_"
        ),
        "kk": (
            "📱 **Растау коды ресми Telegram қосымшасына жіберілді (777000 аккаунтынан)!**\n\n"
            "Телефоныңыздағы немесе компьютеріңіздегі ресми **«Telegram»** чатын тексеріңіз.\n\n"
            "💡 _Егер код келмесе, төмендегі «📲 1 басуда кіру» батырмасын басыңыз._\n\n"
            "_Келген кодты енгізіңіз:_"
        ),
        "en": (
            "📱 **Code sent to your official Telegram app (from 777000)!**\n\n"
            "Please check the chat with official **«Telegram»** on your phone or PC.\n\n"
            "💡 _If you don't see it, check other devices where Telegram is active, "
            "or tap «📲 1-click login» below._\n\n"
            "_Enter the received code:_"
        ),
    },
    "sms_code_prompt_sms": {
        "ru": (
            "📩 **Внимание: Telegram отправил код по SMS!**\n\n"
            "Код отправлен в **обычном SMS-сообщении** на номер `{phone}` "
            "(НЕ в чат 777000 в Telegram!).\n\n"
            "Пожалуйста, проверьте папку входящих **SMS-сообщений** на телефоне.\n\n"
            "_Введите полученный код:_"
        ),
        "kk": (
            "📩 **Назар аударыңыз: Telegram кодты SMS арқылы жіберді!**\n\n"
            "Код `{phone}` нөміріне **қарапайым SMS-хабарлама** ретінде жіберілді "
            "(Telegram 777000 чатына емес!).\n\n"
            "Телефоныңыздағы **кіріс SMS** хабарламаларын тексеріңіз.\n\n"
            "_Келген кодты енгізіңіз:_"
        ),
        "en": (
            "📩 **Notice: Telegram sent the code via SMS!**\n\n"
            "The code was sent as a standard **SMS text message** to `{phone}` "
            "(NOT in Telegram chat 777000!).\n\n"
            "Please check your phone's **SMS inbox**.\n\n"
            "_Enter the received code:_"
        ),
    },
    "sms_code_prompt_email": {
        "ru": (
            "📧 **Telegram отправил код на ваш Email!**\n\n"
            "Проверьте входящие письма (и папку «Спам») на вашей почте, "
            "привязанной к Telegram.\n\n"
            "_Введите полученный код:_"
        ),
        "kk": (
            "📧 **Telegram кодты электрондық поштаңызға жіберді!**\n\n"
            "Telegram-ға тіркелген поштаңыздың кіріс хаттарын тексеріңіз.\n\n"
            "_Келген кодты енгізіңіз:_"
        ),
        "en": (
            "📧 **Telegram sent the code to your Email!**\n\n"
            "Please check your inbox (and Spam folder) of the email "
            "linked to your Telegram account.\n\n"
            "_Enter the received code:_"
        ),
    },
    "sms_code_prompt_call": {
        "ru": (
            "📞 **Telegram выполняет звонок на номер {phone}!**\n\n"
            "Кодом подтверждения являются последние 5 цифр входящего номера.\n\n"
            "_Введите полученный код:_"
        ),
        "kk": (
            "📞 **Telegram {phone} нөміріне қоңырау шалуда!**\n\n"
            "Кіріс нөмірдің соңғы 5 цифры растау коды болып табылады.\n\n"
            "_Келген кодты енгізіңіз:_"
        ),
        "en": (
            "📞 **Telegram is calling {phone}!**\n\n"
            "The verification code is the last 5 digits of the incoming number.\n\n"
            "_Enter the received code:_"
        ),
    },
    "resend_code_unavailable": {
        "ru": (
            "⏳ Все каналы доставки Telegram для этого номера временно исчерпаны. "
            "Подождите 10-15 минут или используйте моментальный вход в 1 клик."
        ),
        "kk": (
            "⏳ Telegram-ның осы нөмір үшін барлық жіберу арналары уақытша шектелді. "
            "10-15 минут күтіңіз немесе 1 басуда кіру батырмасын қолданыңыз."
        ),
        "en": (
            "⏳ All Telegram delivery channels for this number have been temporarily exhausted. "
            "Please wait 10-15 minutes or use the instant 1-click login."
        ),
    },
    "code_display_label": {
        "ru": "Код:",
        "kk": "Код:",
        "en": "Code:",
    },
    "code_numpad_tip": {
        "ru": "👇 _Нажимайте кнопки с цифрами ниже для безопасного ввода кода._",
        "kk": "👇 _Кодты қауіпсіз енгізу үшін төмендегі сандарды басыңыз._",
        "en": "👇 _Tap the number buttons below for secure code entry._",
    },
    "code_verifying": {
        "ru": "⏳ Проверяем код {code}...",
        "kk": "⏳ {code} коды тексерілуде...",
        "en": "⏳ Verifying code {code}...",
    },
    "phone_code_expired_tip": {
        "ru": (
            "❌ **Telegram аннулировал этот код из соображений безопасности.**\n\n"
            "Telegram автоматически блокирует коды, отправленные текстом в чат.\n\n"
            "👉 Нажмите **«🔄 Отправить код повторно»** и введите новый код "
            "**кнопками с цифрами ниже** 👇"
        ),
        "kk": (
            "❌ **Telegram қауіпсіздік мақсатында бұл кодты жойды.**\n\n"
            "Telegram чатқа мәтін ретінде жіберілген кодтарды бұғаттайды.\n\n"
            "👉 **«🔄 Кодты қайта жіберу»** басып, жаңа кодты "
            "**төмендегі сандар батырмаларымен** енгізіңіз 👇"
        ),
        "en": (
            "❌ **Telegram invalidated this code for security reasons.**\n\n"
            "Telegram automatically revokes codes sent as chat text.\n\n"
            "👉 Tap **«🔄 Resend code»** and enter the new code "
            "using the **number buttons below** 👇"
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
    "clean_completed_report": {
        "ru": (
            "✨ **Очистка успешно завершена!**\n\n"
            "• ✉️ Отмечено прочитанными: **{marked}**\n"
            "• 📁 Создано/обновлено папок: **{folders}**\n\n"
            "Сессия остаётся **активной**. Вы можете настроить другие папки "
            "или запустить повторный анализ.\n\n"
            "Когда закончите, нажмите **«🚪 Выйти и удалить сессию»**, чтобы отозвать "
            "доступ на серверах Telegram и получить итоговую карточку для Stories! 📲"
        ),
        "kk": (
            "✨ **Тазарту сәтті аяқталды!**\n\n"
            "• ✉️ Оқылған деп белгіленді: **{marked}**\n"
            "• 📁 Құрылған/жаңартылған папкалар: **{folders}**\n\n"
            "Сессия **белсенді** күйде қалады. Басқа папкаларды баптауға "
            "немесе қайта талдау жасауға болады.\n\n"
            "Аяқтаған соң, Telegram серверлеріндегі кілтті өшіру және "
            "Stories карточкасын алу үшін **«🚪 Шығу және сессияны жою»** батырмасын басыңыз! 📲"
        ),
        "en": (
            "✨ **Cleanup completed successfully!**\n\n"
            "• ✉️ Marked as read: **{marked}**\n"
            "• 📁 Created/updated folders: **{folders}**\n\n"
            "Your session remains **active**. You can configure additional folders "
            "or run a re-scan.\n\n"
            "When you are finished, tap **«🚪 Log out & destroy session»** to revoke access "
            "on Telegram servers and receive your Wrapped social card! 📲"
        ),
    },
    "wrapped_logout_caption": {
        "ru": (
            "🔒 **Сессия успешно уничтожена!**\n"
            "Ключ авторизации отозван на серверах Telegram (Zero-Knowledge).\n\n"
            "🧘 **Твой Дзен в Telegram:**\n"
            "• Архетип: **{archetype}**\n"
            "• Очищено сообщений: **{messages}**\n"
            "• Сэкономлено: **{hours} ч**\n"
            "• Дзен-индекс: **{score}/100**\n\n"
            "Поделись своим результатом в Instagram Stories или с друзьями 👇"
        ),
        "kk": (
            "🔒 **Сессия сәтті жойылды!**\n"
            "Telegram серверлеріндегі кілт кері қайтарылды (Zero-Knowledge).\n\n"
            "🧘 **Telegram-дағы Дзеніңіз:**\n"
            "• Архетип: **{archetype}**\n"
            "• Тазартылған хабарламалар: **{messages}**\n"
            "• Үнемделді: **{hours} сағ**\n"
            "• Дзен-индекс: **{score}/100**\n\n"
            "Нәтижеңізді Instagram Stories-те немесе достарыңызбен бөлісіңіз 👇"
        ),
        "en": (
            "🔒 **Session terminated and destroyed!**\n"
            "Authorization key revoked on Telegram servers (Zero-Knowledge).\n\n"
            "🧘 **Your Telegram Zen:**\n"
            "• Archetype: **{archetype}**\n"
            "• Cleared messages: **{messages}**\n"
            "• Saved: **{hours} hrs**\n"
            "• Zen Index: **{score}/100**\n\n"
            "Share your achievement on Instagram Stories or with friends 👇"
        ),
    },
    "btn_rescan": {
        "ru": "🔄 Повторное сканирование",
        "kk": "🔄 Қайта сканерлеу",
        "en": "🔄 Re-scan account",
    },
    "btn_continue_session": {
        "ru": "⚡ Продолжить работу (активная сессия)",
        "kk": "⚡ Жұмысты жалғастыру (белсенді сессия)",
        "en": "⚡ Continue session (active)",
    },
    # --- Admin & Feedback ---
    "admin_access_denied": {
        "ru": "⛔ **Доступ запрещен.**\n\nЭта команда доступна только администраторам бота.",
        "kk": "⛔ **Рұқсат берілмеген.**\n\nБұл команда тек бот әкімшілеріне қолжетімді.",
        "en": "⛔ **Access denied.**\n\nThis command is restricted to bot administrators.",
    },
    "btn_admin_panel": {
        "ru": "👑 Админ-панель",
        "kk": "👑 Әкімші панелі",
        "en": "👑 Admin Panel",
    },
    "btn_refresh_stats": {
        "ru": "🔄 Обновить статистику",
        "kk": "🔄 Статистиканы жаңарту",
        "en": "🔄 Refresh Stats",
    },
    "btn_recent_reviews": {
        "ru": "📝 Отзывы пользователей",
        "kk": "📝 Қолданушылар пікірлері",
        "en": "📝 User Reviews",
    },
    "btn_leave_feedback": {
        "ru": "⭐ Оставить отзыв",
        "kk": "⭐ Пікір қалдыру",
        "en": "⭐ Leave a Review",
    },
    "btn_skip_comment": {
        "ru": "➡️ Пропустить комментарий",
        "kk": "➡️ Пікірді өткізіп жіберу",
        "en": "➡️ Skip comment",
    },
    "feedback_prompt": {
        "ru": (
            "⭐ **Оцените работу Tazala:**\n\n"
            "Насколько бот помог вам навести порядок в Telegram? "
            "Выберите оценку от 1 до 5 звезд:"
        ),
        "kk": (
            "⭐ **Tazala жұмысын бағалаңыз:**\n\n"
            "Бот Telegram-ды реттеуге қаншалықты көмектесті? "
            "1-ден 5-ке дейін бағалаңыз:"
        ),
        "en": (
            "⭐ **Rate your experience with Tazala:**\n\n"
            "How well did Tazala help you declutter Telegram? "
            "Please choose 1 to 5 stars:"
        ),
    },
    "feedback_stars_saved": {
        "ru": (
            "⭐ Вы поставили оценку **{rating}/5**!\n\n"
            "💬 Напишите короткий отзыв или пожелание в этот чат "
            "(или нажмите кнопку «Пропустить комментарий»):"
        ),
        "kk": (
            "⭐ Сіз **{rating}/5** бағасын қойдыңыз!\n\n"
            "💬 Чатқа қысқаша пікір немесе ұсынысыңызды жазыңыз "
            "(немесе «Пікірді өткізіп жіберу» батырмасын басыңыз):"
        ),
        "en": (
            "⭐ You rated **{rating}/5**!\n\n"
            "💬 Send a short review or suggestion in this chat "
            "(or click «Skip comment»):"
        ),
    },
    "feedback_saved_thanks": {
        "ru": (
            "🙏 **Спасибо за ваш отзыв!**\n\n"
            "Ваша оценка и комментарий помогают нам делать Tazala ещё лучше и удобнее."
        ),
        "kk": (
            "🙏 **Пікіріңізге рақмет!**\n\n"
            "Сіздің бағаңыз бен пікіріңіз Tazala-ны одан әрі жақсартуға көмектеседі."
        ),
        "en": (
            "🙏 **Thank you for your feedback!**\n\n"
            "Your review helps us make Tazala even better."
        ),
    },
    "btn_folder_manager": {
        "ru": "📁 Мои папки",
        "kk": "📁 Менің бумаларым",
        "en": "📁 My Folders",
    },
    "btn_add_smart_folder": {
        "ru": "✨ Создать умные папки",
        "kk": "✨ Ақылды бумалар жасау",
        "en": "✨ Create Smart Folders",
    },
    "btn_rename_folder": {
        "ru": "✏️ Переименовать папку",
        "kk": "✏️ Бума атауын өзгерту",
        "en": "✏️ Rename Folder",
    },
    "btn_delete_folder": {
        "ru": "🗑️ Удалить папку",
        "kk": "🗑️ Буманы жою",
        "en": "🗑️ Delete Folder",
    },
    "btn_confirm_delete": {
        "ru": "🗑️ Да, удалить папку",
        "kk": "🗑️ Иә, буманы жою",
        "en": "🗑️ Yes, delete folder",
    },
    "btn_cancel": {
        "ru": "❌ Отмена",
        "kk": "❌ Бас тарту",
        "en": "❌ Cancel",
    },
    "btn_back_to_folders": {
        "ru": "🔙 Назад к папкам",
        "kk": "🔙 Бумаларға оралу",
        "en": "🔙 Back to Folders",
    },
    "folder_mgr_title": {
        "ru": (
            "📁 **Управление папками Telegram**\n\n"
            "Всего папок: **{count}** из 10 (лимит Telegram).\n\n"
            "Нажмите на нужную папку для просмотра, переименования или удаления:"
        ),
        "kk": (
            "📁 **Telegram бумаларын басқару**\n\n"
            "Барлық бума: **{count}** / 10 (Telegram шегі).\n\n"
            "Көру, атауын өзгерту немесе жою үшін керекті буманы таңдаңыз:"
        ),
        "en": (
            "📁 **Telegram Folder Manager**\n\n"
            "Total folders: **{count}** of 10 (Telegram limit).\n\n"
            "Click a folder to view, rename, or delete it:"
        ),
    },
    "folder_view_info": {
        "ru": (
            "📂 **Папка: {title}**\n\n"
            "💬 Количество чатов: **{chats_count}**\n\n"
            "Выберите необходимое действие:"
        ),
        "kk": (
            "📂 **Бума: {title}**\n\n"
            "💬 Чаттар саны: **{chats_count}**\n\n"
            "Қажетті әрекетті таңдаңыз:"
        ),
        "en": (
            "📂 **Folder: {title}**\n\n"
            "💬 Chats count: **{chats_count}**\n\n"
            "Choose an action:"
        ),
    },
    "folder_rename_prompt": {
        "ru": (
            "✏️ **Переименование папки**\n\n"
            "Отправьте новое название для этой папки в ответном сообщении.\n\n"
            "⚠️ *Максимум 12 символов (ограничение Telegram).*"
        ),
        "kk": (
            "✏️ **Бума атауын өзгерту**\n\n"
            "Осы бума үшін жаңа атауды хабарлама ретінде жіберіңіз.\n\n"
            "⚠️ *Ең көбі 12 таңба (Telegram шектеуі).*"
        ),
        "en": (
            "✏️ **Rename Folder**\n\n"
            "Send the new folder name as a reply in this chat.\n\n"
            "⚠️ *Maximum 12 characters (Telegram limit).*"
        ),
    },
    "folder_rename_too_long": {
        "ru": (
            "❌ **Слишком длинное название!**\n\n"
            "Вы ввели {len} символов. Telegram разрешает не более 12 символов в названии папки.\n"
            "Пожалуйста, отправьте более короткое название:"
        ),
        "kk": (
            "❌ **Атауы тым ұзын!**\n\n"
            "Сіз {len} таңба енгіздіңіз. Telegram бума атауында ең көбі 12 таңбаға рұқсат береді.\n"
            "Қысқарақ атау жіберіңіз:"
        ),
        "en": (
            "❌ **Title too long!**\n\nYou entered {len} characters. "
            "Telegram allows a maximum of 12 characters for folder names.\n"
            "Please send a shorter title:"
        ),
    },
    "folder_rename_success": {
        "ru": "✅ Папка успешно переименована в **«{title}»**!",
        "kk": "✅ Бума атауы сәтті **«{title}»** болып өзгертілді!",
        "en": "✅ Folder successfully renamed to **«{title}»**!",
    },
    "folder_delete_warn": {
        "ru": (
            "⚠️ **Удаление папки «{title}»**\n\n"
            "Вы действительно хотите удалить эту папку?\n\n"
            "*Сами чаты и сообщения удалены НЕ будут — удалится только сама вкладка-папка.*"
        ),
        "kk": (
            "⚠️ **«{title}» бумасын жою**\n\n"
            "Бұл буманы шынымен жойғыңыз келе ме?\n\n"
            "*Чаттар мен хабарламалар жойылмайды — тек бума қойындысы жойылады.*"
        ),
        "en": (
            "⚠️ **Delete Folder «{title}»**\n\n"
            "Are you sure you want to delete this folder?\n\n"
            "*Chats and messages will NOT be deleted — only the folder tab will be removed.*"
        ),
    },
    "folder_delete_success": {
        "ru": "🗑️ Папка успешно удалена.",
        "kk": "🗑️ Бума сәтті жойылды.",
        "en": "🗑️ Folder successfully deleted.",
    },
    "folder_not_found": {
        "ru": "❌ Папка не найдена или уже была удалена.",
        "kk": "❌ Бума табылмады немесе әлдеқашан жойылған.",
        "en": "❌ Folder not found or has already been deleted.",
    },
    "folder_mgr_no_session": {
        "ru": (
            "⚠️ Для управления папками необходимо авторизоваться в Telegram. "
            "Пожалуйста, войдите через меню."
        ),
        "kk": (
            "⚠️ Бумаларды басқару үшін Telegram-ға кіру қажет. "
            "Басты мәзір арқылы кіріңіз."
        ),
        "en": (
            "⚠️ You need to log in to Telegram to manage folders. "
            "Please log in via the menu."
        ),
    },
    "btn_share_tg": {
        "ru": "✈️ Отправить другу в Telegram",
        "kk": "✈️ Telegram-да досыңа жіберу",
        "en": "✈️ Send to Telegram friend",
    },
    "btn_share_whatsapp": {
        "ru": "🟢 Поделиться в WhatsApp",
        "kk": "🟢 WhatsApp-та бөлісу",
        "en": "🟢 Share on WhatsApp",
    },
    "btn_share_stories": {
        "ru": "📸 В Stories (Instagram / Telegram)",
        "kk": "📸 Stories-ке салу (Instagram / TG)",
        "en": "📸 Post to Stories (Instagram / TG)",
    },
    "btn_copy_bot_link": {
        "ru": "📋 Скопировать ссылку для стикера",
        "kk": "📋 Стикер үшін сілтемені көшіру",
        "en": "📋 Copy link for sticker",
    },
    "btn_open_instagram": {
        "ru": "📸 Открыть Instagram",
        "kk": "📸 Instagram-ды ашу",
        "en": "📸 Open Instagram",
    },
    "btn_back_to_card": {
        "ru": "🔙 Назад к карточке",
        "kk": "🔙 Карточкаға оралу",
        "en": "🔙 Back to card",
    },
    "wrapped_stories_guide": {
        "ru": (
            "📸 **Как опубликовать карточку в Stories:**\n\n"
            "1️⃣ **Сохраните карточку выше в галерею** "
            "(нажмите на картинку ➔ три точки в углу ➔ «Сохранить в галерею» 📲).\n"
            "2️⃣ **Откройте Stories** в Instagram или Telegram.\n"
            "3️⃣ **Выберите сохраненную картинку Tazala** из галереи.\n"
            "4️⃣ **Добавьте стикер-ссылку** на бота "
            "(нажмите кнопку ниже, чтобы скопировать ссылку):\n"
            "`https://t.me/tazala_app_bot`\n\n"
            "✨ *Пусть друзья тоже оценят свой цифровой Дзен!* 🧘"
        ),
        "kk": (
            "📸 **Карточканы Stories-ке қалай салу керек:**\n\n"
            "1️⃣ **Жоғарыдағы карточканы галереяға сақтаңыз** "
            "(суретті басыңыз ➔ бұрыштағы үш нүкте ➔ «Галереяға сақтау» 📲).\n"
            "2️⃣ **Instagram немесе Telegram Stories-ті ашыңыз**.\n"
            "3️⃣ Галереядан **сақталған Tazala суретін таңдаңыз**.\n"
            "4️⃣ Боттың **сілтеме-стикерін қосыңыз** "
            "(көшіру үшін төмендегі батырманы басыңыз):\n"
            "`https://t.me/tazala_app_bot`\n\n"
            "✨ *Достарыңыз да өздерінің цифрлық Дзенін бағаласын!* 🧘"
        ),
        "en": (
            "📸 **How to post your card to Stories:**\n\n"
            "1️⃣ **Save the card above to your gallery** "
            "(tap the image ➔ three dots ➔ «Save to gallery» 📲).\n"
            "2️⃣ **Open Stories** in Instagram or Telegram.\n"
            "3️⃣ **Select the saved Tazala card** from your gallery.\n"
            "4️⃣ **Add a link sticker** to the bot "
            "(tap button below to copy the link):\n"
            "`https://t.me/tazala_app_bot`\n\n"
            "✨ *Inspire your friends to achieve digital Zen too!* 🧘"
        ),
    },
    "btn_leave_dead_channels": {
        "ru": "💣 Отписаться от {count} мёртвых каналов",
        "kk": "💣 Барлық {count} өлі каналдан шығу",
        "en": "💣 Leave all {count} dead channels",
    },
    "btn_confirm_leave_dead": {
        "ru": "💣 Да, отписаться от всех {count}",
        "kk": "💣 Иә, барлық {count}-ден шығу",
        "en": "💣 Yes, leave all {count}",
    },
    "dead_leave_prompt_warn": {
        "ru": (
            "⚠️ **Внимание: Необратимое действие!**\n\n"
            "Найдено **{count}** каналов и групп, заброшенных более 6–12 месяцев.\n"
            "Вы действительно хотите отписаться от них одним кликом?\n"
            "(Вам не придётся делать это вручную)"
        ),
        "kk": (
            "⚠️ **Назар аударыңыз: Қайтарылмайтын әрекет!**\n\n"
            "6–12 айдан астам уақыт бойы белсенді емес **{count}** канал мен топ табылды.\n"
            "Олардың барлығынан бір басумен шыққыңыз келе ме?\n"
            "(Қолмен шығудың қажеті болмайды)"
        ),
        "en": (
            "⚠️ **Warning: Irreversible Action!**\n\n"
            "Found **{count}** channels and groups inactive for over 6–12 months.\n"
            "Are you sure you want to leave all of them in one click?\n"
            "(You won't have to do it manually)"
        ),
    },
    "dead_leave_starting": {
        "ru": "💣 Начинаю массовую отписку от мёртвых каналов...",
        "kk": "💣 Өлі каналдардан жаппай шығу басталуда...",
        "en": "💣 Starting mass unsubscribe from dead channels...",
    },
    "dead_leave_progress": {
        "ru": "💣 Отписка: покинуто {current} из {total} ({title})...",
        "kk": "💣 Шығу барысы: {total}-ден {current} өшірілді ({title})...",
        "en": "💣 Leaving: {current} of {total} left ({title})...",
    },
    "dead_leave_completed": {
        "ru": (
            "🎉 **Готово!** Вы успешно отписались от **{count}** мёртвых каналов.\n"
            "Ваш Telegram стал намного легче! 🧘"
        ),
        "kk": (
            "🎉 **Дайын!** Сіз **{count}** өлі каналдан сәтті шықтыңыз.\n"
            "Telegram тізіміңіз біршама тазарды! 🧘"
        ),
        "en": (
            "🎉 **Done!** You have successfully left **{count}** dead channels.\n"
            "Your Telegram is much cleaner now! 🧘"
        ),
    },
    "dead_choice_prompt": {
        "ru": (
            "💣 **Найдено {count} заброшенных каналов и групп.**\n\n"
            "Как вы хотите поступить?"
        ),
        "kk": (
            "💣 **{count} белсенді емес канал мен топ табылды.**\n\n"
            "Қалай жалғастырғыңыз келеді?"
        ),
        "en": (
            "💣 **Found {count} inactive channels and groups.**\n\n"
            "How would you like to proceed?"
        ),
    },
    "btn_dead_all_fast": {
        "ru": "⚡ Отписаться от всех {count} разом",
        "kk": "⚡ Барлық {count}-ден бірден шығу",
        "en": "⚡ Leave all {count} at once",
    },
    "btn_dead_browse_manual": {
        "ru": "📋 Выбрать из списка вручную",
        "kk": "📋 Тізімнен қолмен таңдау",
        "en": "📋 Select from list manually",
    },
    "dead_browse_title": {
        "ru": (
            "📋 **Список заброшенных каналов**\n"
            "Стр. {page}/{total_pages} • Отмечено: **{selected} из {total}**\n\n"
            "_Нажмите на канал, чтобы снять или поставить отметку:_"
        ),
        "kk": (
            "📋 **Белсенді емес каналдар тізімі**\n"
            "Бет {page}/{total_pages} • Таңдалғаны: **{selected} / {total}**\n\n"
            "_Белгіні қою немесе алып тастау үшін каналды басыңыз:_"
        ),
        "en": (
            "📋 **Inactive Channels List**\n"
            "Page {page}/{total_pages} • Selected: **{selected} of {total}**\n\n"
            "_Tap a channel to toggle selection:_"
        ),
    },
    "btn_dead_select_page": {
        "ru": "🔘 Выбрать страницу",
        "kk": "🔘 Бетті таңдау",
        "en": "🔘 Select page",
    },
    "btn_dead_deselect_page": {
        "ru": "⚪ Снять страницу",
        "kk": "⚪ Бетті алып тастау",
        "en": "⚪ Deselect page",
    },
    "btn_dead_delete_selected": {
        "ru": "🗑 Отписаться от выбранных ({count})",
        "kk": "🗑 Таңдалған {count} каналдан шығу",
        "en": "🗑 Leave selected ({count})",
    },
    "dead_none_selected_alert": {
        "ru": "⚠️ Не выбрано ни одного канала для отписки!",
        "kk": "⚠️ Шығу үшін бірде-бір канал таңдалмаған!",
        "en": "⚠️ No channels selected to leave!",
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
