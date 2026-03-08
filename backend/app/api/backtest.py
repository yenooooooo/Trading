"""
백테스트 API 엔드포인트
- 백테스트 실행, 결과 조회, 파라미터 최적화
- 사용처: 백테스트 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter()


@router.post("")
async def run_backtest():
    """백테스트 실행 (비동기)"""
    return success_response({"message": "백테스트 실행 (구현 예정)"})


@router.get("/{backtest_id}")
async def get_backtest_result(backtest_id: str):
    """백테스트 결과 조회"""
    return success_response({"message": f"백테스트 {backtest_id} 결과 (구현 예정)"})


@router.get("/{backtest_id}/trades")
async def get_backtest_trades(backtest_id: str):
    """백테스트 거래 내역"""
    return success_response({"message": f"백테스트 {backtest_id} 거래 (구현 예정)"})


@router.post("/{backtest_id}/optimize")
async def optimize_params(backtest_id: str):
    """파라미터 최적화 실행"""
    return success_response({"message": f"백테스트 {backtest_id} 최적화 (구현 예정)"})
