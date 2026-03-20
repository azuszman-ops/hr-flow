"""
APScheduler — harmonogram zadań automatycznych HR-Flow.
Uruchamiany z app/main.py w lifespan (start/stop).
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import (
    MessageCampaign, MessageLog, Employee, ScheduleSubmission,
    TenantSettings, MessageChannel, CampaignStatus,
    DEFAULT_REMINDER_MESSAGE, DEFAULT_REMINDER_2_MESSAGE,
)
from app.services.messaging import send_whatsapp, render_template, MONTH_NAMES_PL

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def send_follow_up_reminders():
    """
    Dla każdej aktywnej kampanii (status='sent') sprawdź, którzy pracownicy:
    1. Dostali wiadomość początkową X dni temu (X = reminder_days tenanta)
    2. NIE wypełnili grafiku
    3. NIE dostali jeszcze przypomnienia

    Jeśli warunki spełnione — wyślij przypomnienie WhatsApp i zapisz log.
    """
    logger.info("[Scheduler] Starting follow-up reminder job")
    now = datetime.utcnow()

    async with AsyncSessionLocal() as db:
        # Pobierz wszystkie kampanie ze statusem 'sent'
        active_campaigns = (
            await db.execute(
                select(MessageCampaign).where(MessageCampaign.status == CampaignStatus.sent)
            )
        ).scalars().all()

        for campaign in active_campaigns:
            tenant_id = campaign.tenant_id

            # Pobierz ustawienia tenanta (reminder_days)
            tenant_settings = (
                await db.execute(
                    select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                )
            ).scalar_one_or_none()

            reminder_days = tenant_settings.reminder_days if tenant_settings else 3
            reminder_template = (
                tenant_settings.reminder_message
                if tenant_settings
                else DEFAULT_REMINDER_MESSAGE
            )

            cutoff_time = now - timedelta(days=reminder_days)

            # Pobierz logi wiadomości początkowych dla tej kampanii (nie przypomnienia)
            initial_logs = (
                await db.execute(
                    select(MessageLog)
                    .where(
                        MessageLog.campaign_id == campaign.id,
                        MessageLog.is_reminder == False,
                        MessageLog.status == "sent",
                        MessageLog.sent_at <= cutoff_time,
                    )
                    .options(selectinload(MessageLog.employee))
                )
            ).scalars().all()

            reminder_2_template = (
                tenant_settings.reminder_2_message
                if tenant_settings and tenant_settings.reminder_2_message
                else DEFAULT_REMINDER_2_MESSAGE
            )
            reminder_2_days = tenant_settings.reminder_2_days if tenant_settings and tenant_settings.reminder_2_days else 1

            for log in initial_logs:
                emp = log.employee
                if not emp or not emp.is_active or not emp.phone_whatsapp:
                    continue

                # Sprawdź, czy już wysłano przypomnienie 1
                existing_reminder = (
                    await db.execute(
                        select(MessageLog).where(
                            MessageLog.campaign_id == campaign.id,
                            MessageLog.employee_id == emp.id,
                            MessageLog.is_reminder == True,
                        )
                    )
                ).scalar_one_or_none()

                # Sprawdź, czy pracownik uzupełnił grafik
                submission = (
                    await db.execute(
                        select(ScheduleSubmission).where(
                            ScheduleSubmission.employee_id == emp.id,
                            ScheduleSubmission.year == campaign.year,
                            ScheduleSubmission.month == campaign.month,
                        )
                    )
                ).scalar_one_or_none()

                if submission:
                    continue  # Grafik uzupełniony — nie wysyłaj

                if not existing_reminder:
                    # Wyślij przypomnienie 1
                    month_name = MONTH_NAMES_PL.get(campaign.month, str(campaign.month))
                    message = render_template(reminder_template, emp, month_name, emp.token)
                    result = await send_whatsapp(emp.phone_whatsapp, message)
                    reminder_log = MessageLog(
                        campaign_id=campaign.id,
                        employee_id=emp.id,
                        channel=MessageChannel.whatsapp,
                        phone_or_email=emp.phone_whatsapp,
                        status=result["status"],
                        external_id=result.get("external_id"),
                        error_message=result.get("error"),
                        is_reminder=True,
                    )
                    db.add(reminder_log)
                    logger.info(
                        "[Scheduler] Reminder 1 sent to %s %s (campaign %d) — status: %s",
                        emp.first_name, emp.last_name, campaign.id, result["status"]
                    )
                elif (
                    existing_reminder.status == "sent"
                    and existing_reminder.sent_at <= now - timedelta(days=reminder_2_days)
                ):
                    # Sprawdź, czy już wysłano przypomnienie 2
                    existing_reminder_2 = (
                        await db.execute(
                            select(MessageLog).where(
                                MessageLog.campaign_id == campaign.id,
                                MessageLog.employee_id == emp.id,
                                MessageLog.is_reminder_2 == True,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing_reminder_2:
                        # Wyślij przypomnienie 2
                        month_name = MONTH_NAMES_PL.get(campaign.month, str(campaign.month))
                        message = render_template(reminder_2_template, emp, month_name, emp.token)
                        result = await send_whatsapp(emp.phone_whatsapp, message)
                        reminder_2_log = MessageLog(
                            campaign_id=campaign.id,
                            employee_id=emp.id,
                            channel=MessageChannel.whatsapp,
                            phone_or_email=emp.phone_whatsapp,
                            status=result["status"],
                            external_id=result.get("external_id"),
                            error_message=result.get("error"),
                            is_reminder=False,
                            is_reminder_2=True,
                        )
                        db.add(reminder_2_log)
                        logger.info(
                            "[Scheduler] Reminder 2 sent to %s %s (campaign %d) — status: %s",
                            emp.first_name, emp.last_name, campaign.id, result["status"]
                        )

        await db.commit()
    logger.info("[Scheduler] Follow-up reminder job completed")


def start_scheduler():
    """Rejestruje zadania i startuje scheduler."""
    scheduler.add_job(
        send_follow_up_reminders,
        trigger=CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="follow_up_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] Started — follow-up reminders scheduled at 09:00 UTC daily")


def stop_scheduler():
    """Zatrzymuje scheduler (wywoływane przy shutdown)."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
