from __future__ import annotations
from typing import List, Literal, Dict, Any
import httpx

ANILIST_URL = "https://graphql.anilist.co"

Suggestion = Dict[str, Any]


async def fetch_suggestions(media_type: Literal["anime", "manga"] = "anime", per_page: int = 10) -> List[Suggestion]:
    query = (
        "query ($type: MediaType, $perPage: Int) {\n"
        "  Page(perPage: $perPage) {\n"
        "    media(type: $type, sort: TRENDING_DESC) {\n"
        "      id\n"
        "      type\n"
        "      title { romaji english native }\n"
        "      coverImage { large }\n"
        "    }\n"
        "  }\n"
        "}"
    )
    variables: Dict[str, Any] = {
        "type": "ANIME" if media_type == "anime" else "MANGA",
        "perPage": max(1, min(per_page, 20)),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(ANILIST_URL, json={"query": query, "variables": variables})
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("Page", {}).get("media", [])
            results: List[Suggestion] = []
            for m in items:
                title_obj: Dict[str, Any] = m.get("title") or {}
                title = (
                    title_obj.get("romaji")
                    or title_obj.get("english")
                    or title_obj.get("native")
                    or "Untitled"
                )
                cover_obj: Dict[str, Any] = m.get("coverImage") or {}
                results.append(
                    {
                        "id": str(m.get("id")),
                        "title": title,
                        "type": media_type,
                        "cover_url": cover_obj.get("large"),
                    }
                )
            return results
    except Exception:
        # Graceful fallback
        return [{"id": "0", "title": f"Trending {media_type.title()} #1", "type": media_type, "cover_url": None}]


async def search_titles(query_text: str, media_type: Literal["anime", "manga"] = "manga", per_page: int = 8) -> List[Dict[str, Any]]:
    if not query_text or len(query_text.strip()) < 2:
        return []
    gql = (
        "query ($search: String, $type: MediaType, $perPage: Int) {\n"
        "  Page(perPage: $perPage) {\n"
        "    media(search: $search, type: $type, sort: POPULARITY_DESC) {\n"
        "      id\n"
        "      type\n"
        "      title { romaji english native }\n"
        "      coverImage { medium large }\n"
        "      chapters\n"
        "      episodes\n"
        "    }\n"
        "  }\n"
        "}"
    )
    variables: Dict[str, Any] = {
        "search": query_text,
        "type": "ANIME" if media_type == "anime" else "MANGA",
        "perPage": max(1, min(per_page, 20)),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0, headers={"Accept": "application/json", "User-Agent": "anime-tracker/0.1"}) as client:
            resp = await client.post(ANILIST_URL, json={"query": gql, "variables": variables})
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("Page", {}).get("media", [])
            out: List[Dict[str, Any]] = []
            for m in items:
                title_obj: Dict[str, Any] = m.get("title") or {}
                title = (
                    title_obj.get("english")
                    or title_obj.get("romaji")
                    or title_obj.get("native")
                    or "Untitled"
                )
                cover: Dict[str, Any] = m.get("coverImage") or {}
                out.append({
                    "id": str(m.get("id")),
                    "title": title,
                    "type": media_type,
                    "cover_url": cover.get("medium") or cover.get("large"),
                    "chapters": m.get("chapters"),
                    "episodes": m.get("episodes"),
                })
            return out
    except Exception:
        # Fallback: simple echo to ensure UI isn't empty
        return [{"id": "0", "title": query_text, "type": media_type, "cover_url": None, "chapters": None, "episodes": None}]
