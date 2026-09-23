"""
Modele modułu Onboarding (Find Work, wrzesień 2026).

Osobny plik: nie zmienia istniejących tabel HR-Flow. Powiązanie z pracownikiem
przez onboarding_persons.employee_id (1:1), kasowanie kaskadowe po stronie bazy.
Tabele tworzy Base.metadata.create_all w init_db (import przez app.api.onboarding).
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, LargeBinary,
    UniqueConstraint, func,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ---------------------------------------------------------------------------
# Ustawienia onboardingu per tenant (brand, flaga edytora)
# ---------------------------------------------------------------------------
class OnboardingSettings(Base):
    __tablename__ = "onboarding_settings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    brand_name = Column(String(200), nullable=True)
    brand_color = Column(String(20), nullable=False, default="#1d4ed8")
    logo_data = Column(LargeBinary, nullable=True)
    logo_content_type = Column(String(100), nullable=True)
    welcome_text = Column(Text, nullable=True)
    # Pakiet Rozszerzony: klient sam edytuje segmenty i moduły.
    editor_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Segment (np. Automotive 1, Magazyn 2, Piekarnia) z własną listą modułów
# ---------------------------------------------------------------------------
class OnboardingSegment(Base):
    __tablename__ = "onboarding_segments"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    modules = relationship(
        "OnboardingModule", back_populates="segment",
        order_by="OnboardingModule.sort_order", cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# Moduł: tekst + załączniki (zdjęcia, PDF), kończy się potwierdzeniem
# ---------------------------------------------------------------------------
class OnboardingModule(Base):
    __tablename__ = "onboarding_modules"

    id = Column(Integer, primary_key=True)
    segment_id = Column(Integer, ForeignKey("onboarding_segments.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False, default="")
    estimated_minutes = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    segment = relationship("OnboardingSegment", back_populates="modules")
    attachments = relationship(
        "OnboardingAttachment", back_populates="module",
        order_by="OnboardingAttachment.sort_order", cascade="all, delete-orphan",
    )
    translations = relationship(
        "OnboardingModuleTranslation", back_populates="module", cascade="all, delete-orphan",
    )


class OnboardingModuleTranslation(Base):
    __tablename__ = "onboarding_module_translations"
    __table_args__ = (UniqueConstraint("module_id", "lang"),)

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("onboarding_modules.id", ondelete="CASCADE"), nullable=False)
    lang = Column(String(5), nullable=False)   # en / uk / es / ru
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False, default="")

    module = relationship("OnboardingModule", back_populates="translations")


class OnboardingAttachment(Base):
    __tablename__ = "onboarding_attachments"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("onboarding_modules.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(300), nullable=False)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False, default=0)
    data = Column(LargeBinary, nullable=False)
    caption = Column(String(300), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    module = relationship("OnboardingModule", back_populates="attachments")

    @property
    def is_image(self) -> bool:
        return (self.content_type or "").startswith("image/")

    @property
    def is_pdf(self) -> bool:
        return self.content_type == "application/pdf"


# ---------------------------------------------------------------------------
# Osoba w onboardingu: 1:1 z Employee, segment, język, kod logowania
# ---------------------------------------------------------------------------
class OnboardingPerson(Base):
    __tablename__ = "onboarding_persons"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False)
    segment_id = Column(Integer, ForeignKey("onboarding_segments.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(5), nullable=False, default="pl")
    birth_day = Column(Integer, nullable=False)
    birth_month = Column(Integer, nullable=False)
    first_day_info = Column(Text, nullable=True)   # godzina, miejsce, koordynator
    link_sent_at = Column(DateTime(timezone=True), nullable=True)
    link_sent_count = Column(Integer, nullable=False, default=0)
    first_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")
    segment = relationship("OnboardingSegment")
    acks = relationship("OnboardingAck", back_populates="person", cascade="all, delete-orphan")
    logins = relationship("OnboardingLogin", back_populates="person", cascade="all, delete-orphan",
                          order_by="OnboardingLogin.logged_at")
    messages = relationship("OnboardingMessage", back_populates="person", cascade="all, delete-orphan",
                            order_by="OnboardingMessage.sent_at")

    @property
    def login_code(self) -> str:
        return f"{self.birth_day:02d}{self.birth_month:02d}"


class OnboardingAck(Base):
    """Potwierdzenie „Zapoznałem się i rozumiem" dla modułu."""
    __tablename__ = "onboarding_acks"
    __table_args__ = (UniqueConstraint("person_id", "module_id"),)

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("onboarding_persons.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(Integer, ForeignKey("onboarding_modules.id", ondelete="CASCADE"), nullable=False)
    module_title = Column(String(300), nullable=False)   # migawka tytułu w chwili potwierdzenia
    language = Column(String(5), nullable=False, default="pl")
    acked_at = Column(DateTime(timezone=True), server_default=func.now())

    person = relationship("OnboardingPerson", back_populates="acks")
    module = relationship("OnboardingModule")


class OnboardingLogin(Base):
    __tablename__ = "onboarding_logins"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("onboarding_persons.id", ondelete="CASCADE"), nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(String(300), nullable=True)

    person = relationship("OnboardingPerson", back_populates="logins")


class OnboardingMessage(Base):
    """Log wysyłki linku onboardingowego przez WhatsApp."""
    __tablename__ = "onboarding_messages"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("onboarding_persons.id", ondelete="CASCADE"), nullable=False)
    phone = Column(String(30), nullable=False)
    status = Column(String(50), nullable=False)       # sent / failed / rate_limited
    external_id = Column(String(200), nullable=True)  # Twilio SID
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    person = relationship("OnboardingPerson", back_populates="messages")
