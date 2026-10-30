from __future__ import annotations

from urllib.parse import urlsplit
from sqlalchemy import func, select
from models import Animal, Shelter

SPECIES = {"cat": "Кошка", "dog": "Собака", "other": "Другое"}
STATUSES = {"searching": "Ищет дом", "adopted": "Нашёл дом"}
GENDERS = {"female": "Девочка", "male": "Мальчик", "unknown": "Не указан"}
SIZES = {"small": "Маленький", "medium": "Средний", "large": "Крупный"}
INPUT_FIELDS = {
    "name", "species", "city", "age_years", "gender", "size", "description", "status",
    "vaccinated", "neutered", "photo_url", "contact_email", "shelter_id"
}


def animal_to_dict(a: Animal):
    return {"id": a.id, "name": a.name, "species": a.species,
            "city": a.city, "age_years": a.age_years, "gender": a.gender,
            "size": a.size, "description": a.description, "status": a.status,
            "vaccinated": a.vaccinated, "neutered": a.neutered,
            "photo_url": a.photo_url, "contact_email": a.contact_email,
            "shelter_id": a.shelter_id, "shelter_name": a.shelter.name if a.shelter else None,
            "created_at": a.created_at.isoformat() if a.created_at else None}


def validate_payload(data, *, partial=False):
    if not isinstance(data, dict):
        raise ValueError("Ожидается JSON-объект")
    unknown = set(data) - INPUT_FIELDS
    if unknown:
        raise ValueError("Неизвестные поля: " + ", ".join(sorted(unknown)))
    if not partial and any(not data.get(key) for key in ("name", "species", "city")):
        raise ValueError("Поля name, species и city обязательны")
    normalized = {}
    for key, value in data.items():
        if key in ("name", "city"):
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > (120 if key == "name" else 100):
                raise ValueError(f"Поле {key} обязательно, максимальная длина 120/100 символов")
            value = value.strip()
        elif key in ("description", "photo_url", "contact_email"):
            if not isinstance(value, str):
                raise ValueError(f"Поле {key} должно быть строкой")
            value = value.strip()
            if len(value) > {"description": 3000, "photo_url": 500, "contact_email": 254}[key]:
                raise ValueError(f"Поле {key} слишком длинное")
            if key == "photo_url" and value:
                parts = urlsplit(value)
                if parts.scheme not in ("https", "http") or not parts.netloc or parts.username or parts.password:
                    raise ValueError("Изображение: нужна полная HTTP(S)-ссылка")
            if key == "contact_email" and value and ("@" not in value or any(c.isspace() for c in value)):
                raise ValueError("Укажите корректный email")
        elif key == "species" and value not in SPECIES:
            raise ValueError("species: cat, dog или other")
        elif key == "status" and value not in STATUSES:
            raise ValueError("status: searching или adopted")
        elif key == "gender" and value not in GENDERS:
            raise ValueError("gender: female, male или unknown")
        elif key == "size" and value not in SIZES:
            raise ValueError("size: small, medium или large")
        elif key == "age_years":
            if value in (None, ""):
                value = None
            elif type(value) is not int or not 0 <= value <= 50:
                raise ValueError("Возраст должен быть целым числом от 0 до 50")
        elif key in ("vaccinated", "neutered") and type(value) is not bool:
            raise ValueError(f"{key}: требуется true или false")
        elif key == "shelter_id":
            if value in (None, ""):
                value = None
            elif type(value) is not int or value <= 0:
                raise ValueError("shelter_id должен быть положительным целым числом")
        normalized[key] = value
    return normalized


def create_animal(session, data):
    values = validate_payload(data)
    if values.get("shelter_id") and session.get(Shelter, values["shelter_id"]) is None:
        raise ValueError("Указанный приют не найден")
    values["name_key"] = values["name"].casefold()
    values["city_key"] = values["city"].casefold()
    animal = Animal(**values)
    session.add(animal)
    session.commit()
    return animal_to_dict(animal)


def update_animal(session, animal_id, data):
    animal = session.get(Animal, animal_id)
    if not animal:
        return None
    values = validate_payload(data, partial=True)
    if values.get("shelter_id") and session.get(Shelter, values["shelter_id"]) is None:
        raise ValueError("Указанный приют не найден")
    for key, value in values.items():
        setattr(animal, key, value)
    if "name" in values:
        animal.name_key = animal.name.casefold()
    if "city" in values:
        animal.city_key = animal.city.casefold()
    session.commit()
    return animal_to_dict(animal)


def get_animal(session, animal_id):
    animal = session.get(Animal, animal_id)
    return animal_to_dict(animal) if animal else None


def delete_animal(session, animal_id):
    animal = session.get(Animal, animal_id)
    if animal is None:
        return False
    session.delete(animal)
    session.commit()
    return True


def list_animals(session, *, species=None, city=None, status=None, q=None, page=1, per_page=9, size=None, shelter_id=None):
    if type(page) is not int or type(per_page) is not int or page < 1 or per_page < 1 or per_page > 100:
        raise ValueError("page должен быть ≥ 1, per_page — от 1 до 100")
    if species and species not in SPECIES or status and status not in STATUSES or size and size not in SIZES:
        raise ValueError("Некорректный фильтр")
    stmt = select(Animal)
    if species:
        stmt = stmt.where(Animal.species == species)
    if city:
        stmt = stmt.where(Animal.city_key == city.strip().casefold())
    if status:
        stmt = stmt.where(Animal.status == status)
    if size:
        stmt = stmt.where(Animal.size == size)
    if shelter_id is not None:
        if type(shelter_id) is not int or shelter_id < 1:
            raise ValueError("Неправильный ID приюта")
        stmt = stmt.where(Animal.shelter_id == shelter_id)
    if q:
        q_norm = q.strip().casefold()
        if len(q_norm) > 120:
            raise ValueError("Поисковый запрос слишком длинный")
        if q_norm:
            stmt = stmt.where(Animal.name_key.contains(q_norm, autoescape=True))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    animals = session.scalars(stmt.order_by(Animal.created_at.desc(), Animal.id.desc())
                              .offset((page-1)*per_page).limit(per_page)).all()
    return {"items": [animal_to_dict(a) for a in animals], "total": total,
            "page": page, "per_page": per_page, "pages": max(1, (total + per_page - 1) // per_page)}


def list_shelters(session):
    return session.scalars(select(Shelter).order_by(Shelter.name)).all()


def list_cities(session):
    return session.scalars(select(Animal.city).distinct().order_by(Animal.city)).all()


def stats(session):
    return {
        "total": session.scalar(select(func.count(Animal.id))) or 0,
        "searching": session.scalar(select(func.count(Animal.id)).where(Animal.status == "searching")) or 0,
        "adopted": session.scalar(select(func.count(Animal.id)).where(Animal.status == "adopted")) or 0,
        "shelters": session.scalar(select(func.count(Shelter.id))) or 0,
    }
