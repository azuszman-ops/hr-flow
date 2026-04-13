from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from datetime import date, datetime, timedelta
from typing import List, Optional
import calendar


def get_easter(year: int) -> date:
    """Algorytm Anonymous Gregorian — oblicza datę Wielkanocy."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_polish_holidays(year: int) -> dict:
    """Zwraca słownik {date: nazwa_święta} polskich dni wolnych."""
    easter = get_easter(year)
    holidays = {
        date(year, 1, 1): "Nowy Rok",
        date(year, 1, 6): "Trzech Króli",
        easter: "Wielkanoc",
        easter + timedelta(days=1): "Poniedziałek Wielkanocny",
        date(year, 5, 1): "Święto Pracy",
        date(year, 5, 3): "Święto Konstytucji 3 Maja",
        easter + timedelta(days=49): "Zielone Świątki",
        easter + timedelta(days=60): "Boże Ciało",
        date(year, 8, 15): "Wniebowzięcie NMP",
        date(year, 11, 1): "Wszystkich Świętych",
        date(year, 11, 11): "Święto Niepodległości",
        date(year, 12, 25): "Boże Narodzenie",
        date(year, 12, 26): "Drugi dzień Bożego Narodzenia",
    }
    return holidays

from app.database import get_db
from app.models import (
    Tenant, Contract, Employee, ContractEmployee,
    ScheduleSubmission, AvailabilityDay, AvailabilityStatus,
    MessageTemplate, MessageCampaign, MessageLog, MessageChannel, CampaignStatus,
    TenantSettings, DEFAULT_INITIAL_MESSAGE, DEFAULT_REMINDER_MESSAGE, DEFAULT_REMINDER_2_MESSAGE,
)
from app.services.messaging import (
    send_whatsapp, render_template, MONTH_NAMES_PL, build_schedule_link
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# ADMIN — Dashboard
# ============================================================

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    tenants = (await db.execute(select(Tenant))).scalars().all()
    # Jeśli jest dokładnie 1 tenant — przekieruj bezpośrednio do jego panelu
    if len(tenants) == 1:
        return RedirectResponse(f"/admin/{tenants[0].id}", status_code=302)
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "tenants": tenants})


# ============================================================
# ADMIN — Tenant Overview
# ============================================================

@router.get("/admin/{tenant_id}", response_class=HTMLResponse)
async def tenant_overview(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)

    now = datetime.now()
    year, month = now.year, now.month

    total_employees = (await db.execute(
        select(func.count(Employee.id)).where(Employee.tenant_id == tenant_id, Employee.is_active == True)
    )).scalar() or 0

    total_contracts = (await db.execute(
        select(func.count(Contract.id)).where(Contract.tenant_id == tenant_id, Contract.is_active == True)
    )).scalar() or 0

    submitted_count = (await db.execute(
        select(func.count(ScheduleSubmission.id))
        .join(Employee, Employee.id == ScheduleSubmission.employee_id)
        .where(
            Employee.tenant_id == tenant_id,
            ScheduleSubmission.year == year,
            ScheduleSubmission.month == month,
        )
    )).scalar() or 0

    submitted_pct = round(submitted_count / total_employees * 100) if total_employees > 0 else 0

    stats = {
        "total_employees": total_employees,
        "total_contracts": total_contracts,
        "submitted_count": submitted_count,
        "pending_count": max(0, total_employees - submitted_count),
        "submitted_pct": submitted_pct,
    }

    return templates.TemplateResponse("admin/tenant_overview.html", {
        "request": request,
        "tenant": tenant,
        "stats": stats,
        "month_name": MONTH_NAMES_PL.get(month, ""),
        "year": year,
    })


# ============================================================
# ADMIN — Kalendarz zarządczy
# ============================================================

@router.get("/admin/{tenant_id}/calendar", response_class=HTMLResponse)
async def admin_calendar(
    request: Request,
    tenant_id: int,
    year: int = None,
    month: int = None,
    contract_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)

    now = datetime.now()
    if year is None or month is None:
        # Domyślnie: następny miesiąc (zbieramy grafik na przyszły miesiąc)
        if now.month == 12:
            year, month = now.year + 1, 1
        else:
            year, month = now.year, now.month + 1

    # Prev / next month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    contracts = (await db.execute(
        select(Contract).where(Contract.tenant_id == tenant_id, Contract.is_active == True)
    )).scalars().all()

    # Pobierz pracowników (z filtrem po kontrakcie)
    if contract_id:
        employees = (await db.execute(
            select(Employee)
            .join(ContractEmployee, ContractEmployee.employee_id == Employee.id)
            .where(
                Employee.tenant_id == tenant_id,
                Employee.is_active == True,
                ContractEmployee.contract_id == contract_id,
            )
            .order_by(Employee.last_name, Employee.first_name)
            .distinct()
        )).scalars().all()
    else:
        employees = (await db.execute(
            select(Employee)
            .where(Employee.tenant_id == tenant_id, Employee.is_active == True)
            .order_by(Employee.last_name, Employee.first_name)
        )).scalars().all()

    employee_ids = [e.id for e in employees]

    # Pobierz submissiony z dniami
    submissions = (await db.execute(
        select(ScheduleSubmission)
        .where(
            ScheduleSubmission.employee_id.in_(employee_ids),
            ScheduleSubmission.year == year,
            ScheduleSubmission.month == month,
        )
        .options(selectinload(ScheduleSubmission.days))
    )).scalars().all()

    submissions_by_emp = {s.employee_id: s for s in submissions}

    # Zbuduj mapę: emp_id -> {iso_date: status}
    day_statuses: dict[int, dict[str, str]] = {}
    day_hours: dict[int, dict[str, str]] = {}
    for sub in submissions:
        day_statuses[sub.employee_id] = {}
        day_hours[sub.employee_id] = {}
        for d in sub.days:
            iso = d.date.isoformat()
            day_statuses[sub.employee_id][iso] = d.status.value
            if d.status.value == "partial" and d.hour_from and d.hour_to:
                day_hours[sub.employee_id][iso] = f"{d.hour_from}–{d.hour_to}"

    num_days = calendar.monthrange(year, month)[1]
    days = [date(year, month, d) for d in range(1, num_days + 1)]
    holidays = get_polish_holidays(year)
    holidays_iso = {d.isoformat(): name for d, name in holidays.items() if d.month == month}

    return templates.TemplateResponse("admin/calendar.html", {
        "request": request,
        "tenant": tenant,
        "contracts": contracts,
        "selected_contract_id": contract_id,
        "employees": employees,
        "submissions_by_emp": submissions_by_emp,
        "day_statuses": day_statuses,
        "day_hours": day_hours,
        "days": days,
        "holidays_iso": holidays_iso,
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES_PL.get(month, ""),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "submitted_count": len(submissions),
    })


# ============================================================
# ADMIN — Kontrakty
# ============================================================

@router.get("/admin/{tenant_id}/contracts", response_class=HTMLResponse)
async def admin_contracts(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    contracts = (
        await db.execute(
            select(Contract)
            .where(Contract.tenant_id == tenant_id)
            .options(selectinload(Contract.employee_links).selectinload(ContractEmployee.employee))
        )
    ).scalars().all()
    return templates.TemplateResponse("admin/contracts.html", {
        "request": request, "tenant": tenant, "contracts": contracts
    })


@router.post("/admin/{tenant_id}/contracts")
async def create_contract(
    tenant_id: int,
    name: str = Form(...),
    description: str = Form(""),
    city_1: str = Form(""),
    city_2: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    contract = Contract(
        tenant_id=tenant_id, name=name, description=description or None,
        city_1=city_1 or None, city_2=city_2 or None,
    )
    db.add(contract)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/contracts", status_code=303)


@router.post("/admin/{tenant_id}/contracts/{contract_id}/delete")
async def delete_contract(tenant_id: int, contract_id: int, db: AsyncSession = Depends(get_db)):
    contract = await db.get(Contract, contract_id)
    if contract and contract.tenant_id == tenant_id:
        await db.delete(contract)
        await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/contracts", status_code=303)


@router.post("/admin/{tenant_id}/contracts/{contract_id}/edit")
async def edit_contract(
    tenant_id: int,
    contract_id: int,
    name: str = Form(...),
    description: str = Form(""),
    city_1: str = Form(""),
    city_2: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if contract and contract.tenant_id == tenant_id:
        contract.name = name
        contract.description = description or None
        contract.city_1 = city_1 or None
        contract.city_2 = city_2 or None
        await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/contracts", status_code=303)


@router.get("/admin/{tenant_id}/contracts/{contract_id}", response_class=HTMLResponse)
async def contract_detail(
    request: Request, tenant_id: int, contract_id: int, db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    contract = (
        await db.execute(
            select(Contract)
            .where(Contract.id == contract_id, Contract.tenant_id == tenant_id)
            .options(selectinload(Contract.employee_links).selectinload(ContractEmployee.employee))
        )
    ).scalar_one_or_none()
    if not contract:
        raise HTTPException(404)

    assigned_employee_ids = {link.employee_id for link in contract.employee_links}
    assigned_employees = [link.employee for link in contract.employee_links]

    all_employees = (
        await db.execute(
            select(Employee)
            .where(Employee.tenant_id == tenant_id)
            .order_by(Employee.last_name, Employee.first_name)
        )
    ).scalars().all()

    available_employees = [e for e in all_employees if e.id not in assigned_employee_ids]

    return templates.TemplateResponse("admin/contract_detail.html", {
        "request": request,
        "tenant": tenant,
        "contract": contract,
        "assigned_employees": assigned_employees,
        "available_employees": available_employees,
    })


@router.post("/admin/{tenant_id}/contracts/{contract_id}/add_employee")
async def add_employee_to_contract(
    tenant_id: int,
    contract_id: int,
    employee_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.tenant_id != tenant_id:
        raise HTTPException(404)
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise HTTPException(404)
    # Sprawdź czy już przypisany
    existing = (await db.execute(
        select(ContractEmployee).where(
            ContractEmployee.contract_id == contract_id,
            ContractEmployee.employee_id == employee_id,
        )
    )).scalar_one_or_none()
    if not existing:
        link = ContractEmployee(contract_id=contract_id, employee_id=employee_id)
        db.add(link)
        await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/contracts/{contract_id}", status_code=303)


@router.post("/admin/{tenant_id}/contracts/{contract_id}/remove_employee/{employee_id}")
async def remove_employee_from_contract(
    tenant_id: int,
    contract_id: int,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.tenant_id != tenant_id:
        raise HTTPException(404)
    await db.execute(
        delete(ContractEmployee).where(
            ContractEmployee.contract_id == contract_id,
            ContractEmployee.employee_id == employee_id,
        )
    )
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/contracts/{contract_id}", status_code=303)


# ============================================================
# ADMIN — Pracownicy
# ============================================================

@router.get("/admin/{tenant_id}/employees", response_class=HTMLResponse)
async def admin_employees(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    employees = (
        await db.execute(
            select(Employee)
            .where(Employee.tenant_id == tenant_id)
            .order_by(Employee.last_name, Employee.first_name)
        )
    ).scalars().all()
    contracts = (
        await db.execute(select(Contract).where(Contract.tenant_id == tenant_id, Contract.is_active == True))
    ).scalars().all()
    return templates.TemplateResponse("admin/employees.html", {
        "request": request, "tenant": tenant, "employees": employees, "contracts": contracts
    })


@router.post("/admin/{tenant_id}/employees")
async def create_employee(
    tenant_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_whatsapp: str = Form(""),
    phone_viber: str = Form(""),
    email: str = Form(""),
    contract_id: int = Form(None),
    db: AsyncSession = Depends(get_db)
):
    emp = Employee(
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        phone_whatsapp=phone_whatsapp or None,
        phone_viber=phone_viber or None,
        email=email or None,
    )
    db.add(emp)
    await db.flush()
    if contract_id:
        link = ContractEmployee(contract_id=contract_id, employee_id=emp.id)
        db.add(link)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/employees", status_code=303)


@router.post("/admin/{tenant_id}/employees/{employee_id}/delete")
async def delete_employee(tenant_id: int, employee_id: int, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, employee_id)
    if emp and emp.tenant_id == tenant_id:
        await db.delete(emp)
        await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/employees", status_code=303)


@router.get("/admin/{tenant_id}/employees/{employee_id}/edit", response_class=HTMLResponse)
async def edit_employee_form(
    request: Request, tenant_id: int, employee_id: int, db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise HTTPException(404)
    return templates.TemplateResponse("admin/employee_edit.html", {
        "request": request, "tenant": tenant, "employee": emp
    })


@router.post("/admin/{tenant_id}/employees/{employee_id}/edit")
async def edit_employee(
    tenant_id: int,
    employee_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_whatsapp: str = Form(""),
    phone_viber: str = Form(""),
    email: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise HTTPException(404)
    emp.first_name = first_name
    emp.last_name = last_name
    emp.phone_whatsapp = phone_whatsapp or None
    emp.phone_viber = phone_viber or None
    emp.email = email or None
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/employees", status_code=303)


# ============================================================
# ADMIN — Kampanie / Wysyłka
# ============================================================

@router.get("/admin/{tenant_id}/campaigns", response_class=HTMLResponse)
async def admin_campaigns(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    campaigns = (
        await db.execute(
            select(MessageCampaign)
            .where(MessageCampaign.tenant_id == tenant_id)
            .order_by(MessageCampaign.year.desc(), MessageCampaign.month.desc())
        )
    ).scalars().all()
    employees = (
        await db.execute(select(Employee).where(Employee.tenant_id == tenant_id, Employee.is_active == True))
    ).scalars().all()
    contracts = (
        await db.execute(
            select(Contract).where(Contract.tenant_id == tenant_id, Contract.is_active == True)
        )
    ).scalars().all()
    now = datetime.now()
    # default_month = następny miesiąc (zbieramy grafik na przyszły miesiąc)
    if now.month == 12:
        default_year, default_month = now.year + 1, 1
    else:
        default_year, default_month = now.year, now.month + 1
    return templates.TemplateResponse("admin/campaigns.html", {
        "request": request, "tenant": tenant, "campaigns": campaigns,
        "employees": employees, "contracts": contracts,
        "now": now, "default_year": default_year, "default_month": default_month,
        "month_names": MONTH_NAMES_PL
    })


@router.post("/admin/{tenant_id}/campaigns/create")
async def create_campaign(
    tenant_id: int,
    year: int = Form(...),
    month: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    existing = (await db.execute(
        select(MessageCampaign).where(
            MessageCampaign.tenant_id == tenant_id,
            MessageCampaign.year == year,
            MessageCampaign.month == month,
        )
    )).scalar_one_or_none()
    if not existing:
        campaign = MessageCampaign(tenant_id=tenant_id, year=year, month=month)
        db.add(campaign)
        await db.commit()
        return RedirectResponse(f"/admin/{tenant_id}/campaigns", status_code=303)
    return RedirectResponse(f"/admin/{tenant_id}/campaigns?error=exists", status_code=303)


@router.post("/admin/{tenant_id}/campaigns/{campaign_id}/send")
async def send_campaign(
    request: Request,
    tenant_id: int,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Wysyła wiadomości WhatsApp do aktywnych pracowników (opcjonalnie filtrowanych po kontraktach)."""
    campaign = await db.get(MessageCampaign, campaign_id)
    if not campaign or campaign.tenant_id != tenant_id:
        raise HTTPException(404)

    # Odczytaj contract_ids z form data (może być wiele wartości)
    form = await request.form()
    raw_contract_ids = form.getlist("contract_ids")
    contract_ids: List[int] = [int(c) for c in raw_contract_ids if c]

    if contract_ids:
        # Pobierz pracowników przypisanych do wybranych kontraktów
        rows = (
            await db.execute(
                select(Employee)
                .join(ContractEmployee, ContractEmployee.employee_id == Employee.id)
                .where(
                    Employee.tenant_id == tenant_id,
                    Employee.is_active == True,
                    ContractEmployee.contract_id.in_(contract_ids),
                )
                .distinct()
            )
        ).scalars().all()
        employees = rows
    else:
        # Wszyscy aktywni pracownicy tenanta
        employees = (
            await db.execute(
                select(Employee).where(Employee.tenant_id == tenant_id, Employee.is_active == True)
            )
        ).scalars().all()

    # Pobierz ustawienia tenanta (szablon wiadomości)
    tenant_settings = (
        await db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()

    month_name = MONTH_NAMES_PL.get(campaign.month, str(campaign.month))
    message_template = (
        tenant_settings.initial_message
        if tenant_settings
        else DEFAULT_INITIAL_MESSAGE
    )

    sent, failed = 0, 0
    for emp in employees:
        if not emp.phone_whatsapp:
            continue
        message = render_template(message_template, emp, month_name, emp.token)
        result = await send_whatsapp(emp.phone_whatsapp, message)
        log = MessageLog(
            campaign_id=campaign_id,
            employee_id=emp.id,
            channel=MessageChannel.whatsapp,
            phone_or_email=emp.phone_whatsapp,
            status=result["status"],
            external_id=result.get("external_id"),
            error_message=result.get("error"),
        )
        db.add(log)
        if result["status"] == "sent":
            sent += 1
        else:
            failed += 1

    campaign.status = CampaignStatus.sent
    campaign.sent_at = datetime.now()
    await db.commit()

    return JSONResponse({"sent": sent, "failed": failed})


@router.post("/admin/{tenant_id}/campaigns/{campaign_id}/delete")
async def delete_campaign(tenant_id: int, campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(MessageCampaign, campaign_id)
    if campaign and campaign.tenant_id == tenant_id:
        await db.delete(campaign)
        await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/campaigns", status_code=303)


# ============================================================
# ADMIN — Ustawienia
# ============================================================

@router.get("/admin/{tenant_id}/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request, tenant_id: int, db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    settings = (
        await db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if not settings:
        settings = TenantSettings(
            tenant_id=tenant_id,
            initial_message=DEFAULT_INITIAL_MESSAGE,
            reminder_message=DEFAULT_REMINDER_MESSAGE,
            reminder_days=3,
            reminder_2_message=DEFAULT_REMINDER_2_MESSAGE,
            reminder_2_days=1,
        )
    saved = request.query_params.get("saved") == "1"
    return templates.TemplateResponse("admin/settings.html", {
        "request": request, "tenant": tenant, "settings": settings, "saved": saved
    })


@router.post("/admin/{tenant_id}/settings")
async def save_settings(
    tenant_id: int,
    initial_message: str = Form(...),
    reminder_message: str = Form(...),
    reminder_days: int = Form(3),
    reminder_2_message: str = Form(""),
    reminder_2_days: int = Form(1),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    settings = (
        await db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if settings:
        settings.initial_message = initial_message
        settings.reminder_message = reminder_message
        settings.reminder_days = reminder_days
        settings.reminder_2_message = reminder_2_message or None
        settings.reminder_2_days = reminder_2_days
    else:
        settings = TenantSettings(
            tenant_id=tenant_id,
            initial_message=initial_message,
            reminder_message=reminder_message,
            reminder_days=reminder_days,
            reminder_2_message=reminder_2_message or None,
            reminder_2_days=reminder_2_days,
        )
        db.add(settings)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/settings?saved=1", status_code=303)


# ============================================================
# ADMIN — Status grafików
# ============================================================

@router.get("/admin/{tenant_id}/schedules", response_class=HTMLResponse)
async def admin_schedules(
    request: Request, tenant_id: int,
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    now = datetime.now()

    query = (
        select(ScheduleSubmission)
        .join(Employee)
        .where(Employee.tenant_id == tenant_id)
        .options(selectinload(ScheduleSubmission.employee), selectinload(ScheduleSubmission.days))
        .order_by(ScheduleSubmission.submitted_at.desc())
    )
    if employee_id:
        query = query.where(ScheduleSubmission.employee_id == employee_id)

    submissions = (await db.execute(query)).scalars().all()

    employees = (await db.execute(
        select(Employee)
        .where(Employee.tenant_id == tenant_id, Employee.is_active == True)
        .order_by(Employee.last_name, Employee.first_name)
    )).scalars().all()

    return templates.TemplateResponse("admin/schedules.html", {
        "request": request, "tenant": tenant, "submissions": submissions,
        "now": now, "month_names": MONTH_NAMES_PL,
        "employees": employees, "selected_employee_id": employee_id,
    })


@router.get("/admin/{tenant_id}/employees/{employee_id}/schedule/pdf", response_class=HTMLResponse)
async def employee_schedule_pdf(
    request: Request, tenant_id: int, employee_id: int,
    year: int = None, month: int = None,
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise HTTPException(404)

    now = datetime.now()
    if year is None or month is None:
        if now.month == 12:
            year, month = now.year + 1, 1
        else:
            year, month = now.year, now.month + 1

    submission = (await db.execute(
        select(ScheduleSubmission)
        .where(
            ScheduleSubmission.employee_id == employee_id,
            ScheduleSubmission.year == year,
            ScheduleSubmission.month == month,
        )
        .options(selectinload(ScheduleSubmission.days))
    )).scalar_one_or_none()

    num_days = calendar.monthrange(year, month)[1]
    days = [date(year, month, d) for d in range(1, num_days + 1)]
    holidays = get_polish_holidays(year)
    holidays_iso = {d.isoformat(): name for d, name in holidays.items() if d.month == month}

    day_map = {}
    if submission:
        for d in submission.days:
            day_map[d.date.isoformat()] = d

    return templates.TemplateResponse("admin/schedule_pdf.html", {
        "request": request,
        "tenant": tenant,
        "employee": emp,
        "submission": submission,
        "days": days,
        "holidays_iso": holidays_iso,
        "day_map": day_map,
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES_PL.get(month, ""),
        "now": now,
    })


# ============================================================
# EMPLOYEE — Formularz grafiku
# ============================================================

@router.get("/schedule/{token}", response_class=HTMLResponse)
async def employee_schedule(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    emp = (await db.execute(select(Employee).where(Employee.token == token))).scalar_one_or_none()
    if not emp or not emp.is_active:
        raise HTTPException(404, "Link jest nieprawidłowy lub wygasł.")

    now = datetime.now()
    # Grafik na następny miesiąc
    if now.month == 12:
        year, month = now.year + 1, 1
    else:
        year, month = now.year, now.month + 1

    # Czy już wypełniony?
    existing = (await db.execute(
        select(ScheduleSubmission).where(
            ScheduleSubmission.employee_id == emp.id,
            ScheduleSubmission.year == year,
            ScheduleSubmission.month == month,
        ).options(selectinload(ScheduleSubmission.days))
    )).scalar_one_or_none()

    # Dni miesiąca
    num_days = calendar.monthrange(year, month)[1]
    days = [date(year, month, d) for d in range(1, num_days + 1)]
    days_iso = [d.isoformat() for d in days]
    days_weekday = [d.weekday() for d in days]
    holidays = get_polish_holidays(year)
    holidays_iso = {d.isoformat(): name for d, name in holidays.items() if d.month == month}

    existing_days = {}
    if existing:
        for d in existing.days:
            existing_days[d.date.isoformat()] = {"status": d.status.value, "from": d.hour_from, "to": d.hour_to}

    return templates.TemplateResponse("employee/schedule.html", {
        "request": request,
        "employee": emp,
        "year": year,
        "month": month,
        "days_iso": days_iso,
        "days_weekday": days_weekday,
        "holidays_iso": holidays_iso,
        "month_name": MONTH_NAMES_PL.get(month, ""),
        "days": days,
        "existing": existing,
        "existing_days": existing_days,
    })


@router.post("/schedule/{token}")
async def submit_schedule(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    emp = (await db.execute(select(Employee).where(Employee.token == token))).scalar_one_or_none()
    if not emp or not emp.is_active:
        raise HTTPException(404)

    now = datetime.now()
    if now.month == 12:
        year, month = now.year + 1, 1
    else:
        year, month = now.year, now.month + 1

    # Jeśli grafik już wysłany — odrzuć (blokada edycji)
    existing = (await db.execute(
        select(ScheduleSubmission).where(
            ScheduleSubmission.employee_id == emp.id,
            ScheduleSubmission.year == year,
            ScheduleSubmission.month == month,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(403, "Grafik został już wysłany. Skontaktuj się z koordynatorem.")

    form = await request.form()

    submission = ScheduleSubmission(
        employee_id=emp.id,
        year=year,
        month=month,
        notes=form.get("notes", ""),
    )
    db.add(submission)
    await db.flush()

    num_days = calendar.monthrange(year, month)[1]
    for d in range(1, num_days + 1):
        day_date = date(year, month, d)
        status_val = form.get(f"day_{d}", "unavailable")
        try:
            status = AvailabilityStatus(status_val)
        except ValueError:
            status = AvailabilityStatus.unavailable

        hour_from = form.get(f"from_{d}", None) or None
        hour_to = form.get(f"to_{d}", None) or None

        day_entry = AvailabilityDay(
            submission_id=submission.id,
            date=day_date,
            status=status,
            hour_from=hour_from if status == AvailabilityStatus.partial else None,
            hour_to=hour_to if status == AvailabilityStatus.partial else None,
        )
        db.add(day_entry)

    await db.commit()
    return templates.TemplateResponse("employee/thank_you.html", {
        "request": request,
        "employee": emp,
        "month_name": MONTH_NAMES_PL.get(month, ""),
        "year": year,
    })


# ============================================================
# SETUP — Szybkie tworzenie tenanta (tylko dev)
# ============================================================

@router.post("/setup/tenant")
async def setup_tenant(name: str = Form(...), slug: str = Form(...), db: AsyncSession = Depends(get_db)):
    tenant = Tenant(name=name, slug=slug)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return RedirectResponse(f"/admin/{tenant.id}/contracts", status_code=303)
