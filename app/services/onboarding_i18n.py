"""
Teksty interfejsu strony pracownika (onboarding) w 5 językach.
Języki: pl (bazowy), en, uk (ukraiński, w UI jako UA), es, ru.
Brak klucza w danym języku = tekst polski.

Tłumaczenia treści modułów są w bazie (onboarding_module_translations),
tu tylko stałe elementy interfejsu. Wersje EN/UK/ES/RU na bazie projektu z Claude Design (23.09.2026),
dopasowane do logowania numerem telefonu i datą urodzenia (bez SMS).
"""

LANG_LABELS = {"pl": "PL", "en": "EN", "uk": "UA", "es": "ES", "ru": "RU"}
LANG_NAMES = {"pl": "Polski", "en": "English", "uk": "Українська", "es": "Español", "ru": "Русский"}
SUPPORTED_LANGS = ["pl", "en", "uk", "es", "ru"]

# Języki widoczne w przełączniku na stronie pracownika (Albert 23.09: wszystkie od razu).
# Treść modułu bez tłumaczenia w bazie pokazuje się po polsku.
READY_LANGS = ["pl", "en", "uk", "es", "ru"]

STRINGS = {
    "pl": {
        "kicker": "Portal pracownika",
        "h_light": "Witaj w zespole.",
        "h_bold": "Zacznijmy wprowadzenie.",
        "login_intro": "Zaloguj się numerem telefonu i kodem, którym jest dzień i miesiąc Twojego urodzenia.",
        "phone_label": "Numer telefonu",
        "phone_placeholder": "+48 600 000 000",
        "code_label": "Kod: dzień i miesiąc urodzenia",
        "code_placeholder": "0803",
        "code_hint": "4 cyfry: dzień i miesiąc, np. 0803 dla 8 marca.",
        "login_button": "Zaloguj się",
        "login_error": "Nie znaleźliśmy takiego numeru albo kod jest błędny. Sprawdź i spróbuj ponownie.",
        "login_no_segment": "Twoje wprowadzenie nie jest jeszcze gotowe. Skontaktuj się z koordynatorem.",
        "help": "Problem z logowaniem?",
        "s1": "Zaloguj się",
        "s2": "Przejdź moduły",
        "s3": "Potwierdź i gotowe",
        "logout": "Wyloguj",
        "hi": "Cześć",
        "progress": "{acked} z {total} ukończone",
        "meta": "{modules} · ok. {min} min",
        "meta_short": "{modules}",
        "start_intro": "Przejdź moduły po kolei i potwierdź każdy na końcu. Możesz przerwać i wrócić później.",
        "acked": "Potwierdzono",
        "now": "Teraz",
        "locked": "Po ukończeniu poprzedniego",
        "start_button": "Zaczynam",
        "continue_button": "Kontynuuj",
        "done_button": "Zobacz podsumowanie",
        "back_to_list": "Wróć do listy",
        "module_of": "Moduł {i} z {n}",
        "ack_button": "Przeczytałem i rozumiem",
        "ack_note": "Potwierdzenie zapiszemy z datą i godziną.",
        "acked_at": "Potwierdzono {when}",
        "next_module": "Następny moduł",
        "open_pdf": "Otwórz",
        "locked_message": "Najpierw potwierdź poprzedni moduł.",
        "done_title": "Gotowe",
        "done_intro": "Wszystkie moduły potwierdzone. Do zobaczenia w pracy.",
        "done_first_day": "Twój pierwszy dzień",
        "done_back": "Wróć do modułów",
        "minutes_short": "min",
        "modules_1": "1 moduł", "modules_few": "{n} moduły", "modules_many": "{n} modułów",
    },
    "en": {
        "kicker": "Employee portal",
        "h_light": "Welcome to the team.",
        "h_bold": "Let's get you started.",
        "login_intro": "Sign in with your phone number and your code: the day and month of your birth.",
        "phone_label": "Phone number",
        "phone_placeholder": "+48 600 000 000",
        "code_label": "Code: day and month of birth",
        "code_placeholder": "0803",
        "code_hint": "4 digits: day and month, e.g. 0803 for 8 March.",
        "login_button": "Sign in",
        "login_error": "We could not find this number or the code is wrong. Check and try again.",
        "login_no_segment": "Your introduction is not ready yet. Please contact your coordinator.",
        "help": "Trouble signing in?",
        "s1": "Sign in",
        "s2": "Go through the modules",
        "s3": "Confirm and you're done",
        "logout": "Log out",
        "hi": "Hi",
        "progress": "{acked} of {total} completed",
        "meta": "{modules} · approx. {min} min",
        "meta_short": "{modules}",
        "start_intro": "Go through the modules in order and confirm each one at the end. You can stop and come back later.",
        "acked": "Confirmed",
        "now": "Now",
        "locked": "Unlocks after the previous one",
        "start_button": "Start",
        "continue_button": "Continue",
        "done_button": "See summary",
        "back_to_list": "Back to list",
        "module_of": "Module {i} of {n}",
        "ack_button": "I have read and understood",
        "ack_note": "We will save your confirmation with the date and time.",
        "acked_at": "Confirmed {when}",
        "next_module": "Next module",
        "open_pdf": "Open",
        "locked_message": "Confirm the previous module first.",
        "done_title": "All done",
        "done_intro": "Every module is confirmed. See you at work.",
        "done_first_day": "Your first day",
        "done_back": "Back to modules",
        "minutes_short": "min",
        "modules_1": "1 module", "modules_few": "{n} modules", "modules_many": "{n} modules",
    },
    "es": {
        "kicker": "Portal del trabajador",
        "h_light": "Bienvenido al equipo.",
        "h_bold": "Empecemos la introducción.",
        "login_intro": "Inicia sesión con tu número de teléfono y tu código: el día y el mes de tu nacimiento.",
        "phone_label": "Número de teléfono",
        "phone_placeholder": "+48 600 000 000",
        "code_label": "Código: día y mes de nacimiento",
        "code_placeholder": "0803",
        "code_hint": "4 dígitos: día y mes, p. ej. 0803 para el 8 de marzo.",
        "login_button": "Iniciar sesión",
        "login_error": "No encontramos ese número o el código es incorrecto. Revísalo e inténtalo de nuevo.",
        "login_no_segment": "Tu introducción aún no está lista. Contacta con tu coordinador.",
        "help": "¿Problemas para entrar?",
        "s1": "Inicia sesión",
        "s2": "Completa los módulos",
        "s3": "Confirma y listo",
        "logout": "Salir",
        "hi": "Hola",
        "progress": "{acked} de {total} completados",
        "meta": "{modules} · aprox. {min} min",
        "meta_short": "{modules}",
        "start_intro": "Completa los módulos en orden y confirma cada uno al final. Puedes parar y volver más tarde.",
        "acked": "Confirmado",
        "now": "Ahora",
        "locked": "Se desbloquea tras el anterior",
        "start_button": "Empezar",
        "continue_button": "Continuar",
        "done_button": "Ver resumen",
        "back_to_list": "Volver a la lista",
        "module_of": "Módulo {i} de {n}",
        "ack_button": "He leído y entendido",
        "ack_note": "Guardaremos tu confirmación con fecha y hora.",
        "acked_at": "Confirmado {when}",
        "next_module": "Siguiente módulo",
        "open_pdf": "Abrir",
        "locked_message": "Primero confirma el módulo anterior.",
        "done_title": "Listo",
        "done_intro": "Todos los módulos están confirmados. Nos vemos en el trabajo.",
        "done_first_day": "Tu primer día",
        "done_back": "Volver a los módulos",
        "minutes_short": "min",
        "modules_1": "1 módulo", "modules_few": "{n} módulos", "modules_many": "{n} módulos",
    },
    "uk": {
        "kicker": "Портал працівника",
        "h_light": "Вітаємо в команді.",
        "h_bold": "Почнімо вступ.",
        "login_intro": "Увійдіть за номером телефону та кодом: це день і місяць вашого народження.",
        "phone_label": "Номер телефону",
        "phone_placeholder": "+48 600 000 000",
        "code_label": "Код: день і місяць народження",
        "code_placeholder": "0803",
        "code_hint": "4 цифри: день і місяць, напр. 0803 для 8 березня.",
        "login_button": "Увійти",
        "login_error": "Ми не знайшли такого номера або код неправильний. Перевірте і спробуйте ще раз.",
        "login_no_segment": "Ваш вступ ще не готовий. Зверніться до координатора.",
        "help": "Проблеми зі входом?",
        "s1": "Увійдіть",
        "s2": "Пройдіть модулі",
        "s3": "Підтвердьте і готово",
        "logout": "Вийти",
        "hi": "Привіт",
        "progress": "{acked} з {total} завершено",
        "meta": "{modules} · бл. {min} хв",
        "meta_short": "{modules}",
        "start_intro": "Проходьте модулі по черзі та підтверджуйте кожен наприкінці. Можна зупинитися і повернутися пізніше.",
        "acked": "Підтверджено",
        "now": "Зараз",
        "locked": "Відкриється після попереднього",
        "start_button": "Почати",
        "continue_button": "Продовжити",
        "done_button": "Переглянути підсумок",
        "back_to_list": "Назад до списку",
        "module_of": "Модуль {i} з {n}",
        "ack_button": "Я прочитав(ла) і зрозумів(ла)",
        "ack_note": "Ми збережемо підтвердження з датою та часом.",
        "acked_at": "Підтверджено {when}",
        "next_module": "Наступний модуль",
        "open_pdf": "Відкрити",
        "locked_message": "Спочатку підтвердьте попередній модуль.",
        "done_title": "Готово",
        "done_intro": "Усі модулі підтверджено. До зустрічі на роботі.",
        "done_first_day": "Ваш перший день",
        "done_back": "Повернутися до модулів",
        "minutes_short": "хв",
        "modules_1": "1 модуль", "modules_few": "{n} модулі", "modules_many": "{n} модулів",
    },
    "ru": {
        "kicker": "Портал сотрудника",
        "h_light": "Добро пожаловать в команду.",
        "h_bold": "Начнём введение.",
        "login_intro": "Войдите по номеру телефона и коду: это день и месяц вашего рождения.",
        "phone_label": "Номер телефона",
        "phone_placeholder": "+48 600 000 000",
        "code_label": "Код: день и месяц рождения",
        "code_placeholder": "0803",
        "code_hint": "4 цифры: день и месяц, напр. 0803 для 8 марта.",
        "login_button": "Войти",
        "login_error": "Мы не нашли такой номер или код неверный. Проверьте и попробуйте снова.",
        "login_no_segment": "Ваше введение ещё не готово. Свяжитесь с координатором.",
        "help": "Проблемы со входом?",
        "s1": "Войдите",
        "s2": "Пройдите модули",
        "s3": "Подтвердите и готово",
        "logout": "Выйти",
        "hi": "Привет",
        "progress": "{acked} из {total} завершено",
        "meta": "{modules} · около {min} мин",
        "meta_short": "{modules}",
        "start_intro": "Проходите модули по порядку и подтверждайте каждый в конце. Можно остановиться и вернуться позже.",
        "acked": "Подтверждено",
        "now": "Сейчас",
        "locked": "Откроется после предыдущего",
        "start_button": "Начать",
        "continue_button": "Продолжить",
        "done_button": "Посмотреть итог",
        "back_to_list": "Назад к списку",
        "module_of": "Модуль {i} из {n}",
        "ack_button": "Я прочитал(а) и понял(а)",
        "ack_note": "Мы сохраним подтверждение с датой и временем.",
        "acked_at": "Подтверждено {when}",
        "next_module": "Следующий модуль",
        "open_pdf": "Открыть",
        "locked_message": "Сначала подтвердите предыдущий модуль.",
        "done_title": "Готово",
        "done_intro": "Все модули подтверждены. До встречи на работе.",
        "done_first_day": "Ваш первый день",
        "done_back": "Вернуться к модулям",
        "minutes_short": "мин",
        "modules_1": "1 модуль", "modules_few": "{n} модуля", "modules_many": "{n} модулей",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or {}
    text = table.get(key) or STRINGS["pl"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def modules_count(lang: str, n: int) -> str:
    """„1 moduł", „3 moduły", „5 modułów" (pl/uk/ru liczą po słowiańsku, en/es prosto)."""
    if n == 1:
        return t(lang, "modules_1")
    if lang in ("pl", "uk", "ru"):
        last, last2 = n % 10, n % 100
        few = 2 <= last <= 4 and not 12 <= last2 <= 14
        return t(lang, "modules_few" if few else "modules_many", n=n)
    return t(lang, "modules_few", n=n)


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "pl"
    lang = lang.lower()
    if lang == "ua":
        lang = "uk"
    return lang if lang in SUPPORTED_LANGS else "pl"
