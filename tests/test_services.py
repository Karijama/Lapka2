import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Shelter
from services import (create_animal, list_animals, get_animal,
                      update_animal, delete_animal, validate_payload)

@pytest.fixture
def session():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()

@pytest.fixture
def sample(session):
    session.add(Shelter(name='Приют Дружба', city='Якутск'))
    session.commit()
    for name, species, city in [('Мурка', 'cat', 'Якутск'), ('Бим', 'dog', 'Якутск'),
                                 ('Марс', 'cat', 'Москва'), ('Мышка', 'cat', 'Якутск')]:
        create_animal(session, {'name': name, 'species': species, 'city': city})
    return session

def test_create_and_get(session):
    row = create_animal(session, {'name': 'Бим', 'species': 'dog', 'city': 'Якутск'})
    assert get_animal(session, row['id'])['name'] == 'Бим'

def test_filter_species(sample):
    assert list_animals(sample, species='cat')['total'] == 3

def test_filter_city_casefold(sample):
    assert list_animals(sample, city='якутск')['total'] == 3

def test_combined_filter(sample):
    assert list_animals(sample, species='cat', city='Якутск')['total'] == 2

def test_name_search(sample):
    assert list_animals(sample, q='мур')['items'][0]['name'] == 'Мурка'

def test_pagination(sample):
    a = list_animals(sample, per_page=2, page=1)
    b = list_animals(sample, per_page=2, page=2)
    assert a['total'] == 4 and len(a['items']) == 2
    assert a['items'][0]['id'] != b['items'][0]['id']

def test_update_status(session):
    row = create_animal(session, {'name': 'Лиса', 'species': 'other', 'city': 'Якутск'})
    updated = update_animal(session, row['id'], {'status': 'adopted'})
    assert updated['status'] == 'adopted'

def test_delete(session):
    row = create_animal(session, {'name': 'Бим', 'species': 'dog', 'city': 'Якутск'})
    assert delete_animal(session, row['id']) is True
    assert get_animal(session, row['id']) is None

def test_invalid_species(session):
    with pytest.raises(ValueError):
        create_animal(session, {'name': 'Кто-то', 'species': 'rabbit', 'city': 'Якутск'})

def test_invalid_pagination(sample):
    with pytest.raises(ValueError):
        list_animals(sample, page=0)

def test_missing_fields(session):
    with pytest.raises(ValueError):
        create_animal(session, {'name': 'Бим'})

def test_related_shelter(session):
    s = Shelter(name='Лапа', city='Якутск');session.add(s);session.commit()
    a = create_animal(session, {'name':'Мурка','species':'cat','city':'Якутск','shelter_id':s.id})
    assert a['shelter_id'] == s.id
