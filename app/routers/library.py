from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .auth import get_current_user, User, pwd_context
from ..models import LibraryItem, User as UserModel
from ..db import get_session

router = APIRouter()


class MediaBase(BaseModel):
    title: str
    type: str  # "anime" or "manga"
    source: str  # e.g., "anilist", "mangaDex"
    cover_url: Optional[str] = None


class Media(MediaBase):
    id: int
    status: str  # e.g., "reading", "watching", "completed", "on-hold"
    progress: int = 0  # chapters or episodes


class MediaCreate(MediaBase):
    status: str = "planning"
    progress: int = 0


class MediaUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None

def get_or_create_db_user(session: Session, username: str) -> UserModel:
    db_user = session.exec(select(UserModel).where(UserModel.username == username)).first()
    if db_user:
        return db_user
    # Auto-provision demo user into DB so choices persist across restarts
    if username == "demo":
        user = UserModel(username="demo", full_name="Demo User", hashed_password=pwd_context.hash("demo1234"))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    # For safety, return a user record for any authenticated username (should be registered already)
    # This path should rarely occur because non-demo users are expected to register first.
    user = UserModel(username=username, full_name=None, hashed_password=pwd_context.hash("!placeholder!"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/items", response_model=List[Media])
async def list_items(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    db_user = get_or_create_db_user(session, current_user.username)
    items = session.exec(select(LibraryItem).where(LibraryItem.user_id == db_user.id)).all()
    result: List[Media] = []
    for i in items:
        assert i.id is not None
        result.append(
        Media(
            id=i.id,
            title=i.title,
            type=i.type,
            source=i.source,
            cover_url=i.cover_url,
            status=i.status,
            progress=i.progress,
        ))
    return result


@router.post("/items", response_model=Media)
async def add_item(
    item: MediaCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    db_user = get_or_create_db_user(session, current_user.username)
    assert db_user.id is not None
    rec = LibraryItem(user_id=db_user.id, **item.model_dump())
    session.add(rec)
    session.commit()
    session.refresh(rec)
    assert rec.id is not None
    return Media(
        id=rec.id,
        title=rec.title,
        type=rec.type,
        source=rec.source,
        cover_url=rec.cover_url,
        status=rec.status,
        progress=rec.progress,
    )


@router.get("/items/{item_id}", response_model=Media)
async def get_item(
    item_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    db_user = get_or_create_db_user(session, current_user.username)
    rec = session.get(LibraryItem, item_id)
    if not rec or rec.user_id != db_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    assert rec.id is not None
    return Media(
        id=rec.id,
        title=rec.title,
        type=rec.type,
        source=rec.source,
        cover_url=rec.cover_url,
        status=rec.status,
        progress=rec.progress,
    )


@router.patch("/items/{item_id}", response_model=Media)
async def update_item(
    item_id: int,
    update: MediaUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    db_user = get_or_create_db_user(session, current_user.username)
    rec = session.get(LibraryItem, item_id)
    if not rec or rec.user_id != db_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    data = update.model_dump(exclude_unset=True)
    if data.get("status") is not None:
        rec.status = data["status"]
    if data.get("progress") is not None:
        rec.progress = data["progress"]
    # touch updated_at
    from datetime import datetime, timezone
    rec.updated_at = datetime.now(timezone.utc)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    assert rec.id is not None
    return Media(
        id=rec.id,
        title=rec.title,
        type=rec.type,
        source=rec.source,
        cover_url=rec.cover_url,
        status=rec.status,
        progress=rec.progress,
    )


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    db_user = get_or_create_db_user(session, current_user.username)
    rec = session.get(LibraryItem, item_id)
    if rec and rec.user_id == db_user.id:
        session.delete(rec)
        session.commit()
    return {"ok": True}


@router.get("/summary")
async def summary(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, object]:
    db_user = get_or_create_db_user(session, current_user.username)
    items = session.exec(select(LibraryItem).where(LibraryItem.user_id == db_user.id)).all()
    total = len(items)
    by_type = {"anime": 0, "manga": 0}
    by_status: dict[str, int] = {}
    for i in items:
        t = (i.type or "").lower()
        if t in by_type:
            by_type[t] += 1
        else:
            by_type[t] = by_type.get(t, 0) + 1
        by_status[i.status] = by_status.get(i.status, 0) + 1
    return {"total": total, "by_type": by_type, "by_status": by_status}
