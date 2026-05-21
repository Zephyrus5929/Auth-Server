from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uuid

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = "change-me-in-production"          # openssl rand -hex 32
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ── App & helpers ─────────────────────────────────────────────────────────────
app = FastAPI(title="Auth Server")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Fake DB (replace with a real one) ────────────────────────────────────────
USERS_DB: dict[str, dict] = {}
REFRESH_TOKENS: set[str] = set()   # store in Redis / DB in production


# ── Schemas ───────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str
    password: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str


# ── Token helpers ─────────────────────────────────────────────────────────────
def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload.update({"exp": datetime.utcnow() + expires_delta, "jti": str(uuid.uuid4())})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_token_pair(username: str) -> TokenPair:
    access = create_token(
        {"sub": username, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh = create_token(
        {"sub": username, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    REFRESH_TOKENS.add(refresh)
    return TokenPair(access_token=access, refresh_token=refresh)

def decode_token(token: str, expected_type: str) -> str:
    """Decode a JWT and return the username, or raise 401."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise ValueError("wrong token type")
        username: str = payload["sub"]
        return username
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ── Dependency: current user from access token ────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    username = decode_token(token, "access")
    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: UserRegister):
    if body.username in USERS_DB:
        raise HTTPException(status_code=400, detail="Username already taken")
    USERS_DB[body.username] = {
        "username": body.username,
        "hashed_password": pwd_context.hash(body.password),
    }
    return {"message": "User created"}


@app.post("/auth/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = USERS_DB.get(form.username)
    if not user or not pwd_context.verify(form.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")
    return create_token_pair(form.username)


@app.post("/auth/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest):
    if body.refresh_token not in REFRESH_TOKENS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown refresh token")
    username = decode_token(body.refresh_token, "refresh")
    REFRESH_TOKENS.discard(body.refresh_token)   # rotate: old token is gone
    return create_token_pair(username)


@app.post("/auth/logout")
def logout(body: RefreshRequest):
    REFRESH_TOKENS.discard(body.refresh_token)
    return {"message": "Logged out"}


@app.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}
