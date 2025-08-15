from __future__ import annotations
from typing import Any, Dict, List, cast
import httpx

from ..config import settings


OAUTH_AUTHORIZE_URL = "https://anilist.co/api/v2/oauth/authorize"
OAUTH_TOKEN_URL = "https://anilist.co/api/v2/oauth/token"
GRAPHQL_URL = "https://graphql.anilist.co"


def get_authorize_url(state: str) -> str:
  from urllib.parse import urlencode

  params = {
    "client_id": settings.anilist_client_id,
    "redirect_uri": settings.anilist_redirect_uri,
    "response_type": "code",
  }
  # state is appended to help CSRF protection; caller stores it in session/frontend
  return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}&state={state}"


async def exchange_code_for_token(code: str) -> Dict[str, Any]:
  async with httpx.AsyncClient(timeout=15) as client:
    # Per AniList docs: JSON body
    json_body: Dict[str, Any] = {
      "grant_type": "authorization_code",
      "client_id": settings.anilist_client_id,
      "client_secret": settings.anilist_client_secret,
      "redirect_uri": settings.anilist_redirect_uri,
      "code": code,
    }
    resp = await client.post(OAUTH_TOKEN_URL, json=json_body)
    if resp.status_code == 200:
      return cast(Dict[str, Any], resp.json())
    # Fallback: form-encoded
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp2 = await client.post(OAUTH_TOKEN_URL, data=json_body, headers=headers)
    resp2.raise_for_status()
    return cast(Dict[str, Any], resp2.json())


async def fetch_user_lists(access_token: str, media_type: str = "ANIME") -> List[Dict[str, Any]]:
  # Fetch user's lists (collection) for ANIME or MANGA
  query = """
  query ($type: MediaType) {
    Viewer { id name }
    MediaListCollection(type: $type) {
    lists {
      name
      entries {
      status
      progress
      score
      media {
        id
        title { romaji english native }
        type
        coverImage { large medium }
        siteUrl
      }
      }
    }
    }
  }
  """
  variables: Dict[str, Any] = {"type": media_type}
  headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": settings.anilist_app_name or "anime-tracker/0.1",
  }
  async with httpx.AsyncClient(timeout=20) as client:
    resp = await client.post(
      GRAPHQL_URL,
      json={"query": query, "variables": variables},
      headers=headers,
    )
    resp.raise_for_status()
    raw: Any = resp.json()

  # If AniList returns GraphQL errors with 200 OK
  if isinstance(raw, dict):
    data_dict: Dict[str, Any] = cast(Dict[str, Any], raw)
    errs_list: List[Dict[str, Any]] = cast(List[Dict[str, Any]], data_dict.get("errors") or [])
    if errs_list:
      # Bubble up a concise message; caller will map to HTTP error
      messages: List[str] = []
      for err in errs_list:
        msg: Any = err.get("message")
        messages.append(str(msg))
      raise RuntimeError(f"AniList GraphQL error: {'; '.join(messages)}")
    data_dict2: Dict[str, Any] = cast(Dict[str, Any], data_dict.get("data") or {})
    mlc_dict: Dict[str, Any] = cast(Dict[str, Any], data_dict2.get("MediaListCollection") or {})
    lists_list: List[Dict[str, Any]] = cast(List[Dict[str, Any]], mlc_dict.get("lists") or [])
    return lists_list

  # Unexpected shape
  return []
