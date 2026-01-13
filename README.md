# Token System

Сервіс **Token System** реалізує внутрішню систему підписок та кредитів для доступу до AI‑генерації документів.  
Він забезпечує управління тарифними планами, балансами користувачів, транзакціями та адміністративними операціями.

## Роль Token System у мікросервісній архітектурі
 - Він відповідає за баланс кредитів користувачів.
 - Він знає про тарифні плани та їхні множники/бонуси.
 - Він виконує операції списання/поповнення кредитів.
 - Він надає internal API для інших сервісів (наприклад, сервіс «платежі» чи «AI‑генерація» може перевірити баланс або списати кредити).
 - Він надає public API для фронтенду (користувач бачить свій баланс, історію транзакцій, може купити кредити).
 - Він має admin API для управління тарифами, курсами конвертації та статистикою.

## Огляд

- Користувачі отримують доступ до сервісу через підписки.
- Кожна підписка має фіксовану вартість та набір кредитів.
- Кредити використовуються для генерації документів.
- Баланс можна поповнювати через покупку або бонуси.
- Усі операції є ідемпотентними та транзакційними.


## Технологічний стек

- **Мова програмування:** Python  
- **Фреймворк:** FastAPI  
- **База даних:** PostgreSQL  
- **ORM:** SQLAlchemy  
- **Кешування:** Redis  
- **Валідація:** Pydantic  
- **Архітектура:** мікросервісна, з розділенням на Internal API, Public API та Admin API


##  Основні концепти

### Підписка
- Тарифи: `basic`, `standard`, `premium`
- Поля: `monthly_cost`, `fixed_cost`, `credits_included`, `bonus_credits`, `multiplier`, `purchase_rate`
- При активації підписки користувач отримує кредити

### Кредити
- Використовуються для генерації документів
- Баланс зберігається у користувача
- Поля: `balance`, `total_earned`, `total_spent`

### Транзакції
- Типи: `charge`, `add`, `subscription`, `bonus`, `refund`
- Зберігають історію змін балансу
- Використовують `operation_id` для ідемпотентності


## Особливості реалізації

- **Ідемпотентність:** повторний запит з тим самим `operation_id` повертає результат першої операції  
- **Транзакційність:** усі операції виконуються у транзакціях БД  
- **Кешування:** баланс користувача кешується у Redis (TTL = 5 хв)  
- **Валідація:** перевірка достатності кредитів, коректності коефіцієнтів  
- **Логування:** усі операції логуються з повним контекстом  

---

##  API

### Internal API (мікросервіси)
- `GET /api/internal/credits/check/{user_id}` – перевірка балансу
- `POST /api/internal/credits/calculate` – розрахунок вартості операції
- `POST /api/internal/credits/charge` – списання кредитів
- `POST /api/internal/credits/add` – поповнення балансу
- `GET /api/internal/credits/balance/{user_id}` – отримання балансу
- `POST /api/internal/subscription/update` – оновлення підписки

### Public API (фронтенд)
- `GET /api/v1/subscription` – інформація про підписку
- `GET /api/v1/transactions` – історія транзакцій
- `POST /api/v1/credits/purchase` – покупка кредитів
- `GET /api/v1/subscription/plans` – доступні тарифні плани

### Admin API
- `POST /api/admin/subscription-plans` – створення/оновлення тарифу
- `PUT /api/admin/subscription-plans/{tier}` – оновлення тарифу
- `DELETE /api/admin/subscription-plans/{tier}` – видалення тарифу
- `GET /api/admin/subscription-plans` – список тарифів
- `PATCH /api/admin/subscription-plans/{tier}/multiplier` – оновлення коефіцієнта списання
- `PATCH /api/admin/subscription-plans/{tier}/purchase-rate` – оновлення коефіцієнта покупки
- `PATCH /api/admin/settings/exchange-rate` – оновлення базового курсу конвертації
- `GET /api/admin/statistics` – отримання статистики використання

---

##  Запуск Token System у Docker 
### Налаштування `.env` 
Створи файл `.env` у корені проєкту на основі `env.sample`:

### Запуск контейнерів

`docker-compose up --build`

Ця команда збере та запустить всі сервіси (api, db, redis).

### Ініціалізація бази даних

Після першого запуску потрібно створити таблиці у БД:

`docker exec -it token_system-api-1 python init_db.py`

Це робиться одноразово для створення базової схеми.

### Створіть хоча б одного користувача
`docker exec -it token_system-db-1 psql -U postgres -d token_system`

`INSERT INTO "users" (id) VALUES ('user_111');`

**user_111 - (!) обов'язково**: буде використано для перевірки **Authorization: Bearer my-secret-user-token**

### Відкриті Token System API

http://localhost:8000/docs

1) Admin API: `/api/admin/settings/exchange-rate`: додати base_rate  (default=10_000) 
2) Admin API: `/api/admin/subscription-plans`: додати subscription plan
3) Internal API: `/api/internal/subscription/update`: змінити subscription plan користувача
4) ...

#### Запуск tests/
дуже спрощене тестування, тільки зовнішній вигляд деяких GET API 

`docker exec -it token_system-api-1 pytest tests/ -v`

#### Check redis cache

`docker exec -it token_system-redis-1 redis-cli`

`KEYS *`