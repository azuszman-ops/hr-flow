from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import date, datetime, timedelta
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
    MessageTemplate, MessageCampaign, MessageLog, MessageChannel, CampaignStatus
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
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "tenants": tenants})


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
    db: AsyncSession = Depends(get_db)
):
    contract = Contract(tenant_id=tenant_id, name=name, description=description)
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
    now = datetime.now()
    return templates.TemplateResponse("admin/campaigns.html", {
        "request": request, "tenant": tenant, "campaigns": campaigns,
        "employees": employees, "now": now, "month_names": MONTH_NAMES_PL
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
async def send_campaign(tenant_id: int, campaign_id: int, db: AsyncSession = Depends(get_db)):
    """Wysyła wiadomości WhatsApp do wszystkich aktywnych pracowników tenanta."""
    campaign = await db.get(MessageCampaign, campaign_id)
    if not campaign or campaign.tenant_id != tenant_id:
        raise HTTPException(404)

    employees = (
        await db.execute(
            select(Employee).where(Employee.tenant_id == tenant_id, Employee.is_active == True)
        )
    ).scalars().all()

    month_name = MONTH_NAMES_PL.get(campaign.month, str(campaign.month))
    message_template = (
        f"Dzień dobry {{first_name}}! 👋\n\n"
        f"Prosimy o uzupełnienie grafiku dostępności na {month_name} {campaign.year}.\n\n"
        f"Kliknij link poniżej i zajmie to tylko chwilę:\n{{schedule_link}}\n\n"
        f"Dziękujemy!"
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


# ============================================================
# ADMIN — Status grafików
# ============================================================

@router.get("/admin/{tenant_id}/schedules", response_class=HTMLResponse)
async def admin_schedules(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    now = datetime.now()
    submissions = (
        await db.execute(
            select(ScheduleSubmission)
            .join(Employee)
            .where(Employee.tenant_id == tenant_id)
            .options(selectinload(ScheduleSubmission.employee), selectinload(ScheduleSubmission.days))
            .order_by(ScheduleSubmission.submitted_at.desc())
        )
    ).scalars().all()
    return templates.TemplateResponse("admin/schedules.html", {
        "request": request, "tenant": tenant, "submissions": submissions,
        "now": now, "month_names": MONTH_NAMES_PL
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

    form = await request.form()
    now = datetime.now()
    if now.month == 12:
        year, month = now.year + 1, 1
    else:
        year, month = now.year, now.month + 1

    # Usuń stare wpisy jeśli istnieją
    existing = (await db.execute(
        select(ScheduleSubmission).where(
            ScheduleSubmission.employee_id == emp.id,
            ScheduleSubmission.year == year,
            ScheduleSubmission.month == month,
        )
    )).scalar_one_or_none()
    if existing:
        await db.execute(delete(AvailabilityDay).where(AvailabilityDay.submission_id == existing.id))
        await db.delete(existing)
        await db.flush()

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
