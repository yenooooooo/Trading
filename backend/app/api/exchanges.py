"""
거래소 연동 API 엔드포인트
- 거래소 API 키 등록/삭제, 잔고 조회, 연결 상태 확인
- 사용처: 설정 > 거래소 API 키 관리 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter()


@router.get("")
async def list_exchanges():
    """지원 거래소 목록 조회"""
    return success_response({
        "exchanges": [
            {"id": "binance", "name": "Binance Futures", "status": "supported"},
            {"id": "bybit", "name": "Bybit", "status": "planned"},
            {"id": "okx", "name": "OKX", "status": "planned"},
        ]
    })


@router.post("/connect")
async def connect_exchange():
    """거래소 API 키 등록 (암호화 저장)"""
    return success_response({"message": "거래소 연동 엔드포인트 (구현 예정)"})


@router.delete("/{exchange_id}")
async def disconnect_exchange(exchange_id: str):
    """거래소 API 키 삭제"""
    return success_response({"message": f"{exchange_id} 연동 해제 (구현 예정)"})


@router.get("/{exchange_id}/balance")
async def get_balance(exchange_id: str):
    """잔고 조회"""
    return success_response({"message": f"{exchange_id} 잔고 조회 (구현 예정)"})


@router.get("/{exchange_id}/status")
async def get_status(exchange_id: str):
    """연결 상태 확인"""
    return success_response({"message": f"{exchange_id} 상태 확인 (구현 예정)"})
