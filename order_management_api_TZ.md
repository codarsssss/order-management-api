# Техническое задание: Order Management API

## 1. Цель проекта

Разработать законченный showcase-проект для портфолио backend-разработчика.

Проект должен выглядеть как небольшой коммерческий backend, а не как учебный `TODO API`.

Основной стек:

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- Docker
- Docker Compose
- pytest
- JWT-аутентификация
- REST API

Главная задача проекта — показать навыки:

- проектирования REST API;
- работы с PostgreSQL;
- построения понятной backend-архитектуры;
- реализации бизнес-логики;
- миграций БД;
- авторизации;
- обработки ошибок;
- тестирования;
- контейнеризации;
- интеграции с внешним API;
- документирования проекта.

Проект должен быть пригоден для публикации в публичном GitHub-репозитории.

Название репозитория:

`order-management-api`

---

# 2. Общая идея

Backend для небольшого сервиса управления заказами.

Пользователь после регистрации может:

- создавать клиентов;
- создавать товары и услуги;
- создавать заказы;
- добавлять позиции в заказ;
- менять статус заказа;
- получать список заказов;
- фильтровать и сортировать заказы;
- смотреть итоговую стоимость заказа;
- при необходимости получать стоимость заказа в другой валюте через внешний API курсов валют.

Frontend разрабатывать не нужно.

Swagger/OpenAPI FastAPI является основным интерфейсом для демонстрации API.

---

# 3. Ограничения проекта

Не нужно:

- микросервисов;
- Kubernetes;
- Kafka;
- сложного DDD;
- GraphQL;
- frontend;
- Redis, если он не нужен;
- Celery, если он не нужен;
- WebSocket;
- чрезмерного количества абстракций;
- искусственного усложнения архитектуры.

Код должен быть достаточно архитектурным для коммерческого проекта, но без overengineering.

---

# 4. Структура проекта

Рекомендуемая структура:

```text
order-management-api/
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── customers.py
│   │       ├── products.py
│   │       └── orders.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── order_item.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── customer.py
│   │   ├── product.py
│   │   └── order.py
│   │
│   ├── repositories/
│   │   ├── customers.py
│   │   ├── products.py
│   │   └── orders.py
│   │
│   ├── services/
│   │   ├── auth.py
│   │   ├── orders.py
│   │   └── currency.py
│   │
│   └── main.py
│
├── alembic/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_customers.py
│   ├── test_products.py
│   └── test_orders.py
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── README.md
└── Makefile
```

Допускается небольшое изменение структуры, если оно обосновано и сохраняет разделение:

- API;
- бизнес-логика;
- доступ к данным;
- модели;
- схемы.

---

# 5. Модель данных

## User

Поля:

- `id`
- `email`
- `hashed_password`
- `is_active`
- `created_at`
- `updated_at`

Требования:

- email уникальный;
- пароль хранится только в виде безопасного хеша;
- пользователь видит только свои сущности.

---

## Customer

Поля:

- `id`
- `owner_id`
- `name`
- `email`
- `phone`
- `comment`
- `created_at`
- `updated_at`

Связь:

```text
User 1 -> N Customer
```

Требования:

- клиент принадлежит конкретному пользователю;
- другой пользователь не должен иметь доступ к чужому клиенту.

---

## Product

Поля:

- `id`
- `owner_id`
- `name`
- `description`
- `price`
- `is_active`
- `created_at`
- `updated_at`

Требования:

- денежные значения хранить через `Decimal` / `NUMERIC`, а не `float`;
- цена должна быть `>= 0`;
- пользователь видит только свои товары.

---

## Order

Поля:

- `id`
- `owner_id`
- `customer_id`
- `status`
- `comment`
- `created_at`
- `updated_at`

Статусы:

```text
new
confirmed
processing
completed
cancelled
```

---

## OrderItem

Поля:

- `id`
- `order_id`
- `product_id`
- `quantity`
- `unit_price`

Требования:

- `quantity > 0`;
- `unit_price >= 0`;
- цена товара должна копироваться в `unit_price` при добавлении позиции;
- изменение цены товара в будущем не должно изменять старые заказы.

Связи:

```text
Order 1 -> N OrderItem
Product 1 -> N OrderItem
```

---

# 6. Бизнес-логика заказа

Итог заказа рассчитывается:

```text
total = SUM(order_item.quantity * order_item.unit_price)
```

Итоговая стоимость не должна храниться отдельным полем без необходимости.

API должен возвращать рассчитанный `total`.

---

# 7. Правила изменения статуса

Разрешённые переходы:

```text
new -> confirmed
new -> cancelled

confirmed -> processing
confirmed -> cancelled

processing -> completed
processing -> cancelled
```

Из:

```text
completed
cancelled
```

переходы запрещены.

При попытке запрещённого перехода API должен вернуть корректную бизнес-ошибку.

Например:

```json
{
  "detail": "Invalid order status transition"
}
```

HTTP status:

```text
409 Conflict
```

---

# 8. Аутентификация

Реализовать JWT Bearer authentication.

Endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

## Register

Пример:

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

Пароль:

- не хранить в исходном виде;
- использовать современный алгоритм хеширования.

---

## Login

Допускается:

- стандартный OAuth2 Password Flow FastAPI;

или

- JSON body.

Предпочтительно использовать стандартный механизм FastAPI/OpenAPI, чтобы Swagger позволял авторизоваться.

Ответ:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

# 9. Customers API

Endpoints:

```text
POST   /api/v1/customers
GET    /api/v1/customers
GET    /api/v1/customers/{customer_id}
PATCH  /api/v1/customers/{customer_id}
DELETE /api/v1/customers/{customer_id}
```

Для списка реализовать:

- pagination;
- поиск по имени;
- поиск по email.

Пример:

```text
GET /api/v1/customers?search=ivan&page=1&page_size=20
```

---

# 10. Products API

Endpoints:

```text
POST   /api/v1/products
GET    /api/v1/products
GET    /api/v1/products/{product_id}
PATCH  /api/v1/products/{product_id}
DELETE /api/v1/products/{product_id}
```

Фильтры:

```text
is_active
search
min_price
max_price
```

Пример:

```text
GET /api/v1/products?is_active=true&min_price=100&max_price=5000
```

---

# 11. Orders API

Endpoints:

```text
POST   /api/v1/orders
GET    /api/v1/orders
GET    /api/v1/orders/{order_id}
PATCH  /api/v1/orders/{order_id}
DELETE /api/v1/orders/{order_id}
```

Дополнительные endpoints:

```text
POST   /api/v1/orders/{order_id}/items
PATCH  /api/v1/orders/{order_id}/items/{item_id}
DELETE /api/v1/orders/{order_id}/items/{item_id}

PATCH  /api/v1/orders/{order_id}/status
```

---

# 12. Создание заказа

Пример:

```json
{
  "customer_id": 10,
  "comment": "Позвонить перед доставкой",
  "items": [
    {
      "product_id": 5,
      "quantity": 2
    },
    {
      "product_id": 8,
      "quantity": 1
    }
  ]
}
```

API должен:

1. проверить существование клиента;
2. проверить, что клиент принадлежит текущему пользователю;
3. проверить существование товаров;
4. проверить принадлежность товаров пользователю;
5. проверить активность товаров;
6. скопировать текущую цену каждого товара в `unit_price`;
7. создать заказ;
8. создать позиции заказа;
9. вернуть заказ вместе с позициями и `total`.

Операция должна выполняться транзакционно.

Если одна из позиций невалидна, заказ не должен создаваться частично.

---

# 13. Получение списка заказов

Endpoint:

```text
GET /api/v1/orders
```

Поддержать:

- pagination;
- фильтрацию по status;
- фильтрацию по customer_id;
- диапазон дат;
- сортировку.

Пример:

```text
GET /api/v1/orders?status=processing&customer_id=10&page=1&page_size=20
```

Допустимые сортировки:

```text
created_at
-total
total
```

Если сортировка по вычисляемому total заметно усложняет реализацию — допустимо оставить сортировку только по:

```text
created_at
-created_at
```

Но это решение нужно явно описать в README.

---

# 14. Валютная интеграция

Добавить небольшую интеграцию с публичным API курсов валют.

Endpoint:

```text
GET /api/v1/orders/{order_id}/total
```

Без параметра:

```json
{
  "currency": "RUB",
  "total": "12500.00"
}
```

С параметром:

```text
GET /api/v1/orders/{order_id}/total?currency=USD
```

Ответ:

```json
{
  "currency": "USD",
  "total": "137.40",
  "rate": "..."
}
```

Требования:

- внешний HTTP-клиент должен быть асинхронным;
- использовать timeout;
- корректно обрабатывать недоступность внешнего сервиса;
- код внешней интеграции вынести в отдельный service;
- URL внешнего API не хардкодить в бизнес-логике;
- интеграция должна легко мокаться в тестах.

Если выбранный публичный сервис требует API key, ключ должен передаваться через environment variables.

В README указать используемый внешний сервис.

---

# 15. Ошибки API

Сделать единообразную обработку ошибок.

Использовать корректные HTTP codes:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
```

Примеры:

```json
{
  "detail": "Customer not found"
}
```

```json
{
  "detail": "Product is inactive"
}
```

```json
{
  "detail": "Invalid order status transition"
}
```

Не отдавать наружу traceback или внутренние SQL-ошибки.

---

# 16. PostgreSQL

Использовать PostgreSQL как основную БД.

Не использовать SQLite в production-конфигурации.

Требования:

- foreign keys;
- unique constraints;
- indexes там, где они логически нужны;
- корректные типы данных;
- timestamps;
- миграции через Alembic.

---

# 17. SQLAlchemy

Использовать SQLAlchemy 2.x style.

Предпочтительно:

- declarative models;
- `Mapped`;
- `mapped_column`;
- async engine;
- `AsyncSession`.

Избегать устаревшего SQLAlchemy legacy API.

---

# 18. Alembic

Должна быть минимум одна полноценная миграция, создающая структуру БД.

После:

```bash
alembic upgrade head
```

база должна полностью подготавливаться к работе.

---

# 19. Конфигурация

Использовать environment variables.

Пример `.env.example`:

```env
APP_NAME=Order Management API
DEBUG=false

POSTGRES_DB=orders
POSTGRES_USER=orders
POSTGRES_PASSWORD=orders
POSTGRES_HOST=db
POSTGRES_PORT=5432

JWT_SECRET=change-me
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

CURRENCY_API_URL=...
CURRENCY_API_KEY=
```

Реальный `.env` не должен попадать в Git.

---

# 20. Docker

Приложение должно запускаться командой:

```bash
docker compose up --build
```

Минимум два контейнера:

```text
api
db
```

PostgreSQL должен использовать volume.

API должен быть доступен:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

# 21. Healthcheck

Добавить endpoint:

```text
GET /health
```

Ответ:

```json
{
  "status": "ok"
}
```

Желательно проверить соединение с БД.

Допустимый вариант:

```json
{
  "status": "ok",
  "database": "ok"
}
```

---

# 22. Тесты

Использовать:

```text
pytest
```

Минимально покрыть тестами:

## Auth

- регистрация;
- повторная регистрация с тем же email;
- login;
- запрос без токена.

## Customers

- создание;
- получение;
- обновление;
- удаление;
- запрет доступа к чужому customer.

## Products

- создание;
- валидация отрицательной цены;
- фильтрация;
- запрет доступа к чужому product.

## Orders

- создание заказа;
- расчёт total;
- сохранение `unit_price`;
- невозможность добавить чужой product;
- невозможность добавить inactive product;
- корректный переход статуса;
- запрещённый переход статуса;
- rollback при ошибке создания заказа.

## External API

Не делать реальные HTTP-запросы к валютному сервису в unit/integration tests.

Использовать mock.

---

# 23. Code quality

Добавить:

```text
ruff
```

или аналогичный современный линтер.

Опционально:

```text
mypy
```

Но mypy не обязателен, если его настройка начинает непропорционально усложнять проект.

Код должен быть:

- типизирован;
- без очевидного дублирования;
- с понятными именами;
- без закомментированного мусора;
- без секретов;
- без debug-print.

---

# 24. Makefile

Добавить удобные команды.

Например:

```makefile
up:
	docker compose up --build

down:
	docker compose down

test:
	docker compose run --rm api pytest

lint:
	docker compose run --rm api ruff check .

migrate:
	docker compose run --rm api alembic upgrade head
```

Можно реализовать эквивалентные команды.

---

# 25. README

README является важной частью проекта.

Он должен быть написан так, чтобы заказчик мог понять проект за 2–3 минуты.

Обязательные разделы:

```text
# Order Management API

## About
## Features
## Tech Stack
## Architecture
## Data Model
## API
## Authentication
## Order Status Workflow
## External API Integration
## Quick Start
## Environment Variables
## Migrations
## Tests
## Project Structure
```

---

# 26. README: начало

README должен начинаться примерно так:

```markdown
# Order Management API

Production-style REST API for managing customers, products and orders.

Built with FastAPI, PostgreSQL, SQLAlchemy 2, Alembic and Docker.

The project demonstrates:

- JWT authentication
- REST API design
- PostgreSQL data modeling
- transactional order creation
- business rules for order statuses
- filtering and pagination
- external API integration
- automated tests
- Dockerized local environment
```

Не писать:

```text
This is my pet project.
This project was created for learning.
Homework.
Educational project.
```

Проект позиционируется как showcase/commercial-style backend.

---

# 27. Swagger

Все endpoints должны корректно отображаться в `/docs`.

Разнести endpoints по tags:

```text
Auth
Customers
Products
Orders
System
```

Добавить:

- summary;
- понятные Pydantic schemas;
- response models;
- корректные status codes.

---

# 28. Pagination

Использовать простой понятный формат.

Например:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 125
}
```

Не подключать тяжёлую библиотеку только ради pagination.

---

# 29. Ownership / безопасность данных

Это обязательная часть проекта.

Каждая сущность должна принадлежать пользователю.

Нельзя делать:

```python
select(Customer).where(Customer.id == customer_id)
```

без проверки владельца.

Логика должна учитывать:

```text
resource.owner_id == current_user.id
```

Чужие объекты не должны быть доступны через подстановку ID.

Предпочтительный ответ:

```text
404 Not Found
```

чтобы не раскрывать существование чужого объекта.

---

# 30. Транзакции

Создание заказа с позициями должно быть атомарным.

Нельзя получить ситуацию:

```text
Order создан
OrderItem #1 создан
OrderItem #2 упал
Order остался в БД
```

При ошибке вся операция должна rollback.

---

# 31. Денежные значения

Не использовать:

```python
float
```

для стоимости.

Использовать:

```python
Decimal
```

и PostgreSQL:

```text
NUMERIC(12, 2)
```

или аналогичный тип.

API должен возвращать денежные значения без ошибок бинарного float.

---

# 32. Даты

Использовать timezone-aware datetime.

В API отдавать ISO 8601.

Например:

```text
2026-09-10T12:30:00Z
```

---

# 33. Начальные данные

Опционально сделать простой seed/demo script.

Например:

```bash
python -m scripts.seed
```

Он может создать:

- demo user;
- несколько customers;
- несколько products;
- один order.

Это удобно для демонстрации проекта.

Seed не является обязательным, если заметно увеличивает объём работы.

---

# 34. GitHub Actions

Если реализация не требует большого времени, добавить:

```text
.github/workflows/ci.yml
```

На:

```text
push
pull_request
```

выполнять:

```text
ruff check
pytest
```

CI должен быть зелёным.

Это желательно, но не должно блокировать завершение основного проекта.

---

# 35. Definition of Done

Проект считается завершённым, если выполняются все обязательные условия:

- [ ] приложение запускается через Docker Compose;
- [ ] используется FastAPI;
- [ ] используется PostgreSQL;
- [ ] используется SQLAlchemy 2.x;
- [ ] есть Alembic migrations;
- [ ] есть JWT auth;
- [ ] есть users;
- [ ] есть customers CRUD;
- [ ] есть products CRUD;
- [ ] есть orders;
- [ ] есть order items;
- [ ] работает расчёт total;
- [ ] цена позиции фиксируется на момент заказа;
- [ ] есть workflow статусов заказа;
- [ ] запрещены невалидные переходы;
- [ ] проверяется ownership;
- [ ] создание заказа транзакционное;
- [ ] есть pagination;
- [ ] есть фильтрация;
- [ ] есть внешняя валютная интеграция;
- [ ] внешняя интеграция мокается в тестах;
- [ ] есть pytest tests;
- [ ] есть `/health`;
- [ ] есть `.env.example`;
- [ ] секреты не находятся в Git;
- [ ] есть README;
- [ ] Swagger полностью работает;
- [ ] проект можно клонировать и запустить по README.

---

# 36. Приоритеты

Если времени не хватает, реализовывать в следующем порядке.

## P0 — обязательно

1. FastAPI.
2. PostgreSQL.
3. Docker Compose.
4. SQLAlchemy.
5. Alembic.
6. Auth.
7. Customers.
8. Products.
9. Orders.
10. OrderItems.
11. Ownership.
12. Status workflow.
13. Transactions.
14. Tests.
15. README.

## P1 — желательно

1. Currency API.
2. Filtering.
3. Pagination.
4. Healthcheck.
5. Ruff.
6. Makefile.

## P2 — если остаётся время

1. GitHub Actions.
2. Seed script.
3. Дополнительные тесты.

---

# 37. Инструкция Codex по способу работы

Перед реализацией:

1. Прочитать всё ТЗ.
2. Составить краткий implementation plan.
3. Создать архитектуру проекта.
4. Реализовывать проект по этапам.
5. После каждого значимого этапа запускать тесты.
6. Не оставлять проект в partially-working состоянии.
7. Не менять требования без необходимости.
8. Если возникает неоднозначность — выбирать простое production-like решение.

---

# 38. Правила для Codex

Необходимо:

- писать реальный рабочий код;
- не оставлять `TODO` вместо реализации;
- не использовать фиктивные заглушки в production code;
- не добавлять зависимости без необходимости;
- использовать актуальные стабильные версии библиотек;
- обеспечить совместимость зависимостей;
- проверять запуск проекта;
- проверять миграции;
- проверять тесты;
- проверять Swagger/OpenAPI.

После завершения Codex должен выполнить:

```text
1. Запуск линтера.
2. Запуск тестов.
3. Проверку docker compose config.
4. Проверку миграций.
5. Проверку запуска приложения.
```

Если какое-либо действие невозможно выполнить в текущем окружении, это нужно явно указать в итоговом отчёте.

---

# 39. Финальный отчёт Codex

После завершения реализации предоставить:

```text
## Implemented
- ...

## Architecture
- ...

## API
- ...

## Tests
- ...

## Commands
- ...

## Known limitations
- ...

## Verification
- tests: PASS / FAIL
- lint: PASS / FAIL
- migrations: PASS / FAIL
- docker: PASS / FAIL
```

Не скрывать ошибки и непроверенные части.

---

# 40. Цель для портфолио

После завершения проект должен позволять разместить в портфолио описание:

> **Order Management API — FastAPI + PostgreSQL + Docker**
>
> Backend API для управления клиентами, товарами и заказами. Реализованы JWT-аутентификация, PostgreSQL, SQLAlchemy 2, Alembic, транзакционное создание заказов, бизнес-правила изменения статусов, фильтрация, пагинация, интеграция с внешним API и автоматические тесты. Проект полностью контейнеризирован и запускается через Docker Compose.

Проект должен быть достаточно компактным для быстрого изучения заказчиком, но достаточно содержательным, чтобы демонстрировать уровень backend-разработчика, способного работать с существующими коммерческими проектами и разрабатывать отдельные backend-модули под ключ.
