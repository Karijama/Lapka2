"""Validation and database operations separated from Flask routing."""
from sqlalchemy import func, select
from models import Animal, Shelter

ALLOWED_SPECIES = {"cat", "dog", "other"}
ALLOWED_STATUSES = {"searching", "adopted"}

def animal_to_dict(a):
    return {"id": a.id, "name": a.name, "species": a.species,
            "city": a.city, "age_years": a.age_years,
            "description": a.description, "status": a.status,
            "shelter_id": a.shelter_id}

def validate_payload(data, partial=False):
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    required = ("name", "species", "city")
    if not partial and any(not data.get(k) for k in required):
        raise ValueError("name, species and city are required")
    if "species" in data and data["species"] not in ALLOWED_SPECIES:
        raise ValueError("unsupported species")
    if "status" in data and data["status"] not in ALLOWED_STATUSES:
        raise ValueError("unsupported status")
    if "age_years" in data and data["age_years"] is not None:
        if type(data["age_years"]) is not int or data["age_years"] < 0:
            raise ValueError("age_years must be a nonnegative integer")
    for k in ("name", "city"):
        if k in data and (not isinstance(data[k], str) or not data[k].strip()):
            raise ValueError(f"{k} must be a nonempty string")
    allowed = {"name", "species", "city", "age_years", "description", "status", "shelter_id"}
    return {k: v.strip() if k in {"name", "city"} and isinstance(v, str) else v
            for k, v in data.items() if k in allowed}

def create_animal(session, data):
    fields = validate_payload(data)
    if fields.get("shelter_id") is not None and session.get(Shelter, fields["shelter_id"]) is None:
        raise ValueError("shelter not found")
    fields["name_key"] = fields["name"].casefold()
    fields["city_key"] = fields["city"].casefold()
    a = Animal(**fields)
    session.add(a)
    session.commit()
    return animal_to_dict(a)

def list_animals(session, species=None, city=None, status=None, q=None, page=1, per_page=10):
    if not isinstance(page, int) or not isinstance(per_page, int) or page < 1 or not 1 <= per_page <= 100:
        raise ValueError("page must be >=1; per_page must be in 1..100")
    stmt = select(Animal)
    if species:
        stmt = stmt.where(Animal.species == species)
    if city:
        stmt = stmt.where(Animal.city_key == city.casefold())
    if status:
        stmt = stmt.where(Animal.status == status)
    if q:
        stmt = stmt.where(Animal.name_key.contains(q.casefold()))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = session.scalars(stmt.order_by(Animal.id).offset((page - 1) * per_page).limit(per_page)).all()
    return {"items": [animal_to_dict(a) for a in rows], "total": total,
            "page": page, "per_page": per_page}

def get_animal(session, animal_id):
    a = session.get(Animal, animal_id)
    return animal_to_dict(a) if a else None

def update_animal(session, animal_id, data):
    a = session.get(Animal, animal_id)
    if not a: return None
    changed = validate_payload(data, partial=True)
    for key, value in changed.items():
        setattr(a, key, value)
    if "name" in changed:
        a.name_key = a.name.casefold()
    if "city" in changed:
        a.city_key = a.city.casefold()
    session.commit()
    return animal_to_dict(a)

def delete_animal(session, animal_id):
    a = session.get(Animal, animal_id)
    if not a: return False
    session.delete(a)
    session.commit()
    return True
