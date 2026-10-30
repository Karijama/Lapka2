"""Populate the database with **fictional** demonstration records.
Run from project root: python scripts/seed_demo.py
Does not overwrite existing data; only seeds an empty database.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select, func
from app import app
from models import Animal, Shelter
from services import create_animal

samples = [
    ("Мурка", "cat", "Якутск", 2, "female", "small", "Нежная, немного застенчивая кошечка. Любит спокойные вечера и мягкие пледы."),
    ("Барсик", "cat", "Москва", 1, "male", "medium", "Обожает играть с игрушками и встречать гостей. Очень любознательный."),
    ("Рыжик", "cat", "Санкт-Петербург", 3, "male", "medium", "Самый ласковый рыжий друг: мурчит и всегда рядом с человеком."),
    ("Луна", "cat", "Якутск", 4, "female", "small", "Спокойная и умная кошка. Отлично подойдёт для размеренной домашней жизни."),
    ("Бим", "dog", "Якутск", 2, "male", "medium", "Весёлый и активный пёс, обожает прогулки и новые знакомства."),
    ("Джесси", "dog", "Москва", 1, "female", "large", "Ищет энергичную семью. Любит бегать и прекрасно учится командам."),
    ("Тоби", "dog", "Казань", 4, "male", "small", "Компактный, дружелюбный товарищ для игр и уютных вечеров."),
    ("Ника", "dog", "Якутск", 3, "female", "medium", "Добрая и уравновешенная собака. Любит внимание и долгие прогулки."),
    ("Кнопка", "other", "Казань", 1, "female", "small", "Декоративный кролик, которому нужен заботливый и внимательный хозяин."),
    ("Пушок", "cat", "Москва", 5, "male", "large", "Независимый красавец с добрым сердцем, ценит уважение к личному пространству."),
    ("Снежок", "dog", "Санкт-Петербург", 1, "male", "small", "Юный непоседа и большой любитель игр с мячиками."),
    ("Ася", "cat", "Казань", 2, "female", "small", "Ласковая кошка для спокойного дома, любит сидеть у окна."),
]

if __name__ == "__main__":
    Session = app.extensions["lapka_session_factory"]
    with Session() as db:
        count = db.scalar(select(func.count(Animal.id)))
        if count:
            print(f"В базе уже {count} питомцев. Демоданные не добавлены.")
            raise SystemExit(0)
        shelter = Shelter(name="Учебный демо-приют Lapka", city="Якутск",
                          description="Вымышленный приют для демонстрации учебного проекта. НЕ РЕАЛЬНЫЕ ОБЪЯВЛЕНИЯ.")
        db.add(shelter)
        db.commit()
        for index, (name, species, city, age, gender, size, description) in enumerate(samples):
            create_animal(db, dict(name=name, species=species, city=city, age_years=age,
                                   gender=gender, size=size, description=description,
                                   status="adopted" if index in (3, 10) else "searching",
                                   vaccinated=index % 2 == 0, neutered=index % 3 == 0,
                                   shelter_id=shelter.id, contact_email=""))
    print("Добавлены 12 ВЫМЫШЛЕННЫХ демонстрационных питомцев. Замените их реальными анкетами перед публикацией.")
