"""Educational JSON API for the Lapka project.
Run after installing requirements: python app.py
"""
import os
from flask import Flask, jsonify, request
from models import session_factory
from services import create_animal, delete_animal, get_animal, list_animals, update_animal

app = Flask(__name__)
Session = session_factory(os.environ.get("DATABASE_URL", "sqlite:///lapka.db"))

@app.get('/api/animals')
def animals():
    try:
        with Session() as session:
            result = list_animals(session, species=request.args.get('species'),
                city=request.args.get('city'), status=request.args.get('status'),
                q=request.args.get('q'), page=int(request.args.get('page', 1)),
                per_page=int(request.args.get('per_page', 10)))
            return jsonify(result)
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400

@app.get('/api/animals/<int:animal_id>')
def animal_detail(animal_id):
    with Session() as session:
        row = get_animal(session, animal_id)
        return (jsonify(row), 200) if row else (jsonify(error='not found'), 404)

@app.post('/api/animals')
def animal_create():
    try:
        with Session() as session:
            row = create_animal(session, request.get_json(silent=True))
            return jsonify(row), 201
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400

@app.put('/api/animals/<int:animal_id>')
def animal_update(animal_id):
    try:
        with Session() as session:
            row = update_animal(session, animal_id, request.get_json(silent=True))
            return (jsonify(row), 200) if row else (jsonify(error='not found'), 404)
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400

@app.delete('/api/animals/<int:animal_id>')
def animal_delete(animal_id):
    with Session() as session:
        found = delete_animal(session, animal_id)
        return ('', 204) if found else (jsonify(error='not found'), 404)

if __name__ == '__main__':
    app.run(debug=True)
