"""
앱 설정 관리 모듈
- 환경변수를 pydantic Settings로 타입 안전하게 관리
- 사용처: main.py, database.py, security.py 등 전체 앱
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """환경변수 기반 앱 설정"""

    # --- Supabase ---
    database_url: str = ""
    supabase_service_role_key: str = ""
    supabase_url: str = ""         # Supabase 프로젝트 URL
    supabase_anon_key: str = ""    # Supabase 공개 키 (anon)

    # --- Redis ---
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # --- 보안 ---
    encryption_key: str = ""  # AES-256 마스터 키 (거래소 API 키 암호화용)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 15

    # --- 바이낸스 ---
    binance_api_key: str = ""
    binance_secret_key: str = ""

    # --- 알림 ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # --- 트레이딩 ---
    trading_mode: str = "paper"  # "paper" | "live"

    # --- 서버 ---
    backend_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 — 앱 전체에서 하나의 인스턴스만 사용"""
    return Settings()
