"""
Supabase Auth 서비스
- Supabase REST API로 회원가입/로그인/토큰갱신 처리
- Windows DNS 우회: ThreadedResolver 사용
- 사용처: auth API 라우터에서 호출
"""

import aiohttp
import structlog

from app.config import get_settings

logger = structlog.get_logger()


def _create_session() -> aiohttp.ClientSession:
    """Windows DNS 문제 우회용 세션 생성"""
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    return aiohttp.ClientSession(connector=connector)


class SupabaseAuthService:
    """Supabase GoTrue API 래퍼"""

    def __init__(self):
        s = get_settings()
        self.url = s.supabase_url
        self.anon_key = s.supabase_anon_key
        self.service_key = s.supabase_service_role_key

    # --- 헤더 ---

    def _headers(self, use_service_key: bool = False) -> dict:
        """Supabase API 요청 헤더"""
        key = self.service_key if use_service_key else self.anon_key
        return {
            "apikey": key,
            "Content-Type": "application/json",
        }

    # --- 회원가입 ---

    async def sign_up(self, email: str, password: str) -> dict:
        """이메일 회원가입 → 토큰 + 사용자 정보 반환"""
        url = f"{self.url}/auth/v1/signup"
        payload = {"email": email, "password": password}

        async with _create_session() as session:
            async with session.post(
                url, json=payload, headers=self._headers()
            ) as resp:
                data = await resp.json()

                if resp.status != 200:
                    error_msg = data.get("error_description") or data.get("msg", "회원가입 실패")
                    logger.error("supabase_signup_failed", error=error_msg)
                    raise ValueError(error_msg)

                return data

    # --- 로그인 ---

    async def sign_in(self, email: str, password: str) -> dict:
        """이메일 로그인 → 토큰 + 사용자 정보 반환"""
        url = f"{self.url}/auth/v1/token?grant_type=password"
        payload = {"email": email, "password": password}

        async with _create_session() as session:
            async with session.post(
                url, json=payload, headers=self._headers()
            ) as resp:
                data = await resp.json()

                if resp.status != 200:
                    error_msg = data.get("error_description") or data.get("msg", "로그인 실패")
                    logger.error("supabase_signin_failed", error=error_msg)
                    raise ValueError(error_msg)

                return data

    # --- 토큰 갱신 ---

    async def refresh_token(self, refresh_token: str) -> dict:
        """리프레시 토큰으로 새 액세스 토큰 발급"""
        url = f"{self.url}/auth/v1/token?grant_type=refresh_token"
        payload = {"refresh_token": refresh_token}

        async with _create_session() as session:
            async with session.post(
                url, json=payload, headers=self._headers()
            ) as resp:
                data = await resp.json()

                if resp.status != 200:
                    error_msg = data.get("error_description") or data.get("msg", "토큰 갱신 실패")
                    logger.error("supabase_refresh_failed", error=error_msg)
                    raise ValueError(error_msg)

                return data

    # --- 사용자 정보 조회 (서비스 키 사용) ---

    async def get_user(self, user_id: str) -> dict | None:
        """관리자 권한으로 사용자 정보 조회"""
        url = f"{self.url}/auth/v1/admin/users/{user_id}"

        async with _create_session() as session:
            async with session.get(
                url, headers=self._headers(use_service_key=True)
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
