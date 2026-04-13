from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Text,
    ForeignKey, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import secrets


class MessageChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    viber = "viber"
    email = "email"


class AvailabilityStatus(str, enum.Enum):
    available = "available"        # cały dzień
    partial = "partial"            # określone godziny
    unavailable = "unavailable"    # niedostępny


class CampaignStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    completed = "completed"


# ---------------------------------------------------------------------------
# Tenant — klient agencji (np. find-work.pl)
# ---------------------------------------------------------------------------
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)  # np. "find-work"
    api_key = Column(String(64), default=lambda: secrets.token_hex(32), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contracts = relationship("Contract", back_populates="tenant", cascade="all, delete")
    employees = relationship("Employee", back_populates="tenant", cascade="all, delete")
    campaigns = relationship("MessageCampaign", back_populates="tenant", cascade="all, delete")


# ---------------------------------------------------------------------------
# Contract — kontrakt / klient końcowy pracownicy
# ---------------------------------------------------------------------------
class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    city_1 = Column(String(200), nullable=True)
    city_2 = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="contracts")
    employee_links = relationship("ContractEmployee", back_populates="contract", cascade="all, delete")


# ---------------------------------------------------------------------------
# Employee — pracownik
# ---------------------------------------------------------------------------
class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_whatsapp = Column(String(30), nullable=True)   # format: +48XXXXXXXXX
    phone_viber = Column(String(30), nullable=True)
    email = Column(String(200), nullable=True)
    token = Column(String(64), default=lambda: secrets.token_urlsafe(32), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="employees")
    contract_links = relationship("ContractEmployee", back_populates="employee", cascade="all, delete")
    submissions = relationship("ScheduleSubmission", back_populates="employee")
    message_logs = relationship("MessageLog", back_populates="employee")


# ---------------------------------------------------------------------------
# ContractEmployee — przypisanie pracownika do kontraktu
# ---------------------------------------------------------------------------
class ContractEmployee(Base):
    __tablename__ = "contract_employees"
    __table_args__ = (UniqueConstraint("contract_id", "employee_id"),)

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="employee_links")
    employee = relationship("Employee", back_populates="contract_links")


# ---------------------------------------------------------------------------
# ScheduleSubmission — wypełniony grafik (jeden na miesiąc per pracownik)
# ---------------------------------------------------------------------------
class ScheduleSubmission(Base):
    __tablename__ = "schedule_submissions"
    __table_args__ = (UniqueConstraint("employee_id", "year", "month"),)

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)   # 1-12
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="submissions")
    days = relationship("AvailabilityDay", back_populates="submission", cascade="all, delete")


# ---------------------------------------------------------------------------
# AvailabilityDay — dostępność per dzień
# ---------------------------------------------------------------------------
class AvailabilityDay(Base):
    __tablename__ = "availability_days"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("schedule_submissions.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(SAEnum(AvailabilityStatus), nullable=False, default=AvailabilityStatus.available)
    hour_from = Column(String(5), nullable=True)   # np. "08:00"
    hour_to = Column(String(5), nullable=True)     # np. "16:00"

    submission = relationship("ScheduleSubmission", back_populates="days")


# ---------------------------------------------------------------------------
# MessageTemplate — szablon wiadomości edytowalny przez klienta
# ---------------------------------------------------------------------------
class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    channel = Column(SAEnum(MessageChannel), nullable=False)
    body = Column(Text, nullable=False)
    # Zmienne: {first_name}, {last_name}, {month_name}, {schedule_link}
    is_reminder = Column(Boolean, default=False)  # False = pierwsze, True = przypomnienie
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# MessageCampaign — kampania wysyłkowa (miesięczna)
# ---------------------------------------------------------------------------
class MessageCampaign(Base):
    __tablename__ = "message_campaigns"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    status = Column(SAEnum(CampaignStatus), default=CampaignStatus.pending)
    confirmed_by = Column(String(200), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="campaigns")
    logs = relationship("MessageLog", back_populates="campaign", cascade="all, delete")


# ---------------------------------------------------------------------------
# MessageLog — log wysłanych wiadomości
# ---------------------------------------------------------------------------
class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("message_campaigns.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    channel = Column(SAEnum(MessageChannel), nullable=False)
    phone_or_email = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False)   # sent / failed / delivered
    external_id = Column(String(200), nullable=True)  # Twilio SID
    is_reminder = Column(Boolean, default=False)
    is_reminder_2 = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text, nullable=True)

    campaign = relationship("MessageCampaign", back_populates="logs")
    employee = relationship("Employee", back_populates="message_logs")


# ---------------------------------------------------------------------------
# TenantSettings — ustawienia tenanta (szablony wiadomości, przypomnienia)
# ---------------------------------------------------------------------------
DEFAULT_INITIAL_MESSAGE = (
    "Dzień dobry {first_name}! 👋\n\n"
    "Prosimy o uzupełnienie grafiku dostępności na {month_name}.\n\n"
    "Link: {schedule_link}\n\n"
    "Dziękujemy!"
)

DEFAULT_REMINDER_MESSAGE = (
    "Dzień dobry {first_name}, przypominamy o uzupełnieniu grafiku na {month_name}.\n\n"
    "Link: {schedule_link}"
)

DEFAULT_REMINDER_2_MESSAGE = (
    "Hej {first_name}! To ostatnie przypomnienie — prosimy o uzupełnienie grafiku na {month_name}.\n\n"
    "Link: {schedule_link}"
)


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False)
    initial_message = Column(Text, nullable=False, default=DEFAULT_INITIAL_MESSAGE)
    reminder_message = Column(Text, nullable=False, default=DEFAULT_REMINDER_MESSAGE)
    reminder_days = Column(Integer, nullable=False, default=3)
    reminder_2_message = Column(Text, nullable=True, default=DEFAULT_REMINDER_2_MESSAGE)
    reminder_2_days = Column(Integer, nullable=True, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant")
