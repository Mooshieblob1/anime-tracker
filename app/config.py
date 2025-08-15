from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Anime & Manga Tracker"
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./app.db"

    # AniList OAuth settings
    anilist_client_id: str = "29366"
    anilist_client_secret: str = "Ia0qEaUMlDApQwT3vP7SeNArR4wpH8aE5OQzPCAS"
    anilist_app_name: str = "Test"
    # Default redirect points to backend callback; override via .env if needed
    anilist_redirect_uri: str = "http://127.0.0.1:8000/api/anilist/callback"

    class Config:
        env_file = ".env"


settings = Settings()
