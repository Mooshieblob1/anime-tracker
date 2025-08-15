from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Session, select
from ..config import settings
from ..db import get_session
from ..models import User as UserModel

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

router = APIRouter()

# In-memory users for MVP
_fake_users_db: Dict[str, Dict[str, Any]] = {}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = False

class UserInDB(User):
    hashed_password: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db: Dict[str, Dict[str, Any]], username: str) -> Optional[UserInDB]:
    user = db.get(username)
    if user:
        return UserInDB(**user)
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(_fake_users_db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode: Dict[str, Any] = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username_val = payload.get("sub")
        if not isinstance(username_val, str):
            raise credentials_exception
        username: str = username_val
    except JWTError:
        raise credentials_exception
    user = get_user(_fake_users_db, username)
    if user is None:
        # Try DB-backed user
        db_user = session.exec(select(UserModel).where(UserModel.username == username)).first()
        if db_user is None:
            raise credentials_exception
        return User(username=db_user.username, full_name=db_user.full_name, disabled=False)
    return user

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        # Try DB user; if not present and username is demo, auto-provision demo into DB for persistence
        db_user = session.exec(select(UserModel).where(UserModel.username == form_data.username)).first()
        if db_user is None and form_data.username == "demo":
            db_user = UserModel(
                username="demo",
                full_name="Demo User",
                hashed_password=pwd_context.hash("demo1234"),
            )
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
        if db_user and verify_password(form_data.password, db_user.hashed_password):
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": db_user.username}, expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer"}
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str | None = None


class RegisterResponse(BaseModel):
    id: int
    username: str


@router.post("/register", response_model=RegisterResponse)
def register(req: RegisterRequest, session: Session = Depends(get_session)) -> RegisterResponse:
    existing = session.exec(select(UserModel).where(UserModel.username == req.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = UserModel(
        username=req.username,
        full_name=req.full_name,
        hashed_password=pwd_context.hash(req.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return RegisterResponse(id=user.id, username=user.username)
