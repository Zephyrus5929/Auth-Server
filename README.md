# Auth Server — FastAPI + JWT

A minimal auth server with access/refresh token rotation.

## Setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Interactive docs at **http://localhost:8000/docs**

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account (`{"username", "password"}`) |
| POST | `/auth/login` | Login — returns token pair (form data) |
| POST | `/auth/refresh` | Swap refresh token for a new pair |
| POST | `/auth/logout` | Invalidate a refresh token |
| GET | `/me` | Protected route — returns current user |

## Token flow

```
register → login → { access_token, refresh_token }
                        │                │
                 use for API calls   keep safe; swap for
                 (15 min lifetime)   new pair when access expires
                                     (7 day lifetime, rotated on use)
```

## Before going to production

- Replace `SECRET_KEY` with a real secret (`openssl rand -hex 32`)
- Swap `USERS_DB` dict for a real database (SQLAlchemy, Tortoise, etc.)
- Swap `REFRESH_TOKENS` set for Redis or a DB table
- Add HTTPS, rate limiting, and account lockout logic
