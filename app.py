from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from sqlalchemy import select
from models import Animal, Shelter, make_session_factory
from services import (GENDERS, SIZES, SPECIES, STATUSES, create_animal, delete_animal,
                      get_animal, list_animals, list_cities, list_shelters, stats,
                      update_animal, validate_payload)

# Read persistent local configuration before Flask is created.
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE_URL=os.environ.get("DATABASE_URL") or "sqlite:///" + (ROOT / "instance" / "lapka.db").as_posix(),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        LAPKA_API_KEY=os.environ.get("LAPKA_API_KEY", ""),
        MAX_CONTENT_LENGTH=1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    if app.config["DATABASE_URL"].startswith("sqlite:///"):
        Path(app.config["DATABASE_URL"][10:]).parent.mkdir(parents=True, exist_ok=True)
    Session, engine = make_session_factory(app.config["DATABASE_URL"])
    app.extensions["lapka_session_factory"] = Session
    app.extensions["lapka_engine"] = engine

    @app.context_processor
    def globals_for_templates():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"], "is_admin": bool(session.get("admin")),
                "species_labels": SPECIES, "status_labels": STATUSES,
                "gender_labels": GENDERS, "size_labels": SIZES}

    def verify_csrf():
        token = request.form.get("csrf_token", "")
        if not token or not hmac.compare_digest(token, session.get("csrf_token", "")):
            abort(400, "Форма устарела. Обновите страницу и повторите отправку.")

    def admin_required():
        if not session.get("admin"):
            abort(403, "Для изменения объявлений войдите как администратор")

    def require_api_key():
        key = app.config.get("LAPKA_API_KEY", "")
        incoming = request.headers.get("X-API-Key", "")
        if not key or not incoming or not hmac.compare_digest(key, incoming):
            return jsonify(error="Требуется действующий X-API-Key"), 401
        return None

    def parse_form():
        names = ("name", "species", "city", "description", "status", "gender", "size",
                 "photo_url", "contact_email")
        payload = {name: request.form.get(name, "").strip() for name in names}
        payload["vaccinated"] = "vaccinated" in request.form
        payload["neutered"] = "neutered" in request.form
        age = request.form.get("age_years", "").strip()
        shelter = request.form.get("shelter_id", "").strip()
        try:
            payload["age_years"] = int(age) if age else None
            payload["shelter_id"] = int(shelter) if shelter else None
        except ValueError:
            raise ValueError("Возраст и ID приюта должны быть числами")
        return payload

    @app.get("/")
    def index():
        try:
            page = int(request.args.get("page", "1"))
            filters = {k: request.args.get(k, "").strip() for k in ("q", "species", "city", "status", "size")}
            with Session() as db:
                results = list_animals(db, **filters, page=page, per_page=10)
                cities = list_cities(db)
        except ValueError as exc:
            abort(400, str(exc))
        return render_template("index.html", results=results, filters=filters, cities=cities)

    @app.get("/animals")
    def catalog():
        try:
            page = int(request.args.get("page", "1"))
            filters = {k: request.args.get(k, "").strip() for k in ("q", "species", "city", "status", "size")}
            with Session() as db:
                results = list_animals(db, **filters, page=page, per_page=10)
                cities = list_cities(db)
        except ValueError as exc:
            abort(400, str(exc))
        return render_template("catalog.html", results=results, filters=filters, cities=cities)

    @app.get("/animals/<int:animal_id>")
    def animal_detail(animal_id):
        with Session() as db:
            animal = db.get(Animal, animal_id)
            if animal is None:
                abort(404)
            item = get_animal(db, animal_id)
            related = [a for a in list_animals(db, species=animal.species, status="searching", per_page=4)["items"]
                       if a["id"] != animal_id][:3]
        return render_template("detail.html", animal=item, related=related)

    @app.get("/shelters")
    def shelters():
        with Session() as db:
            rows = [{"id": shelter.id, "name": shelter.name, "city": shelter.city,
                     "description": shelter.description, "count": len(shelter.animals)}
                    for shelter in list_shelters(db)]
        return render_template("shelters.html", shelters=rows)

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            verify_csrf()
            configured = app.config.get("ADMIN_PASSWORD", "")
            if configured and hmac.compare_digest(configured, request.form.get("password", "")):
                session.clear()
                session["admin"] = True
                session["csrf_token"] = secrets.token_urlsafe(32)
                flash("Вы вошли как администратор", "success")
                return redirect(url_for("catalog"))
            flash("Неверный пароль или ADMIN_PASSWORD не настроен", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        verify_csrf()
        session.clear()
        flash("Вы вышли из панели управления", "info")
        return redirect(url_for("index"))

    @app.route("/create/", methods=["GET", "POST"])
    def create():
        admin_required()
        with Session() as db:
            shelter_rows = list_shelters(db)
            if request.method == "POST":
                verify_csrf()
                try:
                    result = create_animal(db, parse_form())
                    flash("Анкета успешно опубликована", "success")
                    return redirect(url_for("animal_detail", animal_id=result["id"]))
                except ValueError as exc:
                    flash(str(exc), "error")
            return render_template("create.html", item=None, shelters=shelter_rows)

    @app.route("/<int:animal_id>/edit/", methods=["GET", "POST"])
    def edit(animal_id):
        admin_required()
        with Session() as db:
            item = get_animal(db, animal_id)
            if item is None:
                abort(404)
            shelter_rows = list_shelters(db)
            if request.method == "POST":
                verify_csrf()
                try:
                    update_animal(db, animal_id, parse_form())
                    flash("Изменения сохранены", "success")
                    return redirect(url_for("animal_detail", animal_id=animal_id))
                except ValueError as exc:
                    flash(str(exc), "error")
            return render_template("edit.html", item=item, shelters=shelter_rows)

    @app.post("/<int:animal_id>/delete/")
    def delete(animal_id):
        admin_required()
        verify_csrf()
        with Session() as db:
            if not delete_animal(db, animal_id):
                abort(404)
        flash("Анкета удалена", "info")
        return redirect(url_for("catalog"))

    @app.get("/api/animals")
    def api_animals():
        try:
            page = int(request.args.get("page", "1"))
            per_page = int(request.args.get("per_page", "10"))
            params = {k: request.args.get(k, "") for k in ("q", "species", "city", "status", "size")}
            with Session() as db:
                return jsonify(list_animals(db, **params, page=page, per_page=per_page))
        except (ValueError, TypeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/api/animals/<int:animal_id>")
    def api_animal_detail(animal_id):
        with Session() as db:
            result = get_animal(db, animal_id)
        return jsonify(result) if result else (jsonify(error="Объявление не найдено"), 404)

    @app.post("/api/animals")
    def api_create():
        failure = require_api_key()
        if failure is not None:
            return failure
        try:
            with Session() as db:
                return jsonify(create_animal(db, request.get_json(silent=True))), 201
        except (ValueError, TypeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.route("/api/animals/<int:animal_id>", methods=["PUT", "PATCH"])
    def api_update(animal_id):
        failure = require_api_key()
        if failure is not None:
            return failure
        try:
            with Session() as db:
                result = update_animal(db, animal_id, request.get_json(silent=True))
            return jsonify(result) if result else (jsonify(error="Объявление не найдено"), 404)
        except (ValueError, TypeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.delete("/api/animals/<int:animal_id>")
    def api_delete(animal_id):
        failure = require_api_key()
        if failure is not None:
            return failure
        with Session() as db:
            existed = delete_animal(db, animal_id)
        return ("", 204) if existed else (jsonify(error="Объявление не найдено"), 404)

    @app.get("/api/shelters")
    def api_shelters():
        with Session() as db:
            rows = [{"id": s.id, "name": s.name, "city": s.city, "description": s.description}
                    for s in list_shelters(db)]
        return jsonify(items=rows, total=len(rows))

    @app.post("/api/shelters")
    def api_create_shelter():
        failure = require_api_key()
        if failure is not None:
            return failure
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Ожидается JSON-объект"), 400
        name, city, description = payload.get("name"), payload.get("city"), payload.get("description", "")
        if not all(isinstance(x, str) for x in (name, city, description)) or not name.strip() or not city.strip():
            return jsonify(error="Укажите название и город приюта"), 400
        if len(name.strip()) > 120 or len(city.strip()) > 100 or len(description) > 3000:
            return jsonify(error="Слишком длинные поля"), 400
        with Session() as db:
            obj = Shelter(name=name.strip(), city=city.strip(), description=description.strip())
            db.add(obj)
            db.commit()
            return jsonify(id=obj.id, name=obj.name, city=obj.city), 201

    @app.get("/health")
    def health():
        return jsonify(status="ok", app="Lapka")

    @app.errorhandler(404)
    def handle_404(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Страница не найдена"), 404
        return render_template("error.html", code=404, message="Не удалось найти эту страницу"), 404

    @app.errorhandler(403)
    def handle_403(error):
        return render_template("error.html", code=403, message=error.description), 403

    @app.errorhandler(400)
    def handle_400(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), 400
        return render_template("error.html", code=400, message=error.description), 400

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
