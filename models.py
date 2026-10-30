from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Shelter(Base):
    __tablename__ = "shelters"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    animals: Mapped[list["Animal"]] = relationship(back_populates="shelter")


class Animal(Base):
    __tablename__ = "animals"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    species: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    city_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), default="unknown")
    size: Mapped[str] = mapped_column(String(20), default="medium")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="searching", index=True)
    vaccinated: Mapped[bool] = mapped_column(Boolean, default=False)
    neutered: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_url: Mapped[str] = mapped_column(String(500), default="")
    contact_email: Mapped[str] = mapped_column(String(254), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    shelter_id: Mapped[int | None] = mapped_column(ForeignKey("shelters.id"), nullable=True)
    shelter: Mapped[Shelter | None] = relationship(back_populates="animals")


def make_session_factory(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine
