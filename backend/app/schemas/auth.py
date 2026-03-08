"""
인증 스키마
- 로그인/회원가입 요청·응답 모델
- 사용처: auth API 라우터
"""

from pydantic import BaseModel, EmailStr


# --- 요청 스키마 ---

class LoginRequest(BaseModel):
    """이메일 + 비밀번호 로그인"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """회원가입"""
    email: EmailStr
    password: str
    nickname: str | None = None


class RefreshRequest(BaseModel):
    """토큰 갱신"""
    refresh_token: str


# --- 응답 스키마 ---

class AuthTokens(BaseModel):
    """Supabase에서 받은 인증 토큰"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class UserProfile(BaseModel):
    """사용자 프로필"""
    id: str
    email: str
    nickname: str | None = None


class AuthResponse(BaseModel):
    """인증 응답 (토큰 + 프로필)"""
    user: UserProfile
    tokens: AuthTokens
