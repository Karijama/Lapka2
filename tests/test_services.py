from pathlib import Path
import pytest
from sqlalchemy import select
from models import Animal, Shelter, make_session_factory
from services import (animal_to_dict, create_animal, delete_animal, get_animal,
                      list_animals, stats, update_animal, validate_payload)

@pytest.fixture()
def db(tmp_path):
    Session, engine = make_session_factory('sqlite:///' + str(tmp_path / 'test.db'))
    with Session() as session:
        yield session
    engine.dispose()

@pytest.fixture()
def animal_data():
    return dict(name='Мурка', species='cat', city='Якутск', age_years=2, description='Домашняя кошка')


def test_create_get_and_normalization(db, animal_data):
    obj = create_animal(db, animal_data)
    assert obj['id'] and obj['name'] == 'Мурка'
    assert get_animal(db, obj['id'])['city'] == 'Якутск'
    a = db.get(Animal, obj['id'])
    assert a.name_key == 'мурка'


def test_case_insensitive_cyrillic_search(db, animal_data):
    create_animal(db, animal_data)
    assert list_animals(db, q='МУР', city='ЯКУТСК')['total'] == 1
    assert list_animals(db, q='бу')['total'] == 0


def test_filter_species_and_status(db, animal_data):
    create_animal(db, animal_data)
    create_animal(db, dict(name='Бим', city='Казань', species='dog', status='adopted'))
    assert list_animals(db, species='dog')['total'] == 1
    assert list_animals(db, status='searching')['total'] == 1
    assert list_animals(db, city='КАЗАНЬ')['total'] == 1


def test_pagination(db):
    for i in range(12):
        create_animal(db, dict(name=f'Кошка {i}', city='Москва', species='cat'))
    first = list_animals(db, page=1, per_page=5)
    second = list_animals(db, page=2, per_page=5)
    assert first['total'] == 12 and first['pages'] == 3
    assert len(first['items']) == 5 and len(second['items']) == 5
    assert first['items'][0]['id'] != second['items'][0]['id']

@pytest.mark.parametrize('bad', [0, -1, 2.5, '2'])
def test_bad_pages(db, bad):
    with pytest.raises(ValueError): list_animals(db, page=bad)

@pytest.mark.parametrize('bad', [0, 101, '10'])
def test_bad_page_sizes(db, bad):
    with pytest.raises(ValueError): list_animals(db, per_page=bad)


def test_update_and_delete(db, animal_data):
    a = create_animal(db, animal_data)
    assert update_animal(db, a['id'], {'name': 'Марфа', 'status': 'adopted'})['name'] == 'Марфа'
    assert list_animals(db, q='марф')['total'] == 1
    assert list_animals(db, q='мурк')['total'] == 0
    assert delete_animal(db, a['id'])
    assert get_animal(db, a['id']) is None
    assert not delete_animal(db, a['id'])


def test_relationship(db, animal_data):
    shelter = Shelter(name='Приют', city='Якутск')
    db.add(shelter); db.commit()
    row = create_animal(db, {**animal_data, 'shelter_id': shelter.id})
    assert row['shelter_name'] == 'Приют'
    with pytest.raises(ValueError): create_animal(db, {**animal_data, 'shelter_id': 99999})


def test_invalid_data(db, animal_data):
    for payload in [None, {}, {**animal_data,'species':'horse'}, {**animal_data,'age_years':True},
                    {**animal_data,'photo_url':'javascript:alert(1)'}, {**animal_data,'name':''},
                    {**animal_data,'untrusted':'hello'}]:
        with pytest.raises(ValueError): create_animal(db, payload)


def test_update_bad_shelter(db, animal_data):
    row = create_animal(db, animal_data)
    with pytest.raises(ValueError): update_animal(db, row['id'], {'shelter_id':123})


def test_search_wildcard_is_literal(db, animal_data):
    create_animal(db, animal_data)
    assert list_animals(db, q='%')['total'] == 0
    assert list_animals(db, q='_')['total'] == 0


def test_stats(db, animal_data):
    create_animal(db, animal_data)
    create_animal(db, dict(name='Барсик', city='Москва', species='cat', status='adopted'))
    result = stats(db)
    assert result['total'] == 2 and result['searching'] == 1 and result['adopted'] == 1


def test_boolean_and_string_validation():
    for obj in ({'vaccinated':1}, {'neutered':'yes'}, {'description': 123}, {'name':' '},
                {'shelter_id':True}, {'age_years':-2}, {'photo_url':'ftp://example.com/a.jpg'}):
        with pytest.raises(ValueError): validate_payload(obj, partial=True)


def test_missing_update_not_found(db):
    assert update_animal(db, 555, {'name':'Ника'}) is None


def test_size_and_city(db, animal_data):
    create_animal(db, {**animal_data, 'size': 'small'})
    assert list_animals(db, size='small')['total'] == 1
    assert list_animals(db, size='large')['total'] == 0
