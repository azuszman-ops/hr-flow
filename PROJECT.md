# HR-Flow — Dokumentacja Projektu

## Klient
**Find-Work.pl** — agencja pracy tymczasowej, 300+ pracowników, 20+ kontraktów.

## Cel
Eliminacja manualnego zbierania grafików dostępności. System wysyła spersonalizowane wiadomości WhatsApp, pracownicy wypełniają formularz jednym kliknięciem, admin widzi wyniki w czasie rzeczywistym.

## Stack techniczny
- **Backend**: FastAPI + SQLAlchemy async + PostgreSQL
- **Frontend**: Jinja2 + Tailwind CSS + Alpine.js
- **Messaging**: Twilio WhatsApp API (sandbox → docelowo Meta WhatsApp Business API)
- **Hosting**: Railway (auto-deploy z GitHub `main`)
- **Repo**: `azuszman-ops/hr-flow` branch `main`

---

## Architektura

### Multi-tenant
Jeden system obsługuje wielu klientów (Tenant = klient agencji). Każdy tenant ma swoich pracowników, kontrakty i kampanie.

### Modele danych
- **Tenant** — klient agencji (np. Find-Work.pl)
- **Contract** — kontrakt / miejsce pracy (np. Magazyn Kraków)
- **Employee** — pracownik z unikalnym tokenem do bezpiecznego linku
- **ContractEmployee** — przypisanie pracownika do kontraktu
- **ScheduleSubmission** — wypełniony grafik (1 na miesiąc per pracownik)
- **AvailabilityDay** — dostępność per dzień (available / partial / unavailable)
- **MessageCampaign** — kampania wysyłkowa (miesięczna)
- **MessageLog** — log wysłanych wiadomości (initial / reminder 1 / reminder 2)
- **TenantSettings** — szablony wiadomości i konfiguracja przypomnień

---

## Funkcjonalności

### Panel admina
| URL | Opis |
|-----|------|
| `/` | Redirect do tenanta (jeśli 1 tenant) |
| `/admin/{id}` | Przegląd: statystyki, progress bar, quick links |
| `/admin/{id}/calendar` | Kalendarz zarządczy — grid (pracownicy × dni) |
| `/admin/{id}/schedules` | Lista wypełnionych grafików ze szczegółami |
| `/admin/{id}/employees` | Zarządzanie pracownikami (dodaj/edytuj/usuń) |
| `/admin/{id}/contracts` | Zarządzanie kontraktami (dodaj/edytuj/usuń) |
| `/admin/{id}/campaigns` | Kampanie WhatsApp — tworzenie, wysyłka, delete |
| `/admin/{id}/settings` | Szablony wiadomości + konfiguracja przypomnień |

### Formularz pracownika
- URL: `/schedule/{token}` — unikalny link per pracownik
- Widok kalendarza na następny miesiąc
- Opcje: Dostępny / Częściowo (z godzinami) / Niedostępny
- Przyciski szybkiego wyboru: wszystkie dni, tylko dni robocze, niedostępny
- Polskie święta automatycznie blokowane
- Możliwość aktualizacji po wypełnieniu

### Automatyzacja
- **Kampanie WhatsApp**: masowa wysyłka do pracowników (z filtrem po kontrakcie)
- **Przypomnienie 1**: automatyczne po X dniach (konfigurowalne), tylko do tych bez grafiku
- **Przypomnienie 2**: automatyczne po kolejnych Y dniach od przypomnienia 1
- **Scheduler**: APScheduler, uruchamiany codziennie o 09:00 UTC

---

## Zmienne w szablonach wiadomości
```
{first_name}     — imię pracownika
{last_name}      — nazwisko pracownika
{month_name}     — nazwa miesiąca po polsku
{schedule_link}  — unikalny link do formularza
```

---

## Konfiguracja środowiskowa (Railway env vars)
```
DATABASE_URL              — PostgreSQL connection string
TWILIO_ACCOUNT_SID        — Twilio Account SID
TWILIO_AUTH_TOKEN         — Twilio Auth Token
TWILIO_WHATSAPP_FROM      — nadawca WhatsApp (sandbox: whatsapp:+14155238886)
BASE_URL                  — publiczny URL aplikacji (np. https://hr-flow.railway.app)
```

---

## Demo — przygotowanie

### Przed spotkaniem
1. Dodać uczestników jako pracowników w panelu (Pracownicy → dodaj)
2. Przypisać ich do kontraktu
3. Wysłać uczestnikom screenshot QR kodu z Twilio sandbox z instrukcją:
   > *"Zeskanuj QR kod aparatem — otworzy się WhatsApp z gotową wiadomością, wystarczy ją wysłać. Jednorazowa aktywacja przed demo."*
4. Sprawdzić że `BASE_URL` jest ustawiony na Railway

### Scenariusz demo (~15-20 min)
1. **Przegląd** — pokazać statystyki, progress bar (0% na start)
2. **Pracownicy** — uczestnicy widzą siebie na liście
3. **Kampanie** — Utwórz kampanię na następny miesiąc → Wyślij wiadomości
4. *(każdy dostaje WhatsApp na telefonie)*
5. **Uczestnicy wypełniają grafik** na swoich telefonach (link z WhatsAppa)
6. **Odśwież Przegląd** — progress bar skacze, % rośnie
7. **Kalendarz zarządczy** — widać kolorowy grid z dostępnością
8. Wyjaśnić że system sam przypomni tym, którzy nie wypełnili

---

## Historia zmian

### Sesja 1 — fundament
- Multi-tenant FastAPI app
- Modele: Tenant, Contract, Employee, ScheduleSubmission, AvailabilityDay
- Formularz grafiku dla pracownika z Alpine.js
- Polskie święta blokowane automatycznie
- Admin: pracownicy, kontrakty, kampanie, schedules, settings
- WhatsApp via Twilio
- APScheduler — follow-up reminders

### Sesja 2 — demo features
- **Tenant overview dashboard** (`/admin/{id}`) ze statystykami i progress barem
- **Kalendarz zarządczy** (`/admin/{id}/calendar`) — grid employees × dni, kolory statusów
- Filtr po kontrakcie w kalendarzu + nawigacja po miesiącach
- Domyślny miesiąc w kalendarzu = następny miesiąc
- Zaktualizowana nawigacja (Przegląd + Kalendarz jako główne)
- `seed_demo.py` — seed script z danymi demo (10 pracowników, 3 kontrakty)

### Sesja 3 — poprawki pre-demo
- **Fix**: Crash kalendarza przy wyborze "wszyscy pracownicy" (pusty string vs int)
- **Fix**: Domyślny miesiąc kampanii — obsługa Grudzień→Styczeń
- **Fix**: Internal server error w ustawieniach — `ADD COLUMN IF NOT EXISTS` w `init_db`
- Logo HR-Flow → link do tenant overview (nie główny dashboard)
- `/` redirect do `/admin/{id}` gdy jest tylko 1 tenant (klient nie widzi multi-tenant panelu)
- Delete kampanii (przycisk z potwierdzeniem)
- Inline edycja kontraktu (nazwa + opis)
- **2-etapowe przypomnienia**: Przypomnienie 1 po X dniach, Przypomnienie 2 po Y kolejnych dniach
  - Nowe pola modelu: `TenantSettings.reminder_2_message`, `TenantSettings.reminder_2_days`
  - Nowe pole: `MessageLog.is_reminder_2`
  - Scheduler zaktualizowany o logikę reminder 2
  - Settings UI z dwoma slotami przypomnień

---

## Roadmap (po demo)

### Priorytet wysoki
- [ ] Wymiana Twilio sandbox → **Meta WhatsApp Business API**
- [ ] Logowanie per tenant (prosty login/hasło — klient widzi tylko swoje dane)
- [ ] Import pracowników z **CSV** (imię, nazwisko, telefon, kontrakt)

### Priorytet średni
- [ ] Eksport grafiku do Excel/CSV
- [ ] Widok kalendarza zarządczego z filtrem po dniu (kto dostępny 15 kwietnia?)
- [ ] Email jako alternatywny kanał wysyłki (SendGrid)
- [ ] Viber jako alternatywny kanał

### Priorytet niski
- [ ] Instrukcja wideo "grafik w 60 sekund" dla pracowników
- [ ] PDF z grafikiem do druku
- [ ] Powiadomienie do admina gdy pracownik wypełni grafik
