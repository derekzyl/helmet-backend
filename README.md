# Smart Helmet

A production-shaped **FastAPI + async SQLAlchemy** backend template.

Use it when you want a clean API skeleton with auth, users, RBAC, and the usual infrastructure (Postgres, Redis, Alembic, mail) already wired — without shipping someone else’s business domain.

---

## Why this template

Most FastAPI “starters” either:

- stop at a hello-world + CRUD toy, or  
- dump a whole product (e-commerce, SaaS, pharmacy, etc.) that you have to rip out.


Clone it, rename it to *your* product, and grow domain modules under `app/core/`.

---

## Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI (ORJSON responses) |
| ORM | SQLAlchemy 2.x async |
| Driver | `asyncpg` (Postgres) |
| Auth | JWT (access + refresh) + optional OAuth |
| Passwords | bcrypt via Passlib |
| Cache | Redis (optional; app runs without it) |
| Migrations | Alembic |
| Settings | `pydantic-settings` + `.env` |
| Package manager | `uv` (or pip) |
| Python | **3.13+** |

---

## Features in detail

### Authentication (`/api/v1/auth`)

- **Register** — create `user` (default) or `admin` accounts  
- **Login** — email or username + password  
- **Access + refresh tokens** — refresh without re-login  
- **Logout** — invalidate refresh token  
- **Email verification** — OTP when `USE_MAIL_SERVICE=true`  
- **Forgot / reset password** — OTP flow  
- **Change password** — authenticated  
- **`GET /me`** — current user profile  
- **`GET /permissions`** — flat permission list for the UI  

Auth middleware attaches the current user to `request.state` on protected routes. Public paths (login, register, docs, health, social callbacks) are allow-listed.

### Social auth (`/api/v1/social`)

Optional Google / Facebook / GitHub OAuth. Configure client IDs and redirect URIs in `.env`. Safe to ignore until you need them.

### Users (`/api/v1/user`)

Admin-oriented account management built on a shared CRUD helper layer. User types start as:

- `user` — default application account  
- `admin` — platform administrator  

Extend `UserTypeEnum` in `app/core/users/types/type_user.py` for your domain (e.g. `organizer`, `vendor`).

### RBAC (`app/core/roles`)

SQLAlchemy models for:

- Roles  
- Permissions (resource + action)  
- User ↔ role assignments  
- Attribute-based permission hooks  

Seed catalogs live in `app/config/permissions.py` (platform + profile permissions). Decorators under `app/core/auth/decorators/` enforce permissions on routes.

### System

- **Health** — `GET /health` and `GET /api/v1/system/health`  
- **Settings** — key/value config (`SYSTEM_SETTING`)  
- **File upload** — metadata + Cloudinary-ready upload helpers  

### Admin

- Platform staff / role management  
- Performance monitoring endpoints  

---

## Requirements

- Python **3.13+**  
- PostgreSQL **14+** (async URL with `postgresql+asyncpg://…`)  
- Redis **optional** (caching degrades gracefully if unreachable)  
- [uv](https://github.com/astral-sh/uv) recommended  

---

## Quick start

```bash
# 1. Clone / copy this repo
cd fastapi-sqlalchemy-starter

# 2. Install dependencies
uv sync
# or: python -m venv .venv && source .venv/bin/activate && pip install -e .

# 3. Environment
cp .env.example .env
# Edit DATABASE_URL, JWT_SECRET, and anything else you need

# 4. Create the database
createdb fastapi_starter   # or use your Postgres UI / Docker

# 5. Run the API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- Swagger UI → [http://localhost:8000/docs](http://localhost:8000/docs)  
- ReDoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)  
- Welcome → [http://localhost:8000/](http://localhost:8000/)  
- Health → [http://localhost:8000/health](http://localhost:8000/health)  

On startup the app initializes the DB pool, optionally Redis, and runs `create_all` for registered models. Prefer Alembic migrations once your schema stabilizes (see below).

---

## Environment variables

Copy from `.env.example`. Important keys:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Async Postgres URL (`postgresql+asyncpg://…`) |
| `JWT_SECRET` | Long random string for signing tokens |
| `JWT_ACCESS_EXPIRY_TIME` | Access token lifetime (seconds) |
| `JWT_REFRESH_EXPIRY_TIME` | Refresh token lifetime (seconds) |
| `USE_MAIL_SERVICE` | `true` to send verify/reset emails |
| `MAIL_*` | SMTP host, port, credentials, sender |
| `REDIS_URL` | Redis connection (optional) |
| `CACHE_ENABLED` | Toggle Redis caching |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | SQLAlchemy pool sizing |
| `*_CLIENT_ID` / `*_SECRET` | Social OAuth (optional) |
| `CLOUDINARY_*` | Media uploads (optional) |
| `PAYSTACK_*` / `STRIPE_*` / … | Payment keys when you add billing |

Never commit a real `.env`. It is gitignored.

---

## Project structure

```
fastapi-sqlalchemy-starter/
├── alembic/                 # Migration environment
├── alembic.ini
├── app/
│   ├── app.py               # FastAPI factory, middleware, lifespan
│   ├── config/
│   │   ├── env.py           # Settings from .env
│   │   ├── permissions.py   # Permission catalog
│   │   └── database/
│   │       └── db.py        # Async session manager + BaseModelClass
│   ├── core/                # Feature modules (add your domain here)
│   │   ├── auth/
│   │   ├── users/
│   │   ├── roles/
│   │   ├── admin/
│   │   └── system/
│   ├── middleware/          # Performance, rate limiting
│   ├── utils/               # CRUD, cache, mail, JWT, crypto, logging
│   └── versions/            # API version registry (v1)
├── templates/               # Optional HTML email templates
├── main.py                  # ASGI entry: uvicorn main:app
├── pyproject.toml
├── .env.example
└── README.md
```

### How a feature module is organized

Each domain under `app/core/<name>/` follows the same pattern:

```
models/      # SQLAlchemy tables
types/       # TypedDict / Pydantic / enums for payloads
services/    # Business logic (uses CRUD helpers)
routes/      # APIRouter endpoints
```

Register the router in `app/versions/v1.py` so it mounts under `/api/v1/<path>`.

---

## API overview

Base prefix for versioned routes: **`/api/v1`**

| Area | Prefix | Access |
|------|--------|--------|
| Health | `/system` | Public |
| Auth | `/auth` | Mixed (public + authenticated) |
| Social | `/social` | Public |
| Users | `/user` | Admin |
| Platform staff | `/admin/platform-staff` | Admin |
| Performance | `/admin/performance` | Admin |
| Settings | `/system-setting` | Admin |
| Uploads | `/file-upload` | Authenticated |

### Auth cheat-sheet

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh-token
POST /api/v1/auth/logout
GET  /api/v1/auth/me
Authorization: Bearer <access_token>
```

Login response shape (simplified):

```json
{
  "user": { "id": "...", "email": "...", "user_type": "user", "...": "..." },
  "tokens": { "access_token": "...", "refresh_token": "..." },
  "message": "Login successful"
}
```

---

## Architecture notes

### Request path

1. CORS → GZip → performance middleware → **auth middleware**  
2. Router in `app/versions/v1.py`  
3. Route handler → service → CRUD / SQLAlchemy session  
4. ORJSON response  

### Database

- `DatabaseSessionManager` in `app/config/database/db.py` owns the engine and sessions  
- Models inherit `BaseModelClass` (id, timestamps, soft-delete / audit fields as defined there)  
- Inject sessions with `Depends(get_db)`  

### Caching

- `cache_manager` talks to Redis when enabled  
- Startup continues if Redis is down (warnings in logs)  

### Mail

- Lightweight SMTP + Jinja templates in `app/utils/mail/`  
- Templates: verify email, reset password, password changed, welcome  

---

## Adding your first domain module

Example: a **Bookings** feature for a product called BookIt.

### 1. Scaffold folders

```text
app/core/bookings/
  models/booking.py
  types/booking_types.py
  services/booking_service.py
  routes/booking_route.py
```

### 2. Define a model

```python
# app/core/bookings/models/booking.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.config.database.db import BaseModelClass

class BookingModel(BaseModelClass):
    __tablename__ = "BOOKING"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
```

### 3. Add a router

```python
# app/core/bookings/routes/booking_route.py
from fastapi import APIRouter
booking_router = APIRouter()

@booking_router.get("/")
async def list_bookings():
    return {"success": True, "data": []}
```

### 4. Register in `v1.py`

```python
from app.core.bookings.routes.booking_route import booking_router
# ...
{
    "api_route": booking_router,
    "path": "bookings",
    "tags": ["Bookings"],
    "access_level": AccessLevel.AUTHENTICATED,
    "description": "Create and manage bookings.",
},
```

Endpoint becomes: `GET /api/v1/bookings/`.

### 5. Permissions (optional)

Add entries to `app/config/permissions.py`, seed them, and guard routes with `@require_permission(...)`.

---

## Migrations (Alembic)

The app can create tables on startup for local bootstrap. For real work:

```bash
# Generate a revision after changing models
alembic revision --autogenerate -m "add bookings"

# Apply
alembic upgrade head
```

Ensure new models are imported so Alembic metadata sees them (typically via model packages or `env.py` imports).

---

## Development tips

- Prefer **services** for business rules; keep routes thin  
- Reuse `HybridCrudService` / CRUD helpers in `app/utils/crud/`  
- Keep response envelopes consistent with `response_message(...)`  
- Put new public routes on the auth middleware allow-list if they must skip JWT  
- Use Ruff: `ruff check --fix .`  

---

## Production checklist

- [ ] Strong unique `JWT_SECRET`  
- [ ] Postgres with managed backups  
- [ ] Redis for cache (recommended under load)  
- [ ] `USE_MAIL_SERVICE=true` + real SMTP  
- [ ] Restrict CORS origins in `app/app.py` to your frontends  
- [ ] Alembic migrations only (disable casual `create_all` in prod if you prefer)  
- [ ] HTTPS terminator (nginx, Caddy, cloud LB)  
- [ ] Rotate any secrets that ever lived in an old `.env`  

Example process supervisor command:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Renaming the template to your product

1. Change `name` / `description` in `pyproject.toml`  
2. Update title in `app/app.py` and `README.md`  
3. Update CORS allow-list for your domains  
4. Set `MAIL_SENDER_NAME` and branding in mail templates  
5. Add domain modules under `app/core/`  

Repo / package name recommendation stays **`fastapi-sqlalchemy-starter`** for the public template; your fork can become `bookit-api`, `acme-backend`, etc.

---

## Tech decisions (short)

- **Async end-to-end** — FastAPI + async SQLAlchemy + asyncpg fits IO-bound APIs  
- **ORJSON** — faster JSON for large payloads  
- **Hybrid auth middleware** — JWT verification with optional Redis-backed user cache  
- **Thin permissions catalog** — extend instead of starting from a huge domain matrix  
- **No forced multi-tenancy** — add `organization_id` / tenant tables when *you* need them  

---

## Contributing / license

Treat this as a starter kit: fork it, strip what you don’t need, and ship.

Use freely as a project template (no special license file shipped — add MIT/Apache-2.0 when you publish).

---

---

## Smart Helmet System Extensions

The backend is extended to support the IoT Smart Helmet and Motorcycle Ignition system:

### Smart Helmet Endpoints

| Domain | Base Path | Key Operations |
|:---|:---|:---|
| **Devices** | `/api/v1/devices` | Device registration, fleet listing, cryptographic pairing (`/pair`), and threshold configuration |
| **Telemetry** | `/api/v1/telemetry` | Real-time ingest (`/ingest`), offline batch flush (`/batch`), latest status, history |
| **Safety Events** | `/api/v1/events` | Incident dispatch (`/`), severity filtering, alert acknowledgement |
| **Emergency Contacts**| `/api/v1/contacts`| CRUD for emergency phone numbers and notification preferences |
| **Live WebSocket** | `/api/v1/ws/live` | Bidirectional real-time telemetry feed and instant accident alert broadcast |

### Running & Testing

```bash
# Seed initial fleet, rider, contact, and telemetry breadcrumb data:
uv run python scripts/seed_demo_data.py

# Run backend unit tests:
uv run pytest tests/test_smart_helmet.py -v

# Run interactive hardware simulator:
uv run python scripts/simulate_devices.py --scenario all

# Start backend server:
uv run uvicorn main:app --reload --port 8000
```

# helmet-backend
