"""HTTP integration tests (run with pytest after installing requirements)."""
import pytest
from app import create_app

@pytest.fixture()
def client(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE_URL':'sqlite:///' + str(tmp_path / 'site.db'),
                      'ADMIN_PASSWORD':'demo-pass', 'LAPKA_API_KEY':'demo-secret',
                      'SECRET_KEY':'unit-test-key'})
    with app.test_client() as cli:
        yield cli


def test_frontpage_is_html_not_json(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'<!doctype html>' in r.data
    assert '/animals' in r.get_data(as_text=True)


def test_catalog_and_404(client):
    assert client.get('/animals').status_code == 200
    assert client.get('/animals/999').status_code == 404
    assert client.get('/api/animals/999').status_code == 404


def test_anonymous_writes_are_forbidden(client):
    assert client.post('/api/animals',json={'name':'Мурка','species':'cat','city':'Якутск'}).status_code == 401
    assert client.get('/create/').status_code == 403


def test_api_crud(client):
    auth={'X-API-Key':'demo-secret'}
    data={'name':'Мурка','species':'cat','city':'Якутск','age_years':1}
    r=client.post('/api/animals',json=data,headers=auth)
    assert r.status_code == 201
    obj_id=r.json['id']
    assert client.get('/api/animals',query_string={'q':'МУР','city':'якуТСК'}).json['total']==1
    assert client.get(f'/animals/{obj_id}').status_code==200
    assert client.patch(f'/api/animals/{obj_id}',json={'status':'adopted'},headers=auth).status_code == 200
    assert client.delete(f'/api/animals/{obj_id}',headers=auth).status_code == 204
    assert client.get(f'/api/animals/{obj_id}').status_code == 404


def test_admin_login_and_csrf(client):
    page=client.get('/login')
    assert page.status_code == 200
    import re
    token=re.search(r'name="csrf_token" value="([^"]+)', page.get_data(as_text=True)).group(1)
    assert client.post('/login',data={'password':'demo-pass'},follow_redirects=False).status_code == 400
    r=client.post('/login',data={'password':'demo-pass','csrf_token':token})
    assert r.status_code == 302
    assert client.get('/create/').status_code==200


def test_api_pagination_validation(client):
    assert client.get('/api/animals?page=0').status_code == 400
    assert client.get('/api/animals?per_page=101').status_code == 400


def test_shelter_api(client):
    auth={'X-API-Key':'demo-secret'}
    assert client.post('/api/shelters',json={'name':'Приют','city':'Якутск'},headers=auth).status_code == 201
    assert client.get('/api/shelters').json['total']==1
    assert client.get('/shelters').status_code == 200
