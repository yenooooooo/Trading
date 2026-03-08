"""
FastAPI 앱 진입점
- CORS, 미들웨어, 라우터 등록
- 서버 시작 시 트레이딩 엔진 자동 시작
- 사용처: uvicorn으로 실행되는 메인 앱
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, exchanges, strategies, positions, trades, risk, market, alerts, backtest, trading
from app.api import settings as settings_api

# --- 서버 시작/종료 이벤트 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 트레이딩 엔진 자동 시작"""
    # startup
    await asyncio.sleep(2)  # 커넥터 초기화 대기
    try:
        engine = trading._get_engine()
        if not engine.get_status()["running"]:
            await engine.start()
            print("[AUTO-START] 트레이딩 엔진 자동 시작 완료")
    except Exception as e:
        print(f"[AUTO-START] 엔진 자동 시작 실패: {e}")

    yield

    # shutdown
    try:
        engine = trading._get_engine()
        if engine.get_status()["running"]:
            await engine.stop()
            print("[SHUTDOWN] 트레이딩 엔진 정상 종료")
    except Exception:
        pass


# --- FastAPI 앱 생성 ---
app_settings = get_settings()

app = FastAPI(
    title="Crypto Auto-Trader API",
    description="암호화폐 선물 자동매매 시스템 백엔드",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS 설정 (프론트엔드 연동) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
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
app.include_router(settings_api.router, prefix="/api/settings", tags=["설정"])
