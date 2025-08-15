from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    disabled: bool = False

    items: list["LibraryItem"] = Relationship(back_populates="user")


class LibraryItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    title: str
    type: str  # anime|manga
    source: str
    cover_url: Optional[str] = None

    status: str = "planning"
    progress: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship(back_populates="items")


class OAuthToken(SQLModel, table=True):
    """Stores OAuth access tokens per user and provider.

    Using a new table avoids schema changes on existing tables and works with create_all().
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    provider: str = Field(index=True)  # e.g., "anilist"
    access_token: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
