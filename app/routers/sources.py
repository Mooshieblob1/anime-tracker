from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services.anilist import search_titles
from .auth import get_current_user, User

router = APIRouter()

# MVP: hardcoded sources and a mock search
class Source(BaseModel):
    id: str
    name: str
    type: str  # anime|manga

SOURCES: list[Source] = [
    Source(id="anilist", name="AniList", type="both"),
    Source(id="mangadex", name="MangaDex", type="manga"),
]

class SearchResult(BaseModel):
    id: str
    title: str
    type: str
    cover_url: Optional[str] = None
    chapters: Optional[int] = None
    episodes: Optional[int] = None

@router.get("/", response_model=List[Source])
async def list_sources(current_user: User = Depends(get_current_user)):
    return SOURCES

@router.get("/search", response_model=List[SearchResult])
async def search(q: str, type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    # mock results
    items = [
        SearchResult(id="1", title=f"{q} One", type=type or "manga"),
        SearchResult(id="2", title=f"{q} Two", type=type or "anime"),
    ]
    return items


@router.get("/autocomplete", response_model=List[SearchResult])
async def autocomplete(q: str, type: Optional[str] = "manga", current_user: User = Depends(get_current_user)):
    media_type = "manga" if type not in ("anime", "manga") else type
    results = await search_titles(query_text=q, media_type=media_type, per_page=8)
    out: List[SearchResult] = []
    for r in results:
        out.append(
            SearchResult(
                id=r["id"],
                title=r["title"],
                type=r["type"],
                cover_url=r.get("cover_url"),
                chapters=r.get("chapters"),
                episodes=r.get("episodes"),
            )
        )
    return out


@router.get("/max")
async def get_max(q: str, type: Optional[str] = "manga", current_user: User = Depends(get_current_user)):
    media_type = "manga" if type not in ("anime", "manga") else type
    results = await search_titles(query_text=q, media_type=media_type, per_page=1)
    if not results:
        return {"max": None}
    r = results[0]
    max_val = r.get("episodes") if media_type == "anime" else r.get("chapters")
    return {"max": max_val}
