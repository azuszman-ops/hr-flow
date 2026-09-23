"""
Moduł Onboarding (Find Work, wrzesień 2026).

Osobny router, osobne modele (app/models_onboarding.py), osobne szablony
(app/templates/onboarding/). Z istniejącego kodu korzysta tylko przez import:
get_db, get_authed_tenant, Tenant, Employee, send_whatsapp, validate_phone.

Trasy admina:  /admin/{tenant_id}/onboarding/...
Trasy pracownika: /o/{slug}/...
"""
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_authed_tenant
from app.models import Tenant, Employee
from app.models_onboarding import (
    OnboardingSettings, OnboardingSegment, OnboardingModule, OnboardingModuleTranslation,
    OnboardingAttachment, OnboardingPerson, OnboardingAck, OnboardingLogin, OnboardingMessage,
)
from app.services.messaging import send_whatsapp, validate_phone
from app.services.onboarding_i18n import (
    t, normalize_lang, modules_count, LANG_LABELS, LANG_NAMES, SUPPORTED_LANGS, READY_LANGS,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
WARSAW = ZoneInfo("Europe/Warsaw")

TEMPLATE_ONBOARDING = os.getenv("ONBOARDING_TEMPLATE_SID")   # Twilio Content Template SID (po akceptacji Meta)
STAFF_KEY = os.getenv("ONBOARDING_STAFF_KEY")               # odblokowuje edytor treści dla Scaling Labs
MAX_UPLOAD = 8 * 1024 * 1024                                 # 8 MB na plik
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------
def fmt_dt(value: datetime | None, with_time: bool = True) -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    local = value.astimezone(WARSAW)
    return local.strftime("%d.%m.%Y, %H:%M") if with_time else local.strftime("%d.%m.%Y")


FILE_MARKER = re.compile(r"^\[(?:plik|zdjęcie|zdjecie|file)\s+(\d+)\]$", re.IGNORECASE)


def _block_html(block: str) -> str:
    lines = [ln.rstrip() for ln in block.split("\n") if ln.strip()]
    if not lines:
        return ""
    if all(ln.lstrip().startswith("- ") for ln in lines):
        items = "".join(f"<li>{escape(ln.lstrip()[2:])}</li>" for ln in lines)
        return f"<ul class='ob-list'>{items}</ul>"
    # Pojedyncza krótka linia bez kropki na końcu = śródtytuł
    if len(lines) == 1 and len(lines[0]) <= 60 and not lines[0].rstrip()[-1:] in ".?!:;,":
        return f"<h3 class='ob-h3'>{escape(lines[0])}</h3>"
    return f"<p>{'<br>'.join(str(escape(ln)) for ln in lines)}</p>"


def render_parts(text: str, attachments: list | None = None) -> list[dict]:
    """Prosty tekst -> lista części do szablonu.
    Akapity po pustej linii, linie „- " jako lista, krótka linia bez kropki jako śródtytuł,
    „[plik 2]" w osobnej linii wstawia drugi załącznik w tym miejscu. Nieużyte załączniki idą na koniec.
    """
    attachments = list(attachments or [])
    used, parts = set(), []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        m = FILE_MARKER.match(block.strip())
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(attachments):
                parts.append({"type": "file", "att": attachments[idx]})
                used.add(idx)
            continue
        html = _block_html(block)
        if html:
            parts.append({"type": "html", "html": Markup(html)})
    for i, att in enumerate(attachments):
        if i not in used:
            parts.append({"type": "file", "att": att})
    return parts


def render_body(text: str) -> Markup:
    """Prosty tekst -> HTML (bez załączników). Wszystko escapowane."""
    return Markup("".join(str(p["html"]) for p in render_parts(text) if p["type"] == "html"))


templates.env.filters["ob_body"] = render_body
templates.env.filters["ob_dt"] = fmt_dt
templates.env.filters["ob_date"] = lambda v: fmt_dt(v, with_time=False)
templates.env.globals["LANG_LABELS"] = LANG_LABELS
templates.env.globals["LANG_NAMES"] = LANG_NAMES
templates.env.globals["SUPPORTED_LANGS"] = SUPPORTED_LANGS
templates.env.globals["MONTHS_PL"] = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]


def normalize_phone(raw: str) -> str:
    """'600 123 456' / '0048600123456' / '+48 600-123-456' -> '+48600123456'."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:
        digits = "48" + digits
    return f"+{digits}" if digits else ""


def parse_code(raw: str) -> tuple[int, int] | None:
    """'0803' / '8.03' / '08-03' / '8/3' -> (8, 3)."""
    raw = (raw or "").strip()
    m = re.fullmatch(r"(\d{1,2})\D+(\d{1,2})", raw)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
    else:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 4:
            d, mo = int(digits[:2]), int(digits[2:])
        elif len(digits) == 3:
            d, mo = int(digits[0]), int(digits[1:])
        else:
            return None
    if 1 <= d <= 31 and 1 <= mo <= 12:
        return d, mo
    return None


def build_login_link(slug: str, token: str | None = None) -> str:
    base = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    url = f"{base}/o/{slug}"
    return f"{url}?t={token}" if token else url


_SCHEMA_READY = False


async def _ensure_schema(db: AsyncSession):
    """Kolumny dodane po pierwszym wdrożeniu (create_all nie dodaje kolumn). Idempotentne, raz na proces."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    await db.execute(text("ALTER TABLE onboarding_settings ADD COLUMN IF NOT EXISTS help_phone VARCHAR(40)"))
    await db.commit()
    _SCHEMA_READY = True


async def get_settings(db: AsyncSession, tenant: Tenant) -> OnboardingSettings:
    await _ensure_schema(db)
    s = (await db.execute(
        select(OnboardingSettings).where(OnboardingSettings.tenant_id == tenant.id)
    )).scalar_one_or_none()
    if not s:
        s = OnboardingSettings(tenant_id=tenant.id, brand_name=tenant.name)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


def is_staff(request: Request, tenant_id: int) -> bool:
    return bool(request.session.get(f"ob_staff_{tenant_id}"))


def can_edit(request: Request, tenant_id: int, settings: OnboardingSettings) -> bool:
    return settings.editor_enabled or is_staff(request, tenant_id)


async def load_persons(db: AsyncSession, tenant_id: int) -> list[OnboardingPerson]:
    return (await db.execute(
        select(OnboardingPerson)
        .where(OnboardingPerson.tenant_id == tenant_id)
        .options(
            selectinload(OnboardingPerson.employee),
            selectinload(OnboardingPerson.segment).selectinload(OnboardingSegment.modules),
            selectinload(OnboardingPerson.acks),
        )
        .order_by(OnboardingPerson.created_at.desc())
    )).scalars().all()


def person_progress(p: OnboardingPerson) -> dict:
    modules = [m for m in (p.segment.modules if p.segment else []) if m.is_active]
    module_ids = {m.id for m in modules}
    acked = len([a for a in p.acks if a.module_id in module_ids])
    total = len(modules)
    if p.completed_at:
        status, label = "done", f"Ukończony {fmt_dt(p.completed_at, False)}"
    elif p.first_login_at:
        status, label = "progress", "W trakcie"
    elif p.link_sent_at:
        status, label = "sent", f"Link wysłany {fmt_dt(p.link_sent_at, False)}"
    else:
        status, label = "new", "Nie wysłano"
    pct = int(acked * 100 / total) if total else 0
    return {"acked": acked, "total": total, "pct": pct, "status": status, "label": label}


async def load_segments(db: AsyncSession, tenant_id: int, active_only: bool = False) -> list[OnboardingSegment]:
    q = (select(OnboardingSegment)
         .where(OnboardingSegment.tenant_id == tenant_id)
         .options(selectinload(OnboardingSegment.modules).selectinload(OnboardingModule.attachments))
         .order_by(OnboardingSegment.sort_order, OnboardingSegment.id))
    if active_only:
        q = q.where(OnboardingSegment.is_active == True)
    return (await db.execute(q)).scalars().all()


async def get_person_or_404(db: AsyncSession, tenant_id: int, person_id: int) -> OnboardingPerson:
    p = (await db.execute(
        select(OnboardingPerson)
        .where(OnboardingPerson.id == person_id, OnboardingPerson.tenant_id == tenant_id)
        .options(
            selectinload(OnboardingPerson.employee),
            selectinload(OnboardingPerson.segment).selectinload(OnboardingSegment.modules),
            selectinload(OnboardingPerson.acks).selectinload(OnboardingAck.module),
            selectinload(OnboardingPerson.logins),
            selectinload(OnboardingPerson.messages),
        )
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(404)
    return p


async def send_link(db: AsyncSession, tenant: Tenant, person: OnboardingPerson, settings: OnboardingSettings) -> dict:
    emp = person.employee
    if not validate_phone(emp.phone_whatsapp or ""):
        return {"status": "failed", "error": "Brak poprawnego numeru WhatsApp (format +48...)."}
    if not TEMPLATE_ONBOARDING:
        return {"status": "failed", "error": "Szablon WhatsApp nie jest jeszcze skonfigurowany (ONBOARDING_TEMPLATE_SID)."}
    # Szablon Meta (findwork_wprowadzenie_pl_v3): {{1}} imię, {{2}} token osoby. Adres strony jest wpisany
    # na stałe w treści szablonu (Meta odrzuca cały URL jako zmienną), więc zmiana domeny = nowy szablon.
    result = await send_whatsapp(emp.phone_whatsapp, TEMPLATE_ONBOARDING, {"1": emp.first_name, "2": emp.token})
    db.add(OnboardingMessage(
        person_id=person.id, phone=emp.phone_whatsapp, status=result["status"],
        external_id=result.get("external_id"), error_message=result.get("error"),
    ))
    if result["status"] == "sent":
        person.link_sent_at = datetime.now(WARSAW)
        person.link_sent_count = (person.link_sent_count or 0) + 1
    await db.commit()
    return result


# ===========================================================================
# ADMIN: osoby
# ===========================================================================
@router.get("/admin/{tenant_id}/onboarding", response_class=HTMLResponse)
async def ob_admin_list(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db),
                        tenant: Tenant = Depends(get_authed_tenant)):
    settings = await get_settings(db, tenant)
    persons = await load_persons(db, tenant_id)
    segments = await load_segments(db, tenant_id, active_only=True)
    rows = [{"p": p, "pr": person_progress(p)} for p in persons]
    employees = (await db.execute(
        select(Employee).where(Employee.tenant_id == tenant_id, Employee.is_active == True)
        .order_by(Employee.last_name, Employee.first_name)
    )).scalars().all()
    in_ob = {p.employee_id for p in persons}
    stats = {
        "total": len(rows),
        "done": len([r for r in rows if r["pr"]["status"] == "done"]),
        "progress": len([r for r in rows if r["pr"]["status"] == "progress"]),
        "sent": len([r for r in rows if r["pr"]["status"] == "sent"]),
        "new": len([r for r in rows if r["pr"]["status"] == "new"]),
    }
    return templates.TemplateResponse("onboarding/admin_list.html", {
        "request": request, "tenant": tenant, "settings": settings, "rows": rows,
        "segments": segments, "employees": [e for e in employees if e.id not in in_ob],
        "stats": stats, "can_edit": can_edit(request, tenant_id, settings),
        "login_url": build_login_link(tenant.slug), "template_ready": bool(TEMPLATE_ONBOARDING),
        "msg": request.query_params.get("msg", ""), "err": request.query_params.get("err", ""),
    })


@router.post("/admin/{tenant_id}/onboarding/persons")
async def ob_admin_create_person(
    request: Request, tenant_id: int,
    employee_id: int = Form(None),
    first_name: str = Form(""), last_name: str = Form(""), phone_whatsapp: str = Form(""),
    birth_day: int = Form(...), birth_month: int = Form(...),
    segment_id: int = Form(None), language: str = Form("pl"), first_day_info: str = Form(""),
    db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant),
):
    if not (1 <= birth_day <= 31 and 1 <= birth_month <= 12):
        return RedirectResponse(f"/admin/{tenant_id}/onboarding?err=Nieprawidłowa+data+urodzenia", status_code=303)

    emp = None
    if employee_id:
        emp = await db.get(Employee, employee_id)
        if not emp or emp.tenant_id != tenant_id:
            raise HTTPException(404)
    else:
        phone = normalize_phone(phone_whatsapp)
        if not first_name.strip() or not last_name.strip() or not phone:
            return RedirectResponse(f"/admin/{tenant_id}/onboarding?err=Podaj+imię,+nazwisko+i+numer+telefonu", status_code=303)
        # Ten sam numer = ta sama osoba (lista pracowników HR-Flow)
        emp = (await db.execute(
            select(Employee).where(Employee.tenant_id == tenant_id, Employee.phone_whatsapp == phone)
        )).scalars().first()
        if not emp:
            emp = Employee(tenant_id=tenant_id, first_name=first_name.strip(),
                           last_name=last_name.strip(), phone_whatsapp=phone)
            db.add(emp)
            await db.flush()

    existing = (await db.execute(
        select(OnboardingPerson).where(OnboardingPerson.employee_id == emp.id)
    )).scalar_one_or_none()
    if existing:
        return RedirectResponse(f"/admin/{tenant_id}/onboarding?err=Ta+osoba+jest+już+w+onboardingu", status_code=303)

    db.add(OnboardingPerson(
        tenant_id=tenant_id, employee_id=emp.id, segment_id=segment_id or None,
        language=normalize_lang(language), birth_day=birth_day, birth_month=birth_month,
        first_day_info=first_day_info.strip() or None,
    ))
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding?msg=Dodano+{emp.first_name}+{emp.last_name}", status_code=303)


@router.get("/admin/{tenant_id}/onboarding/persons/{person_id}", response_class=HTMLResponse)
async def ob_admin_person(request: Request, tenant_id: int, person_id: int,
                          db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    settings = await get_settings(db, tenant)
    p = await get_person_or_404(db, tenant_id, person_id)
    segments = await load_segments(db, tenant_id, active_only=True)
    modules = [m for m in (p.segment.modules if p.segment else []) if m.is_active]
    acks_by_module = {a.module_id: a for a in p.acks}
    register = [{"m": m, "ack": acks_by_module.get(m.id)} for m in modules]
    return templates.TemplateResponse("onboarding/admin_person.html", {
        "request": request, "tenant": tenant, "settings": settings, "p": p, "pr": person_progress(p),
        "segments": segments, "register": register, "login_url": build_login_link(tenant.slug, p.employee.token),
        "template_ready": bool(TEMPLATE_ONBOARDING),
        "msg": request.query_params.get("msg", ""), "err": request.query_params.get("err", ""),
    })


@router.post("/admin/{tenant_id}/onboarding/persons/{person_id}/edit")
async def ob_admin_person_edit(
    tenant_id: int, person_id: int,
    birth_day: int = Form(...), birth_month: int = Form(...),
    segment_id: int = Form(None), language: str = Form("pl"), first_day_info: str = Form(""),
    phone_whatsapp: str = Form(""),
    db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant),
):
    p = await get_person_or_404(db, tenant_id, person_id)
    if 1 <= birth_day <= 31 and 1 <= birth_month <= 12:
        p.birth_day, p.birth_month = birth_day, birth_month
    p.segment_id = segment_id or None
    p.language = normalize_lang(language)
    p.first_day_info = first_day_info.strip() or None
    phone = normalize_phone(phone_whatsapp)
    if phone:
        p.employee.phone_whatsapp = phone
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/persons/{person_id}?msg=Zapisano", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/persons/{person_id}/delete")
async def ob_admin_person_delete(tenant_id: int, person_id: int, db: AsyncSession = Depends(get_db),
                                 tenant: Tenant = Depends(get_authed_tenant)):
    p = await get_person_or_404(db, tenant_id, person_id)
    await db.delete(p)   # pracownik zostaje na liście HR-Flow, znika tylko z onboardingu
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding?msg=Usunięto+z+onboardingu", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/persons/{person_id}/send")
async def ob_admin_person_send(tenant_id: int, person_id: int, db: AsyncSession = Depends(get_db),
                               tenant: Tenant = Depends(get_authed_tenant)):
    settings = await get_settings(db, tenant)
    p = await get_person_or_404(db, tenant_id, person_id)
    result = await send_link(db, tenant, p, settings)
    return JSONResponse({"status": result["status"], "error": result.get("error", "")})


@router.post("/admin/{tenant_id}/onboarding/send-all")
async def ob_admin_send_all(tenant_id: int, db: AsyncSession = Depends(get_db),
                            tenant: Tenant = Depends(get_authed_tenant)):
    """Wysyła link do wszystkich, którzy jeszcze go nie dostali."""
    settings = await get_settings(db, tenant)
    persons = await load_persons(db, tenant_id)
    sent, failed, errors = 0, 0, []
    for p in persons:
        if p.link_sent_at or not p.segment_id:
            continue
        r = await send_link(db, tenant, p, settings)
        if r["status"] == "sent":
            sent += 1
        else:
            failed += 1
            errors.append(f"{p.employee.first_name} {p.employee.last_name}: {r.get('error', '')}")
        if r["status"] == "rate_limited":
            break
    return JSONResponse({"sent": sent, "failed": failed, "errors": errors[:10]})


@router.post("/admin/{tenant_id}/onboarding/persons/{person_id}/preview")
async def ob_admin_preview(request: Request, tenant_id: int, person_id: int,
                           db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    """Podgląd strony pracownika oczami tej osoby (bez logowania kodem, bez wpisu w rejestrze)."""
    p = await get_person_or_404(db, tenant_id, person_id)
    request.session[f"ob_emp_{tenant_id}"] = p.id
    request.session[f"ob_lang_{tenant_id}"] = p.language
    return RedirectResponse(f"/o/{tenant.slug}/start", status_code=303)


# ===========================================================================
# ADMIN: edytor treści (staff albo pakiet Rozszerzony)
# ===========================================================================
@router.get("/admin/{tenant_id}/onboarding/staff")
async def ob_admin_staff(request: Request, tenant_id: int, key: str = "",
                         tenant: Tenant = Depends(get_authed_tenant)):
    if not STAFF_KEY or key != STAFF_KEY:
        raise HTTPException(403)
    request.session[f"ob_staff_{tenant_id}"] = True
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments", status_code=303)


async def require_editor(request: Request, tenant_id: int, db: AsyncSession, tenant: Tenant) -> OnboardingSettings:
    settings = await get_settings(db, tenant)
    if not can_edit(request, tenant_id, settings):
        raise HTTPException(403, "Edycja treści nie jest włączona w tym pakiecie.")
    return settings


@router.get("/admin/{tenant_id}/onboarding/segments", response_class=HTMLResponse)
async def ob_admin_segments(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db),
                            tenant: Tenant = Depends(get_authed_tenant)):
    settings = await require_editor(request, tenant_id, db, tenant)
    segments = await load_segments(db, tenant_id)
    counts = dict((await db.execute(
        select(OnboardingPerson.segment_id, func.count(OnboardingPerson.id))
        .where(OnboardingPerson.tenant_id == tenant_id).group_by(OnboardingPerson.segment_id)
    )).all())
    return templates.TemplateResponse("onboarding/admin_segments.html", {
        "request": request, "tenant": tenant, "settings": settings, "segments": segments,
        "counts": counts, "can_edit": True, "is_staff": is_staff(request, tenant_id),
        "msg": request.query_params.get("msg", ""), "err": request.query_params.get("err", ""),
    })


@router.post("/admin/{tenant_id}/onboarding/segments")
async def ob_admin_segment_create(request: Request, tenant_id: int, name: str = Form(...),
                                  description: str = Form(""), db: AsyncSession = Depends(get_db),
                                  tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    n = (await db.execute(select(func.count(OnboardingSegment.id))
                          .where(OnboardingSegment.tenant_id == tenant_id))).scalar() or 0
    seg = OnboardingSegment(tenant_id=tenant_id, name=name.strip(), description=description.strip() or None,
                            sort_order=n + 1)
    db.add(seg)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{seg.id}", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/segments/{segment_id}/edit")
async def ob_admin_segment_edit(request: Request, tenant_id: int, segment_id: int, name: str = Form(...),
                                description: str = Form(""), is_active: str = Form("on"),
                                db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    seg = await db.get(OnboardingSegment, segment_id)
    if not seg or seg.tenant_id != tenant_id:
        raise HTTPException(404)
    seg.name, seg.description, seg.is_active = name.strip(), description.strip() or None, is_active == "on"
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{segment_id}?msg=Zapisano", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/segments/{segment_id}/delete")
async def ob_admin_segment_delete(request: Request, tenant_id: int, segment_id: int,
                                  db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    seg = await db.get(OnboardingSegment, segment_id)
    if not seg or seg.tenant_id != tenant_id:
        raise HTTPException(404)
    await db.delete(seg)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments?msg=Usunięto+segment", status_code=303)


@router.get("/admin/{tenant_id}/onboarding/segments/{segment_id}", response_class=HTMLResponse)
async def ob_admin_segment(request: Request, tenant_id: int, segment_id: int,
                           db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    settings = await require_editor(request, tenant_id, db, tenant)
    seg = (await db.execute(
        select(OnboardingSegment).where(OnboardingSegment.id == segment_id, OnboardingSegment.tenant_id == tenant_id)
        .options(selectinload(OnboardingSegment.modules).selectinload(OnboardingModule.attachments),
                 selectinload(OnboardingSegment.modules).selectinload(OnboardingModule.translations))
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(404)
    return templates.TemplateResponse("onboarding/admin_segment.html", {
        "request": request, "tenant": tenant, "settings": settings, "seg": seg, "can_edit": True,
        "msg": request.query_params.get("msg", ""), "err": request.query_params.get("err", ""),
    })


async def _store_uploads(db: AsyncSession, module: OnboardingModule, files: list[UploadFile], order: int = 0) -> list[str]:
    errors = []
    for f in files or []:
        if not f or not f.filename:
            continue
        data = await f.read()
        ctype = (f.content_type or "").lower()
        if ctype not in ALLOWED_TYPES:
            errors.append(f"{f.filename}: dozwolone są zdjęcia (JPG, PNG, WEBP) i PDF")
            continue
        if len(data) > MAX_UPLOAD:
            errors.append(f"{f.filename}: plik większy niż 8 MB")
            continue
        order += 1
        db.add(OnboardingAttachment(module_id=module.id, filename=f.filename, content_type=ctype,
                                    size=len(data), data=data, sort_order=order))
    return errors


@router.post("/admin/{tenant_id}/onboarding/segments/{segment_id}/modules")
async def ob_admin_module_create(request: Request, tenant_id: int, segment_id: int,
                                 title: str = Form(...), body: str = Form(""), estimated_minutes: int = Form(None),
                                 files: list[UploadFile] = File(None),
                                 db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    seg = await db.get(OnboardingSegment, segment_id)
    if not seg or seg.tenant_id != tenant_id:
        raise HTTPException(404)
    n = (await db.execute(select(func.count(OnboardingModule.id))
                          .where(OnboardingModule.segment_id == segment_id))).scalar() or 0
    mod = OnboardingModule(segment_id=segment_id, title=title.strip(), body=body.strip(),
                           estimated_minutes=estimated_minutes or None, sort_order=n + 1)
    db.add(mod)
    await db.flush()
    errors = await _store_uploads(db, mod, files, order=0)
    await db.commit()
    q = "?err=" + "; ".join(errors) if errors else "?msg=Dodano+moduł"
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{segment_id}{q}", status_code=303)


async def _get_module(db: AsyncSession, tenant_id: int, module_id: int) -> OnboardingModule:
    mod = (await db.execute(
        select(OnboardingModule).join(OnboardingSegment)
        .where(OnboardingModule.id == module_id, OnboardingSegment.tenant_id == tenant_id)
        .options(selectinload(OnboardingModule.attachments), selectinload(OnboardingModule.translations),
                 selectinload(OnboardingModule.segment))
    )).scalar_one_or_none()
    if not mod:
        raise HTTPException(404)
    return mod


@router.post("/admin/{tenant_id}/onboarding/modules/{module_id}/edit")
async def ob_admin_module_edit(request: Request, tenant_id: int, module_id: int,
                               title: str = Form(...), body: str = Form(""), estimated_minutes: int = Form(None),
                               files: list[UploadFile] = File(None),
                               db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    mod = await _get_module(db, tenant_id, module_id)
    mod.title, mod.body, mod.estimated_minutes = title.strip(), body.strip(), estimated_minutes or None
    errors = await _store_uploads(db, mod, files, order=len(mod.attachments))
    await db.commit()
    q = "?err=" + "; ".join(errors) if errors else "?msg=Zapisano+moduł"
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{mod.segment_id}{q}#m{module_id}", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/modules/{module_id}/translation")
async def ob_admin_module_translation(request: Request, tenant_id: int, module_id: int,
                                      lang: str = Form(...), title: str = Form(""), body: str = Form(""),
                                      db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    mod = await _get_module(db, tenant_id, module_id)
    lang = normalize_lang(lang)
    tr = next((x for x in mod.translations if x.lang == lang), None)
    if not title.strip() and not body.strip():
        if tr:
            await db.delete(tr)
    elif tr:
        tr.title, tr.body = title.strip(), body.strip()
    else:
        db.add(OnboardingModuleTranslation(module_id=mod.id, lang=lang, title=title.strip(), body=body.strip()))
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{mod.segment_id}?msg=Zapisano+tłumaczenie#m{module_id}",
                            status_code=303)


@router.post("/admin/{tenant_id}/onboarding/modules/{module_id}/move")
async def ob_admin_module_move(request: Request, tenant_id: int, module_id: int, direction: str = Form(...),
                               db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    mod = await _get_module(db, tenant_id, module_id)
    siblings = (await db.execute(
        select(OnboardingModule).where(OnboardingModule.segment_id == mod.segment_id)
        .order_by(OnboardingModule.sort_order, OnboardingModule.id)
    )).scalars().all()
    idx = next(i for i, m in enumerate(siblings) if m.id == mod.id)
    j = idx - 1 if direction == "up" else idx + 1
    if 0 <= j < len(siblings):
        siblings[idx], siblings[j] = siblings[j], siblings[idx]
    for i, m in enumerate(siblings, start=1):
        m.sort_order = i
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{mod.segment_id}#m{module_id}", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/modules/{module_id}/delete")
async def ob_admin_module_delete(request: Request, tenant_id: int, module_id: int,
                                 db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    mod = await _get_module(db, tenant_id, module_id)
    seg_id = mod.segment_id
    await db.delete(mod)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{seg_id}?msg=Usunięto+moduł", status_code=303)


@router.post("/admin/{tenant_id}/onboarding/attachments/{attachment_id}/delete")
async def ob_admin_attachment_delete(request: Request, tenant_id: int, attachment_id: int,
                                     db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    await require_editor(request, tenant_id, db, tenant)
    att = await db.get(OnboardingAttachment, attachment_id)
    if not att:
        raise HTTPException(404)
    mod = await _get_module(db, tenant_id, att.module_id)
    await db.delete(att)
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments/{mod.segment_id}#m{mod.id}", status_code=303)


def _attachment_response(att: OnboardingAttachment, download: bool = False) -> Response:
    disp = "attachment" if download else "inline"
    return Response(content=att.data, media_type=att.content_type, headers={
        "Content-Disposition": f'{disp}; filename="{att.filename}"',
        "Cache-Control": "private, max-age=3600",
        "X-Content-Type-Options": "nosniff",
    })


@router.get("/admin/{tenant_id}/onboarding/attachments/{attachment_id}")
async def ob_admin_attachment(tenant_id: int, attachment_id: int, db: AsyncSession = Depends(get_db),
                              tenant: Tenant = Depends(get_authed_tenant)):
    att = await db.get(OnboardingAttachment, attachment_id)
    if not att:
        raise HTTPException(404)
    await _get_module(db, tenant_id, att.module_id)   # sprawdza, że plik należy do tego tenanta
    return _attachment_response(att)


@router.post("/admin/{tenant_id}/onboarding/settings")
async def ob_admin_settings(request: Request, tenant_id: int, brand_name: str = Form(""),
                            brand_color: str = Form("#004b9b"), welcome_text: str = Form(""),
                            help_phone: str = Form(""),
                            logo: UploadFile = File(None), remove_logo: str = Form(""),
                            db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_authed_tenant)):
    settings = await require_editor(request, tenant_id, db, tenant)
    settings.brand_name = brand_name.strip() or tenant.name
    if re.fullmatch(r"#[0-9a-fA-F]{6}", brand_color.strip()):
        settings.brand_color = brand_color.strip()
    settings.welcome_text = welcome_text.strip() or None
    settings.help_phone = help_phone.strip()[:40] or None
    if remove_logo == "on":
        settings.logo_data, settings.logo_content_type = None, None
    if logo and logo.filename:
        data = await logo.read()
        if (logo.content_type or "").startswith("image/") and len(data) <= 2 * 1024 * 1024:
            settings.logo_data, settings.logo_content_type = data, logo.content_type
    await db.commit()
    return RedirectResponse(f"/admin/{tenant_id}/onboarding/segments?msg=Zapisano+wygląd", status_code=303)


# ===========================================================================
# PRACOWNIK: /o/{slug}
# ===========================================================================
async def _tenant_by_slug(db: AsyncSession, slug: str) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(404)
    return tenant


def _emp_lang(request: Request, tenant_id: int, person: OnboardingPerson | None = None) -> str:
    q = request.query_params.get("lang")
    if q:
        lang = normalize_lang(q)
        request.session[f"ob_lang_{tenant_id}"] = lang
        return lang
    s = request.session.get(f"ob_lang_{tenant_id}")
    if s:
        return normalize_lang(s)
    return normalize_lang(person.language if person else "pl")


async def _current_person(request: Request, db: AsyncSession, tenant: Tenant) -> OnboardingPerson | None:
    pid = request.session.get(f"ob_emp_{tenant.id}")
    if not pid:
        return None
    p = (await db.execute(
        select(OnboardingPerson).where(OnboardingPerson.id == pid, OnboardingPerson.tenant_id == tenant.id)
        .options(selectinload(OnboardingPerson.employee),
                 selectinload(OnboardingPerson.segment).selectinload(OnboardingSegment.modules)
                 .selectinload(OnboardingModule.attachments),
                 selectinload(OnboardingPerson.segment).selectinload(OnboardingSegment.modules)
                 .selectinload(OnboardingModule.translations),
                 selectinload(OnboardingPerson.acks))
    )).scalar_one_or_none()
    return p


def _module_text(mod: OnboardingModule, lang: str) -> tuple[str, str]:
    if lang != "pl":
        tr = next((x for x in mod.translations if x.lang == lang), None)
        if tr:
            return tr.title, tr.body
    return mod.title, mod.body


def _emp_ctx(request: Request, tenant: Tenant, settings: OnboardingSettings, lang: str, **extra) -> dict:
    ctx = {
        "request": request, "tenant": tenant, "settings": settings, "lang": lang,
        "brand": settings.brand_name or tenant.name, "color": settings.brand_color,
        "has_logo": bool(settings.logo_data), "slug": tenant.slug, "help_phone": settings.help_phone,
        "ready_langs": READY_LANGS, "t": lambda key, **kw: t(lang, key, **kw),
    }
    ctx.update(extra)
    return ctx


def _modules_state(p: OnboardingPerson, lang: str) -> list[dict]:
    modules = [m for m in (p.segment.modules if p.segment else []) if m.is_active]
    acked = {a.module_id: a for a in p.acks}
    out, unlocked = [], True
    for i, m in enumerate(modules, start=1):
        title, body = _module_text(m, lang)
        ack = acked.get(m.id)
        state = "done" if ack else ("now" if unlocked else "locked")
        if not ack:
            unlocked = False
        out.append({"m": m, "i": i, "title": title, "body": body, "ack": ack, "state": state})
    return out


@router.get("/o/{slug}", response_class=HTMLResponse)
async def ob_emp_login_page(request: Request, slug: str, t_: str | None = None,
                            db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    settings = await get_settings(db, tenant)
    person = await _current_person(request, db, tenant)
    lang = _emp_lang(request, tenant.id, person)
    if person and person.segment_id:
        return RedirectResponse(f"/o/{slug}/start", status_code=303)
    prefill = ""
    token = request.query_params.get("t")
    if token:
        emp = (await db.execute(select(Employee).where(Employee.token == token, Employee.tenant_id == tenant.id))
               ).scalar_one_or_none()
        if emp and emp.phone_whatsapp:
            prefill = emp.phone_whatsapp
    return templates.TemplateResponse("onboarding/emp_login.html", _emp_ctx(
        request, tenant, settings, lang, prefill=prefill, error=request.query_params.get("e", ""),
    ))


@router.post("/o/{slug}/login")
async def ob_emp_login(request: Request, slug: str, phone: str = Form(""), code: str = Form(""),
                       db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    norm = normalize_phone(phone)
    parsed = parse_code(code)
    person = None
    if norm and parsed:
        emps = (await db.execute(
            select(Employee).where(Employee.tenant_id == tenant.id, Employee.phone_whatsapp == norm)
        )).scalars().all()
        for emp in emps:
            cand = (await db.execute(
                select(OnboardingPerson).where(OnboardingPerson.employee_id == emp.id)
            )).scalar_one_or_none()
            if cand and (cand.birth_day, cand.birth_month) == parsed:
                person = cand
                break
    if not person:
        return RedirectResponse(f"/o/{slug}?e=1", status_code=303)
    if not person.segment_id:
        return RedirectResponse(f"/o/{slug}?e=2", status_code=303)

    now = datetime.now(WARSAW)
    if not person.first_login_at:
        person.first_login_at = now
    person.last_login_at = now
    db.add(OnboardingLogin(person_id=person.id, user_agent=(request.headers.get("user-agent") or "")[:300]))
    await db.commit()
    request.session[f"ob_emp_{tenant.id}"] = person.id
    request.session[f"ob_lang_{tenant.id}"] = person.language
    return RedirectResponse(f"/o/{slug}/start", status_code=303)


@router.post("/o/{slug}/logout")
async def ob_emp_logout(request: Request, slug: str):
    for key in list(request.session.keys()):
        if key.startswith("ob_emp_") or key.startswith("ob_lang_"):
            request.session.pop(key, None)
    return RedirectResponse(f"/o/{slug}", status_code=303)


@router.get("/o/{slug}/lang/{lang}")
async def ob_emp_lang(request: Request, slug: str, lang: str, db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    lang = normalize_lang(lang)
    request.session[f"ob_lang_{tenant.id}"] = lang
    person = await _current_person(request, db, tenant)
    if person:
        person.language = lang
        await db.commit()
    back = request.headers.get("referer") or f"/o/{slug}"
    return RedirectResponse(back, status_code=303)


@router.get("/o/{slug}/logo")
async def ob_emp_logo(slug: str, db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    settings = await get_settings(db, tenant)
    if not settings.logo_data:
        raise HTTPException(404)
    return Response(content=settings.logo_data, media_type=settings.logo_content_type or "image/png",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/o/{slug}/start", response_class=HTMLResponse)
async def ob_emp_start(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    person = await _current_person(request, db, tenant)
    if not person:
        return RedirectResponse(f"/o/{slug}", status_code=303)
    settings = await get_settings(db, tenant)
    lang = _emp_lang(request, tenant.id, person)
    items = _modules_state(person, lang)
    total_min = sum((it["m"].estimated_minutes or 0) for it in items)
    done = all(it["state"] == "done" for it in items) and bool(items)
    next_item = next((it for it in items if it["state"] == "now"), None)
    acked = len([it for it in items if it["state"] == "done"])
    pct = int(acked * 100 / len(items)) if items else 0
    return templates.TemplateResponse("onboarding/emp_start.html", _emp_ctx(
        request, tenant, settings, lang, person=person, items=items, total_min=total_min,
        done=done, next_item=next_item, locked_msg=request.query_params.get("locked"),
        acked=acked, pct=pct, modules_label=modules_count(lang, len(items)),
    ))


@router.get("/o/{slug}/m/{module_id}", response_class=HTMLResponse)
async def ob_emp_module(request: Request, slug: str, module_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    person = await _current_person(request, db, tenant)
    if not person:
        return RedirectResponse(f"/o/{slug}", status_code=303)
    settings = await get_settings(db, tenant)
    lang = _emp_lang(request, tenant.id, person)
    items = _modules_state(person, lang)
    item = next((it for it in items if it["m"].id == module_id), None)
    if not item:
        raise HTTPException(404)
    if item["state"] == "locked":
        return RedirectResponse(f"/o/{slug}/start?locked=1", status_code=303)
    nxt = next((it for it in items if it["i"] == item["i"] + 1), None)
    parts = render_parts(item["body"], [a for a in item["m"].attachments if a.is_image or a.is_pdf])
    return templates.TemplateResponse("onboarding/emp_module.html", _emp_ctx(
        request, tenant, settings, lang, person=person, items=items, item=item, nxt=nxt, n=len(items), parts=parts,
    ))


@router.post("/o/{slug}/m/{module_id}/ack")
async def ob_emp_ack(request: Request, slug: str, module_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    person = await _current_person(request, db, tenant)
    if not person:
        return RedirectResponse(f"/o/{slug}", status_code=303)
    lang = _emp_lang(request, tenant.id, person)
    items = _modules_state(person, lang)
    item = next((it for it in items if it["m"].id == module_id), None)
    if not item:
        raise HTTPException(404)
    if item["state"] == "locked":
        return RedirectResponse(f"/o/{slug}/start?locked=1", status_code=303)
    if item["state"] != "done":
        db.add(OnboardingAck(person_id=person.id, module_id=module_id, module_title=item["m"].title, language=lang))
        remaining = [it for it in items if it["m"].id != module_id and it["state"] != "done"]
        if not remaining:
            person.completed_at = datetime.now(WARSAW)
        await db.commit()
    nxt = next((it for it in items if it["i"] == item["i"] + 1), None)
    if nxt:
        return RedirectResponse(f"/o/{slug}/m/{nxt['m'].id}", status_code=303)
    return RedirectResponse(f"/o/{slug}/done", status_code=303)


@router.get("/o/{slug}/done", response_class=HTMLResponse)
async def ob_emp_done(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
    tenant = await _tenant_by_slug(db, slug)
    person = await _current_person(request, db, tenant)
    if not person:
        return RedirectResponse(f"/o/{slug}", status_code=303)
    settings = await get_settings(db, tenant)
    lang = _emp_lang(request, tenant.id, person)
    items = _modules_state(person, lang)
    if any(it["state"] != "done" for it in items):
        return RedirectResponse(f"/o/{slug}/start", status_code=303)
    return templates.TemplateResponse("onboarding/emp_done.html", _emp_ctx(
        request, tenant, settings, lang, person=person, items=items,
    ))


@router.get("/o/{slug}/file/{attachment_id}")
async def ob_emp_file(request: Request, slug: str, attachment_id: int, db: AsyncSession = Depends(get_db)):
    """Pliki tylko po zalogowaniu i tylko z segmentu tej osoby."""
    tenant = await _tenant_by_slug(db, slug)
    person = await _current_person(request, db, tenant)
    if not person:
        raise HTTPException(403)
    att = await db.get(OnboardingAttachment, attachment_id)
    if not att:
        raise HTTPException(404)
    allowed = {m.id for m in (person.segment.modules if person.segment else [])}
    if att.module_id not in allowed:
        raise HTTPException(403)
    return _attachment_response(att, download=request.query_params.get("dl") == "1")
