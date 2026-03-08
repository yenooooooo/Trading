"""
데이터베이스 연결 & 세션 관리
- Supabase PostgreSQL에 비동기 연결
- 사용처: dependencies.py에서 의존성 주입으로 사용
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


# --- DB 엔진 생성 ---
settings = get_settings()

# DB URL이 없으면 엔진/세션을 None으로 (DB 없이도 서버 실행 가능)
engine = None
async_session = None

if settings.database_url:
    # Supabase PostgreSQL URL을 asyncpg용으로 변환
    async_database_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(
        async_database_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
    )

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# --- ORM Base 클래스 ---
class Base(DeclarativeBase):
    """모든 ORM 모델의 부모 클래스"""
    pass


# --- 세션 생성 함수 (의존성 주입용) ---
async def get_db() -> AsyncSession:
    """요청마다 DB 세션을 생성하고 자동 정리"""
    if async_session is None:
        raise RuntimeError("DATABASE_URL이 설정되지 않았습니다")
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
