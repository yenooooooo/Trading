"""
커스텀 예외 클래스 모음
- 모든 에러를 분류하여 API 응답에서 일관된 에러 메시지 제공
- 사용처: 전체 앱에서 raise로 호출
"""


class AppException(Exception):
    """앱 기본 예외 — 모든 커스텀 예외의 부모"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(AppException):
    """인증 실패 (잘못된 토큰, 만료 등)"""

    def __init__(self, message: str = "인증에 실패했습니다"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppException):
    """권한 없음 (접근 금지)"""

    def __init__(self, message: str = "접근 권한이 없습니다"):
        super().__init__(message, status_code=403)


class NotFoundError(AppException):
    """리소스를 찾을 수 없음"""

    def __init__(self, resource: str = "리소스"):
        super().__init__(f"{resource}를 찾을 수 없습니다", status_code=404)


class ValidationError(AppException):
    """입력값 검증 실패"""

    def __init__(self, message: str = "입력값이 올바르지 않습니다"):
        super().__init__(message, status_code=422)


class ExchangeError(AppException):
    """거래소 API 관련 에러"""

    def __init__(self, message: str = "거래소 API 오류가 발생했습니다"):
        super().__init__(message, status_code=502)


class RiskLimitError(AppException):
    """리스크 한도 초과 — 주문 거부"""

    def __init__(self, message: str = "리스크 한도를 초과했습니다"):
        super().__init__(message, status_code=400)


class InsufficientBalanceError(AppException):
    """잔고 부족"""

    def __init__(self, message: str = "잔고가 부족합니다"):
        super().__init__(message, status_code=400)
