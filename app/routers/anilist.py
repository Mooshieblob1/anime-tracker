from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from ..config import settings
from ..services.anilist_oauth import get_authorize_url, exchange_code_for_token, fetch_user_lists
from ..db import get_session
from sqlmodel import Session, select
from ..models import LibraryItem
from .auth import get_current_user, User
from jose import jwt, JWTError
from datetime import datetime, timezone, timedelta
from typing import cast
from pydantic import BaseModel
import httpx


router = APIRouter()

# In-memory token store per username (MVP). In production, persist encrypted.
_anilist_tokens: Dict[str, Dict[str, Any]] = {}


def _make_state(username: str) -> str:
    payload: Dict[str, Any] = {
    "sub": username,
        "purpose": "anilist_oauth",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode({**payload, "exp": payload["exp"]}, settings.secret_key, algorithm=settings.algorithm)


def _parse_state(state: str) -> str:
    try:
        data = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
        if data.get("purpose") != "anilist_oauth":
            raise HTTPException(status_code=400, detail="Invalid state")
        username = cast(str, data.get("sub"))
        if not username:
            raise HTTPException(status_code=400, detail="Invalid state")
        return username
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid state")


@router.get("/connect-url")
async def connect_url(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    state = _make_state(current_user.username)
    url = get_authorize_url(state)
    return {"url": url}


@router.get("/callback")
async def anilist_callback(code: str | None = None, state: str | None = None):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    username = _parse_state(state)
    try:
        token = await exchange_code_for_token(code)
        _anilist_tokens[username] = token
        # Return a tiny HTML to close popup and notify opener
        html = """
        <html><body><script>
        (function(){
            if (window.opener) {
                window.opener.postMessage({ type: 'anilist_connected' }, '*');
            }
            window.close();
        })();
        </script>
        Connection successful. You can close this window.
        </body></html>
        """
        return HTMLResponse(content=html)
    except httpx.HTTPStatusError as e:
        err_text = e.response.text
        html = f"""
        <html><body><script>
        (function(){{{{
            if (window.opener) {{{{
                window.opener.postMessage({{{{ type: 'anilist_error', message: {err_text!r} }}}}, '*');
            }}}}
        }}}})();
        </script>
        <pre>{err_text}</pre>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=e.response.status_code)


@router.get("/status")
async def anilist_status(current_user: User = Depends(get_current_user)) -> Dict[str, bool]:
    return {"connected": current_user.username in _anilist_tokens}


@router.get("/debug-config")
async def anilist_debug_config(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    # Do not expose secrets; only show whether values are set and what redirect is
    return {
        "client_id": settings.anilist_client_id,
        "client_secret_set": bool(settings.anilist_client_secret),
        "redirect_uri": settings.anilist_redirect_uri,
    }


class ImportRequest(BaseModel):
    media_type: str = "ANIME"  # ANIME or MANGA


@router.post("/import")
async def import_anilist(
    req: ImportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Dict[str, int]:
    token = _anilist_tokens.get(current_user.username)
    if not token:
        raise HTTPException(status_code=400, detail="AniList not connected")
    access_token: Optional[str] = token.get("access_token")  # type: ignore[assignment]
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access token")

    try:
        lists = await fetch_user_lists(access_token, media_type=req.media_type)
    except httpx.HTTPStatusError as e:
        # Surface upstream HTTP body for easier debugging
        raise HTTPException(status_code=e.response.status_code, detail=f"AniList request failed: {e.response.text}")
    except RuntimeError as e:
        # GraphQL-level error bubbled from service
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AniList error: {e}")

    # Ensure DB user exists (auto-provision demo)
    from .library import get_or_create_db_user
    db_user = get_or_create_db_user(session, current_user.username)
    assert db_user.id is not None

    imported = 0
    for lst in lists:
        for entry in lst.get("entries", []):
            media = entry.get("media", {})
            title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji") or media.get("title", {}).get("native") or "Untitled"
            cover_any: Any = media.get("coverImage") or {}
            if isinstance(cover_any, dict):
                cover = cast(Dict[str, Any], cover_any)
            else:
                cover = {}
            cover_url: Optional[str] = cast(Optional[str], cover.get("large") or cover.get("medium"))
            status = entry.get("status") or "planning"
            progress = entry.get("progress") or 0
            mtype = (media.get("type") or "ANIME").lower()

            # Avoid duplicates: check by title+type+source
            existing = session.exec(
                select(LibraryItem).where(
                    (LibraryItem.user_id == db_user.id) &
                    (LibraryItem.title == title) &
                    (LibraryItem.type == mtype) &
                    (LibraryItem.source == "anilist")
                )
            ).first()
            if existing:
                continue

            rec = LibraryItem(
                user_id=db_user.id,
                title=title,
                type=mtype,
                source="anilist",
                cover_url=cover_url,
                status=status.lower(),
                progress=progress,
            )
            session.add(rec)
            imported += 1

    session.commit()
    return {"imported": imported}
