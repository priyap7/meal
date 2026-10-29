from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_and_food_reference():
    assert client.get('/api/health').status_code == 200
    foods = client.get('/api/foods').json()['items']
    assert any(x['key'] == 'pomegranate' for x in foods)
    assert any(x['key'] == 'pizza' for x in foods)

def test_unknown_nutrition_match_is_rejected():
    response = client.post('/api/nutrition/calculate', json={'food_key':'mystery meal','grams':200})
    assert response.status_code == 422

def test_meal_persists_and_can_be_deleted():
    payload = {'name':'Automated test meal','meal_type':'snack','items':[],'calories':104,'protein_g':0.6,'carbs_g':27.6,'fat_g':0.4,'fibre_g':4.8,'notes':'test','source':'test'}
    created = client.post('/api/meals', json=payload)
    assert created.status_code == 201
    meal_id = created.json()['id']
    assert any(x['id'] == meal_id for x in client.get('/api/meals').json())
    assert client.delete(f'/api/meals/{meal_id}').status_code == 204
    assert all(x['id'] != meal_id for x in client.get('/api/meals').json())

def test_rejects_non_image_upload():
    response = client.post('/api/analyze-image', files={'file':('note.txt',b'not image','text/plain')})
    assert response.status_code == 415
