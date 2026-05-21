# Auth Server — FastAPI + JWT (Production-ready)

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app — routes, token logic, rate limiting |
| `database.py` | SQLAlchemy models + SQLite session |
| `redis_store.py` | Refresh token storage + rate limiting via Redis |
| `security.py` | Brute-force lockout helpers |
| `.env.example` | All configurable values |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then edit SECRET_KEY at minimum
uvicorn main:app --reload     # dev
uvicorn main:app --workers 4  # prod
```

Interactive docs → **http://localhost:8000/docs**

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | **required** | JWT signing key — `openssl rand -hex 32` |
| `DATABASE_URL` | `sqlite:///./auth.db` | SQLAlchemy connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for refresh tokens + rate limits |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `RATE_LIMIT_PER_MINUTE` | `20` | Max requests per IP per minute |
| `MAX_FAILED_ATTEMPTS` | `5` | Failed logins before lockout |
| `LOCKOUT_MINUTES` | `15` | How long accounts stay locked |

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | Returns token pair |
| POST | `/auth/refresh` | — | Rotate refresh token |
| POST | `/auth/logout` | — | Revoke refresh token |
| GET | `/me` | Bearer | Current user info |

## Security features

- **bcrypt** password hashing
- **Short-lived access tokens** (15 min), **long-lived refresh tokens** (7 days)
- **Refresh token rotation** — each use invalidates the old token
- **Redis-backed token store** — survives restarts, tokens revocable instantly
- **Rate limiting** — 20 req/min per IP, tracked in Redis
- **Brute-force lockout** — account locked for 15 min after 5 bad passwords
- **User enumeration prevention** — same error for bad username or bad password

## Switching to Postgres later

```
DATABASE_URL=postgresql://user:password@localhost:5432/authdb
```
The `connect_args` in `database.py` is already conditional on the URL prefix.

## Running behind a reverse proxy (Nginx / Caddy)

Forward the real client IP so rate limiting works correctly:

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

And add `--proxy-headers` to your uvicorn command:

```bash
uvicorn main:app --workers 4 --proxy-headers --forwarded-allow-ips='*'
```
