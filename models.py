"""Data models for the educational Lapka API extension (2026)."""
from sqlalchemy import ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

class Base(DeclarativeBase):
    pass

class Shelter(Base):
    __tablename__ = "shelters"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    animals: Mapped[list["Animal"]] = relationship(back_populates="shelter")

class Animal(Base):
    __tablename__ = "animals"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    species: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    city_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    age_years: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="searching")
    shelter_id: Mapped[int | None] = mapped_column(ForeignKey("shelters.id"), nullable=True)
    shelter: Mapped[Shelter | None] = relationship(back_populates="animals")

def session_factory(db_url="sqlite:///lapka.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
