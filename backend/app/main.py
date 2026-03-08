"""
FastAPI 앱 진입점
- CORS, 미들웨어, 라우터 등록
- 사용처: uvicorn으로 실행되는 메인 앱
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, exchanges, strategies, positions, trades, risk, market, alerts, backtest, trading

# --- FastAPI 앱 생성 ---
settings = get_settings()

app = FastAPI(
    title="Crypto Auto-Trader API",
    description="암호화폐 선물 자동매매 시스템 백엔드",
    version="0.1.0",
)

# --- CORS 설정 (프론트엔드 연동) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 헬스 체크 ---
@app.get("/api/health")
async def health_check():
    """서버 상태 확인 엔드포인트"""
    return {
        "success": True,
        "data": {"status": "healthy", "version": "0.1.0"},
        "error": None,
    }


# --- API 라우터 등록 ---
app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
app.include_router(exchanges.router, prefix="/api/exchanges", tags=["거래소"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["전략"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["백테스트"])
app.include_router(positions.router, prefix="/api/positions", tags=["포지션"])
app.include_router(trades.router, prefix="/api/trades", tags=["거래내역"])
app.include_router(risk.router, prefix="/api/risk", tags=["리스크"])
app.include_router(market.router, prefix="/api/market", tags=["시장데이터"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["알림"])
app.include_router(trading.router, prefix="/api/trading", tags=["실시간매매"])
