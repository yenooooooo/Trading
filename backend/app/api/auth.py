"""
인증 API 엔드포인트
- Supabase Auth로 회원가입/로그인/토큰갱신
- 로그인 시 users 테이블에 자동 동기화
- 사용처: 프론트엔드 인증 플로우
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    AuthResponse,
    AuthTokens,
    UserProfile,
)
from app.schemas.common import success_response, error_response
from app.services.auth.supabase_auth import SupabaseAuthService

router = APIRouter()
auth_service = SupabaseAuthService()


# --- 회원가입 ---

@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Supabase로 회원가입 → users 테이블에 저장"""
    try:
        data = await auth_service.sign_up(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Supabase 응답에서 사용자 정보 추출
    # 이메일 확인 활성화 시: {"id": ..., "email": ...} (토큰 없음)
    # 이메일 확인 비활성화 시: {"user": {"id": ...}, "access_token": ...}
    su_user = data.get("user", data)  # 최상위 또는 user 키
    user_id = su_user.get("id")

    if not user_id:
        raise HTTPException(status_code=400, detail="회원가입 실패: 사용자 ID 없음")

    # users 테이블에 동기화
    user = User(
        id=UUID(user_id),
        email=body.email,
        nickname=body.nickname,
    )
    db.add(user)
    await db.commit()

    # 토큰이 있으면 반환 (이메일 확인 필요 시 토큰 없음)
    access_token = data.get("access_token")
    if access_token:
        return success_response(
            AuthResponse(
                user=UserProfile(id=user_id, email=body.email, nickname=body.nickname),
                tokens=AuthTokens(
                    access_token=access_token,
                    refresh_token=data.get("refresh_token", ""),
                    expires_in=data.get("expires_in", 3600),
                ),
            ).model_dump()
        )

    return success_response({"message": "이메일 확인 후 로그인해주세요"})


# --- 로그인 ---

@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Supabase로 로그인 → users 테이블 동기화"""
    try:
        data = await auth_service.sign_in(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    su_user = data.get("user", {})
    user_id = su_user.get("id")

    # users 테이블에 없으면 자동 생성 (첫 로그인)
    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=UUID(user_id), email=body.email)
        db.add(user)
        await db.commit()

    return success_response(
        AuthResponse(
            user=UserProfile(
                id=user_id, email=user.email, nickname=user.nickname
            ),
            tokens=AuthTokens(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_in=data.get("expires_in", 3600),
            ),
        ).model_dump()
    )


# --- 토큰 갱신 ---

@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """리프레시 토큰으로 새 액세스 토큰 발급"""
    try:
        data = await auth_service.refresh_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return success_response(
        AuthTokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        ).model_dump()
    )


# --- 내 정보 조회 ---

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """현재 로그인된 사용자 정보 조회"""
    return success_response(
        UserProfile(
            id=str(user.id),
            email=user.email,
            nickname=user.nickname,
        ).model_dump()
    )
