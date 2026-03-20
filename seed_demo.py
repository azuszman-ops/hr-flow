"""
Seed script — dane demo dla HR-Flow.
Uruchom: python seed_demo.py

Tworzy:
  - 1 tenant: Find-Work.pl
  - 3 kontrakty (Logistyka Warszawa, Produkcja Łódź, Magazyn Kraków)
  - 10 pracowników z przykładowymi numerami

Bezpieczne wielokrotne uruchamianie — nie duplikuje.

Aby dodać prawdziwe numery uczestników spotkania: edytuj DEMO_EMPLOYEES poniżej.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.database import AsyncSessionLocal, engine, Base
from app.models import Tenant, Contract, Employee, ContractEmployee
from sqlalchemy import select
import app.models  # noqa — rejestruje modele


DEMO_TENANT_SLUG = "find-work"

DEMO_CONTRACTS = [
    "Logistyka Warszawa",
    "Produkcja Łódź",
    "Magazyn Kraków",
]

# -----------------------------------------------------------------------
# EDYTUJ NUMERY przed demo — format: +48XXXXXXXXX lub None
# -----------------------------------------------------------------------
DEMO_EMPLOYEES = [
    {"first_name": "Anna",      "last_name": "Kowalska",    "phone_whatsapp": None},
    {"first_name": "Piotr",     "last_name": "Nowak",       "phone_whatsapp": None},
    {"first_name": "Marta",     "last_name": "Wiśniewska",  "phone_whatsapp": None},
    {"first_name": "Tomasz",    "last_name": "Wójcik",      "phone_whatsapp": None},
    {"first_name": "Katarzyna", "last_name": "Kamińska",    "phone_whatsapp": None},
    {"first_name": "Marcin",    "last_name": "Lewandowski", "phone_whatsapp": None},
    {"first_name": "Agnieszka", "last_name": "Zielińska",   "phone_whatsapp": None},
    {"first_name": "Łukasz",    "last_name": "Szymański",   "phone_whatsapp": None},
    {"first_name": "Natalia",   "last_name": "Woźniak",     "phone_whatsapp": None},
    {"first_name": "Krzysztof", "last_name": "Dąbrowski",   "phone_whatsapp": None},
]

# Przypisanie: indeks pracownika -> nazwa kontraktu
# (pracownicy mogą być w kilku kontraktach)
EMPLOYEE_CONTRACT_MAP = {
    0: "Logistyka Warszawa",
    1: "Logistyka Warszawa",
    2: "Produkcja Łódź",
    3: "Produkcja Łódź",
    4: "Produkcja Łódź",
    5: "Magazyn Kraków",
    6: "Magazyn Kraków",
    7: "Logistyka Warszawa",
    8: "Magazyn Kraków",
    9: "Produkcja Łódź",
}


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Tenant
        tenant = (await db.execute(
            select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG)
        )).scalar_one_or_none()

        if not tenant:
            tenant = Tenant(name="Find-Work.pl", slug=DEMO_TENANT_SLUG)
            db.add(tenant)
            await db.flush()
            print(f"[+] Tenant utworzony: {tenant.name} (id={tenant.id})")
        else:
            print(f"[=] Tenant istnieje: {tenant.name} (id={tenant.id})")

        # Kontrakty
        contract_map = {}
        for name in DEMO_CONTRACTS:
            existing = (await db.execute(
                select(Contract).where(Contract.tenant_id == tenant.id, Contract.name == name)
            )).scalar_one_or_none()
            if not existing:
                c = Contract(tenant_id=tenant.id, name=name)
                db.add(c)
                await db.flush()
                contract_map[name] = c
                print(f"[+] Kontrakt: {name}")
            else:
                contract_map[name] = existing
                print(f"[=] Kontrakt istnieje: {name}")

        # Pracownicy
        for idx, emp_data in enumerate(DEMO_EMPLOYEES):
            full_name_check = (await db.execute(
                select(Employee).where(
                    Employee.tenant_id == tenant.id,
                    Employee.first_name == emp_data["first_name"],
                    Employee.last_name == emp_data["last_name"],
                )
            )).scalar_one_or_none()

            if not full_name_check:
                emp = Employee(
                    tenant_id=tenant.id,
                    first_name=emp_data["first_name"],
                    last_name=emp_data["last_name"],
                    phone_whatsapp=emp_data.get("phone_whatsapp"),
                )
                db.add(emp)
                await db.flush()
                print(f"[+] Pracownik: {emp.first_name} {emp.last_name} — token: {emp.token[:8]}...")

                # Przypisz do kontraktu
                contract_name = EMPLOYEE_CONTRACT_MAP.get(idx)
                if contract_name and contract_name in contract_map:
                    link = ContractEmployee(contract_id=contract_map[contract_name].id, employee_id=emp.id)
                    db.add(link)
            else:
                print(f"[=] Pracownik istnieje: {emp_data['first_name']} {emp_data['last_name']}")

        await db.commit()
        print("\n✅ Seed zakończony.")
        print(f"   Panel admina: /admin/{tenant.id}")
        print(f"   Kalendarz:    /admin/{tenant.id}/calendar")


if __name__ == "__main__":
    asyncio.run(seed())
