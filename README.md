# PPP Backend

A FastAPI backend for the PPP mobile application. Provides JWT-authenticated REST API endpoints for user management.

## Stack

- **FastAPI** – web framework
- **SQLAlchemy** – ORM
- **MySQL 8** – database
- **Alembic** – database migrations
- **passlib/bcrypt** – password hashing
- **python-jose** – JWT tokens
- **Docker / docker-compose** – containerization

## Project Structure

```
app/
├── api/v1/
│   ├── endpoints/
│   │   ├── auth.py      # register, login
│   │   └── users.py     # profile CRUD (protected)
│   └── routes.py        # router aggregation
├── core/
│   ├── config.py        # settings via env vars
│   └── security.py      # password hashing, JWT, auth dependency
├── db/
│   ├── base.py          # SQLAlchemy declarative base
│   └── session.py       # engine, session, get_db dependency
├── models/
│   └── user.py          # User ORM model
├── schemas/
│   └── user.py          # Pydantic request/response schemas
└── main.py              # app entry point, CORS
alembic/                 # database migrations
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Health check |
| POST | `/api/v1/auth/register` | No | Register new user |
| POST | `/api/v1/auth/login` | No | Login, returns JWT |
| GET | `/api/v1/users/me` | Yes | Get current user profile |
| PUT | `/api/v1/users/me` | Yes | Update current user profile |
| DELETE | `/api/v1/users/me` | Yes | Delete current user account |

Interactive API docs available at `http://localhost:8000/docs` when running.

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env and set a strong SECRET_KEY
```

### 2. Run with Docker

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### 3. Run database migrations

```bash
# Generate initial migration (after first run)
docker-compose exec api alembic revision --autogenerate -m "initial"

# Apply migrations
docker-compose exec api alembic upgrade head
```

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/app"
export SECRET_KEY="your-secret-key"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

## Authentication

The API uses **Bearer token** authentication. After login, include the token in the `Authorization` header:

```
Authorization: Bearer <token>
```

### Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret", "full_name": "Jane Doe"}'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'
```

Response:
```json
{"access_token": "<jwt>", "token_type": "bearer"}
```

## Interactive Shell

A Django-style interactive Python shell with the app context pre-loaded.

**Inside Docker (typical workflow):**
```bash
docker compose run api python shell.py
```

**Locally:**
```bash
python shell.py
```

The REPL starts with these pre-loaded:

| Name | What it is |
|---|---|
| `db` | Live SQLAlchemy session |
| `settings` | App config (`DATABASE_URL`, `SECRET_KEY`, etc.) |
| `User` | User ORM model |

Example queries:
```python
db.query(User).all()
db.query(User).filter(User.email == "alice@example.com").first()
db.query(User).count()
```

Uses IPython when available (tab-completion, history, `?` help), with a fallback to the stdlib REPL. Add new models to the `namespace` dict in `shell.py` as the project grows.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_NAME` | `PPP API` | API title shown in docs |
| `DATABASE_URL` | *(see .env.example)* | SQLAlchemy connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **always override** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime in minutes |
| `MYSQL_ROOT_PASSWORD` | `rootpassword` | MySQL root password (Docker only) |
