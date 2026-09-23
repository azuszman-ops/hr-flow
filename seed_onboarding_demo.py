"""
Dane demo do modułu Onboarding (LOKALNIE, do prezentacji dla Find Work).
Tworzy tenant find-work (jeśli brak), 4 segmenty z modułami z oferty i 4 osoby.

Uruchomienie:  set -a; source .env; set +a; .venv/bin/python seed_onboarding_demo.py
Nie uruchamiać na produkcji bez decyzji Alberta.
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models import Tenant, Employee
import app.api.onboarding  # noqa: rejestruje modele onboardingu
from app.models_onboarding import (
    OnboardingSettings, OnboardingSegment, OnboardingModule, OnboardingPerson,
)

SEGMENTS = {
    "Automotive 1": [
        ("Bezpieczeństwo na hali", 5,
         "Na hali obowiązują zasady, które chronią Ciebie i osoby obok. Przeczytaj je uważnie, na koniec potwierdź.\n\n"
         "- Poruszaj się tylko wyznaczonymi ciągami komunikacyjnymi (żółte linie).\n"
         "- Wózki widłowe mają pierwszeństwo. Zatrzymaj się i nawiąż kontakt wzrokowy z operatorem.\n"
         "- Nie wchodź do stref oznaczonych czerwoną taśmą.\n"
         "- Wyłączniki awaryjne (czerwone grzybki) są przy każdej maszynie. Użyj ich, gdy widzisz zagrożenie.\n"
         "- Wypadek albo sytuację niebezpieczną zgłoś natychmiast koordynatorowi.\n\n"
         "Telefon alarmowy na hali: 112. Koordynator Find Work: numer dostaniesz pierwszego dnia."),
        ("Odzież i obuwie ochronne", 3,
         "Na całej hali obowiązuje obuwie ochronne S3 z podnoskiem. Wydaje je koordynator pierwszego dnia.\n\n"
         "- Kamizelka odblaskowa: zawsze, także w drodze do szatni.\n"
         "- Okulary ochronne: na stanowiskach oznaczonych piktogramem.\n"
         "- Rękawice: dobrane do stanowiska, nie zabieraj rękawic z innego stanowiska.\n"
         "- Długie włosy spięte, bez biżuterii na dłoniach."),
        ("Stanowisko: opis maszyny", 5,
         "Pracujesz przy linii montażu wiązek. Maszyna ma trzy strefy: podawanie, zaciskanie, kontrola.\n\n"
         "- Przed startem sprawdź, czy osłony są zamknięte. Maszyna nie ruszy przy otwartej osłonie.\n"
         "- Nigdy nie sięgaj do strefy zaciskania podczas pracy maszyny.\n"
         "- Zacięcie: zatrzymaj maszynę przyciskiem STOP, potem wezwij brygadzistę. Nie usuwaj zacięć samodzielnie.\n"
         "- Na koniec zmiany: wyłącz, posprzątaj stanowisko, wpisz się na karcie."),
        ("Pierwszy dzień i kontakt", 2,
         "Pierwszego dnia zgłoś się do koordynatora Find Work przy wejściu głównym. Weź ze sobą dokument tożsamości.\n\n"
         "- Szatnia i szafka: dostaniesz kluczyk od koordynatora.\n"
         "- Przerwy: 15 minut co 2 godziny, 30 minut na posiłek.\n"
         "- Nieobecność zgłaszaj koordynatorowi najpóźniej 2 godziny przed zmianą.\n\n"
         "Masz pytania? Napisz na WhatsApp, z którego dostałeś ten link."),
    ],
    "Magazyn 2": [
        ("Bezpieczeństwo w magazynie", 4,
         "W magazynie największe ryzyko to ruch wózków i spadające towary.\n\n"
         "- Nie przechodź pod uniesionymi widłami.\n"
         "- Nie wchodź na regały. Do wysokich półek używamy wyłącznie wózka albo drabiny z asekuracją.\n"
         "- Palety układamy do wysokości oznaczonej na regale.\n"
         "- Uszkodzony regał albo paletę zgłoś od razu."),
        ("Skaner i system WMS", 5,
         "Każdą operację potwierdzasz skanerem. Bez skanu towar nie istnieje w systemie.\n\n"
         "- Logowanie do skanera: Twój numer pracownika.\n"
         "- Kompletacja: skanuj lokalizację, potem produkt, potem ilość.\n"
         "- Błąd skanu: nie klikaj dalej, zawołaj lidera zmiany."),
        ("Odzież i obuwie ochronne", 2,
         "Obuwie S3, kamizelka odblaskowa i rękawice. Zimą kurtka ocieplana z magazynu."),
        ("Pierwszy dzień i kontakt", 2,
         "Zgłoś się do lidera zmiany w biurze magazynu. Dostaniesz skaner, kluczyk do szafki i plan pierwszego tygodnia."),
    ],
    "Piekarnia": [
        ("Higiena i strefa produkcji spożywczej", 5,
         "W piekarni obowiązują zasady HACCP. Przed wejściem na produkcję:\n\n"
         "- Umyj i zdezynfekuj dłonie, załóż czepek i fartuch.\n"
         "- Biżuteria, zegarek, lakier na paznokciach: zakazane.\n"
         "- Skaleczenie zabezpiecz niebieskim plastrem i zgłoś liderowi.\n"
         "- Choroba (biegunka, wymioty, gorączka): nie przychodź do pracy, zadzwoń do koordynatora."),
        ("Bezpieczeństwo przy piecach i krajalnicach", 4,
         "- Piece: otwieraj drzwi odwracając twarz, używaj rękawic termicznych.\n"
         "- Krajalnica: tylko po szkoleniu, nigdy bez osłony.\n"
         "- Mokra podłoga: od razu wytrzyj albo ustaw znak."),
        ("Pierwszy dzień i kontakt", 2,
         "Zmiana nocna zaczyna się o 22:00. Zgłoś się do lidera przy wejściu dla pracowników."),
    ],
    "Back office": [
        ("Zasady pracy w biurze", 3,
         "- Godziny pracy 8:00 do 16:00, elastyczny start do 9:00 po uzgodnieniu.\n"
         "- Dostępy do systemów dostaniesz mailem pierwszego dnia.\n"
         "- Dane osobowe pracowników i klientów: nie wynosimy, nie przesyłamy na prywatne skrzynki."),
        ("Bezpieczeństwo informacji", 3,
         "- Blokuj komputer, gdy odchodzisz od biurka.\n"
         "- Hasła tylko w menedżerze haseł, nigdy na kartce.\n"
         "- Podejrzany mail: nie klikaj, prześlij do IT."),
        ("Pierwszy dzień i kontakt", 2,
         "Zgłoś się do recepcji o 9:00. Opiekun pierwszego tygodnia oprowadzi Cię po biurze."),
    ],
}

PERSONS = [
    ("Olena", "Kravchenko", "+48600100001", "Automotive 1", "uk", 12, 4,
     "Poniedziałek 6:00, wejście od ul. Fabrycznej. Koordynatorka: Marzena. Obuwie odbierzesz na miejscu."),
    ("Marek", "Nowak", "+48600100002", "Magazyn 2", "pl", 3, 11, "Wtorek 7:00, biuro magazynu, lider zmiany: Paweł."),
    ("Carlos", "Mendez", "+48600100003", "Piekarnia", "es", 25, 7, "Środa 22:00, wejście dla pracowników."),
    ("Anna", "Wiśniewska", "+48600100004", "Back office", "pl", 8, 3, "Poniedziałek 9:00, recepcja."),
]


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "find-work"))).scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="Find Work", slug="find-work")
            db.add(tenant)
            await db.flush()
            print("Utworzono tenant Find Work")

        settings = (await db.execute(select(OnboardingSettings).where(OnboardingSettings.tenant_id == tenant.id))).scalar_one_or_none()
        if not settings:
            db.add(OnboardingSettings(tenant_id=tenant.id, brand_name="Find Work", brand_color="#1d4ed8"))

        existing = (await db.execute(select(OnboardingSegment).where(OnboardingSegment.tenant_id == tenant.id))).scalars().all()
        if existing:
            print(f"Segmenty już są ({len(existing)}), pomijam.")
        else:
            seg_by_name = {}
            for i, (name, modules) in enumerate(SEGMENTS.items(), start=1):
                seg = OnboardingSegment(tenant_id=tenant.id, name=name, sort_order=i)
                db.add(seg)
                await db.flush()
                seg_by_name[name] = seg
                for j, (title, minutes, body) in enumerate(modules, start=1):
                    db.add(OnboardingModule(segment_id=seg.id, title=title, body=body, estimated_minutes=minutes, sort_order=j))
            print(f"Dodano {len(SEGMENTS)} segmentów")

            for first, last, phone, seg_name, lang, bd, bm, info in PERSONS:
                emp = (await db.execute(select(Employee).where(Employee.tenant_id == tenant.id, Employee.phone_whatsapp == phone))).scalars().first()
                if not emp:
                    emp = Employee(tenant_id=tenant.id, first_name=first, last_name=last, phone_whatsapp=phone)
                    db.add(emp)
                    await db.flush()
                db.add(OnboardingPerson(tenant_id=tenant.id, employee_id=emp.id, segment_id=seg_by_name[seg_name].id,
                                        language=lang, birth_day=bd, birth_month=bm, first_day_info=info))
            print(f"Dodano {len(PERSONS)} osób (kody: " + ", ".join(f"{p[0]} {p[5]:02d}{p[6]:02d}" for p in PERSONS) + ")")
        await db.commit()
        print(f"Panel: /admin/{tenant.id}/onboarding   Strona pracownika: /o/{tenant.slug}")


if __name__ == "__main__":
    asyncio.run(main())
