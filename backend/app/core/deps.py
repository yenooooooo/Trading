"""
FastAPI 의존성 주입
- Supabase JWT 토큰 검증 (ES256 / JWKS)
- 현재 사용자 추출
- 사용처: 인증 필요한 모든 API 엔드포인트
"""

from uuid import UUID

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.services.exchange.binance import BinanceFuturesConnector

# Bearer 토큰 스키마
bearer_scheme = HTTPBearer()

# Supabase JWKS 클라이언트 (공개키 자동 캐싱)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Supabase JWKS 엔드포인트에서 공개키 가져오기"""
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Supabase JWT 토큰을 검증하고 현재 사용자 반환

    흐름:
    1. Authorization 헤더에서 Bearer 토큰 추출
    2. Supabase JWKS 공개키로 ES256 토큰 검증
    3. sub(사용자 ID)로 DB에서 User 조회
    """
    token = credentials.credentials

    # --- JWT 디코딩 (JWKS 공개키로 검증) ---
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
        )

    # --- 사용자 ID 추출 ---
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 사용자 정보가 없습니다",
        )

    # --- DB에서 사용자 조회 ---
    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="등록되지 않은 사용자입니다",
        )

    return user


# --- 거래소 커넥터 싱글톤 ---

_connector: BinanceFuturesConnector | None = None


async def get_connector() -> BinanceFuturesConnector:
    """바이낸스 커넥터 싱글톤 (연결 유지)"""
    global _connector
    if _connector is None or _connector.exchange is None:
        settings = get_settings()
        _connector = BinanceFuturesConnector(
            api_key=settings.binance_api_key,
            secret_key=settings.binance_secret_key,
        )
        await _connector.connect()
    return _connector
