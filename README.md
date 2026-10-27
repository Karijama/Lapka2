# Lapka: учебное расширение REST API (2026)

Дополнительный модуль к учебному прототипу Lapka 2025 года. Исходный прототип имел HTML-интерфейс и CRUD для записей; этот модуль выделяет каталог животных с полями `species`, `city`, `age_years`, `status`, `shelter_id`, добавляет JSON API, поисковую фильтрацию и пагинацию.

## Локальный запуск

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

По умолчанию используется SQLite (`lapka.db`), для PostgreSQL установите переменную окружения `DATABASE_URL`, например `postgresql+psycopg://USER:PASSWORD@HOST:5432/lapka`.

## Примеры API

```sh
curl -X POST http://127.0.0.1:5000/api/animals -H "Content-Type: application/json" -d '{"name":"Мурка","species":"cat","city":"Якутск","age_years":2}'
curl 'http://127.0.0.1:5000/api/animals?species=cat&city=Якутск&page=1&per_page=10'
curl http://127.0.0.1:5000/api/animals/1
curl -X PUT http://127.0.0.1:5000/api/animals/1 -H "Content-Type: application/json" -d '{"status":"adopted"}'
curl -X DELETE http://127.0.0.1:5000/api/animals/1
```

## Тестирование

```sh
python -m pytest -q tests
```

Тесты покрывают бизнес-логику и операции с SQLite in-memory. HTTP-обработчики Flask не покрыты интеграционными тестами, внешний хостинг и сборка Docker не проверялись в среде подготовки материалов.

## Контейнеризация (команды для проверки при установленном Docker)

```sh
docker build -t lapka-api .
docker run --rm -p 8000:8000 lapka-api
```

Затем открыть `http://localhost:8000/api/animals`.

## Ограничения

Учебный прототип: нет аутентификации, модерации, защиты от злоупотреблений, миграций и автоматизированной проверки HTTP-контуров. Не использовать в публичном доступе с персональными данными без дополнительных мер безопасности.
