"""
Teksty interfejsu strony pracownika (onboarding) w 5 językach.
Języki: pl (bazowy), en, uk (ukraiński, w UI jako UA), es, ru.
Brak klucza w danym języku = tekst polski.

Tłumaczenia treści modułów są w bazie (onboarding_module_translations),
tu tylko stałe elementy interfejsu.
"""

LANG_LABELS = {"pl": "PL", "en": "EN", "uk": "UA", "es": "ES", "ru": "RU"}
LANG_NAMES = {"pl": "Polski", "en": "English", "uk": "Українська", "es": "Español", "ru": "Русский"}
SUPPORTED_LANGS = ["pl", "en", "uk", "es", "ru"]

# Języki widoczne w przełączniku na stronie pracownika. Dopisujemy po przetłumaczeniu UI.
READY_LANGS = ["pl"]

STRINGS = {
    "pl": {
        "login_title": "Witaj w {brand}",
        "login_intro": "Zaloguj się, aby przejść onboarding przed pierwszym dniem pracy.",
        "phone_label": "Numer telefonu",
        "phone_placeholder": "+48 600 123 456",
        "code_label": "Kod: dzień i miesiąc urodzenia",
        "code_placeholder": "np. 0803 dla 8 marca",
        "code_hint": "Cztery cyfry: dzień i miesiąc, np. 0803 dla 8 marca.",
        "login_button": "Wejdź",
        "login_error": "Nie znaleźliśmy takiego numeru albo kod jest błędny. Sprawdź i spróbuj ponownie.",
        "login_no_segment": "Twój onboarding nie jest jeszcze gotowy. Skontaktuj się z koordynatorem.",
        "start_title": "Twój onboarding",
        "modules_count": "{n} modułów",
        "modules_count_1": "1 moduł",
        "about_minutes": "około {n} minut",
        "start_intro": "Przejdź wszystkie moduły przed pierwszym dniem pracy. Możesz przerwać i wrócić później.",
        "start_button": "Zaczynam",
        "continue_button": "Kontynuuj",
        "done_button": "Zobacz podsumowanie",
        "module_done": "Potwierdzony",
        "module_now": "Teraz",
        "module_locked": "Odblokuje się po poprzednim module",
        "module_of": "Moduł {i} z {n}",
        "ack_button": "Zapoznałem się i rozumiem",
        "ack_note": "Kliknięcie zapisuje potwierdzenie z datą i godziną.",
        "acked_at": "Potwierdzono {when}",
        "next_module": "Następny moduł",
        "back_to_list": "Wróć do listy",
        "open_pdf": "Otwórz PDF",
        "locked_message": "Najpierw potwierdź poprzedni moduł.",
        "done_title": "Gotowe",
        "done_intro": "Wszystkie moduły potwierdzone.",
        "done_first_day": "Pierwszy dzień",
        "done_back": "Wróć do materiałów",
        "logout": "Wyloguj",
        "minutes_short": "min",
    },
    "en": {},
    "uk": {},
    "es": {},
    "ru": {},
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


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "pl"
    lang = lang.lower()
    if lang == "ua":
        lang = "uk"
    return lang if lang in SUPPORTED_LANGS else "pl"
