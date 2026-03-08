# 코인 선물 자동매매 웹사이트 — Claude 개발 운영 지침서

---

## 1. Claude의 핵심 개발 원칙

### 1.1 코드 품질 원칙
- 모든 코드는 **프로덕션 레벨**로 작성 (타입, 에러 핸들링, 로깅 포함)
- 모든 금액 계산은 **Decimal 타입** 사용 (float 절대 금지)
- 시간은 항상 **UTC 기준**, 표시할 때만 로컬 변환
- 주석은 **한국어**로, **"왜(Why)"** 위주로 작성
- 기술 용어는 **영문 병기** (예: 최대 낙폭(Maximum Drawdown))

### 1.2 리스크 관리 원칙 (최우선)
- 모든 주문은 반드시 **RiskManager**를 통과
- 손절(Stop Loss) 없는 포지션 진입 **절대 금지**
- 최대 레버리지 **20x 하드 리밋** (권장 3~10x)
- 단일 거래에 총 자산의 **50% 이상 투입 금지**
- 백테스트 없는 전략 실전 배포 **금지**

### 1.3 보안 원칙
- API 키는 **AES-256-GCM 암호화** 저장
- 출금(Withdraw) 권한 API 키 **사용 금지**
- API Secret을 프론트엔드에 **절대 노출 금지**
- .env 파일 Git 커밋 **절대 금지**
- 로그에 민감 정보(API 키, 비밀번호) **출력 금지**

---

## 2. 파일 크기 및 구조 관리 규칙

### 2.1 파일 줄 수 제한

| 파일 유형 | 최대 줄 수 | 초과 시 조치 |
|-----------|-----------|-------------|
| React 컴포넌트 (.tsx) | **150줄** | 하위 컴포넌트로 분리 |
| 커스텀 훅 (.ts) | **100줄** | 기능별 훅으로 분리 |
| API 라우트 / 엔드포인트 | **100줄** | 서비스 레이어로 로직 분리 |
| Python 모듈 (.py) | **200줄** | 클래스/함수 단위로 파일 분리 |
| 유틸리티 함수 | **80줄** | 카테고리별 파일 분리 |
| 타입/인터페이스 정의 | **100줄** | 도메인별 파일 분리 |
| 설정 파일 | **50줄** | 환경별 분리 |
| 테스트 파일 | **200줄** | describe 블록별 파일 분리 |

### 2.2 파일 분리 기준
```
파일이 제한 줄 수의 80%에 도달하면:
1. 기능별 섹션을 식별
2. 각 섹션에 상세 주석 블록 추가
3. 독립적인 기능은 새 파일로 분리
4. index.ts 또는 __init__.py로 re-export 관리
```

### 2.3 주석 규칙
```
모든 파일 상단:
  - 파일 목적 설명 (1~2줄)
  - 주요 export 목록
  - 의존성 관계 (어떤 모듈에서 사용되는지)

함수/클래스 단위:
  - 기능 설명 (무엇을 하는지)
  - 파라미터 설명 (복잡한 경우)
  - 반환값 설명
  - 주의사항 (있는 경우)

복잡한 로직 블록:
  - // --- [기능명] 시작 --- 형태의 섹션 구분 주석
  - 왜 이런 방식을 선택했는지 설명
  - // --- [기능명] 끝 --- 으로 섹션 종료
```

---

## 3. 프로젝트 디렉토리 구조

### 3.1 프론트엔드 (Next.js 14+ App Router)
```
crypto-trader/
├── src/
│   ├── app/                          # Next.js App Router 페이지
│   │   ├── layout.tsx                # 루트 레이아웃
│   │   ├── page.tsx                  # 랜딩 페이지
│   │   └── dashboard/
│   │       ├── layout.tsx            # 대시보드 공통 레이아웃 (사이드바, 헤더)
│   │       ├── page.tsx              # 메인 대시보드
│   │       ├── trading/
│   │       │   └── page.tsx          # 실시간 트레이딩 뷰
│   │       ├── strategies/
│   │       │   ├── page.tsx          # 전략 목록
│   │       │   ├── new/
│   │       │   │   └── page.tsx      # 새 전략 생성
│   │       │   └── [id]/
│   │       │       └── page.tsx      # 전략 상세/설정
│   │       ├── backtest/
│   │       │   ├── page.tsx          # 백테스트 실행
│   │       │   └── [id]/
│   │       │       └── page.tsx      # 백테스트 결과 상세
│   │       ├── positions/
│   │       │   └── page.tsx          # 포지션 & 주문 관리
│   │       ├── history/
│   │       │   └── page.tsx          # 거래 내역 & 성과 분석
│   │       ├── risk/
│   │       │   └── page.tsx          # 리스크 대시보드
│   │       └── settings/
│   │           ├── page.tsx          # 일반 설정
│   │           ├── api/
│   │           │   └── page.tsx      # 거래소 API 키 관리
│   │           └── alerts/
│   │               └── page.tsx      # 알림 설정
│   │
│   ├── components/                   # 재사용 컴포넌트
│   │   ├── ui/                       # shadcn/ui 기본 컴포넌트
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   ├── layout/                   # 레이아웃 컴포넌트
│   │   │   ├── Sidebar.tsx           # 사이드바 내비게이션
│   │   │   ├── Header.tsx            # 상단 헤더
│   │   │   └── Footer.tsx
│   │   ├── dashboard/                # 대시보드 전용 컴포넌트
│   │   │   ├── StatCard.tsx          # 통계 카드 (총자산, PnL 등)
│   │   │   ├── EquityCurve.tsx       # 자산 곡선 차트
│   │   │   ├── PositionSummary.tsx   # 포지션 요약 테이블
│   │   │   ├── RiskGauge.tsx         # 리스크 게이지
│   │   │   └── RecentTrades.tsx      # 최근 거래 내역
│   │   ├── trading/                  # 트레이딩 뷰 컴포넌트
│   │   │   ├── CandleChart.tsx       # TradingView 캔들차트
│   │   │   ├── OrderBook.tsx         # 오더북
│   │   │   ├── OrderPanel.tsx        # 주문 패널
│   │   │   ├── PositionList.tsx      # 활성 포지션 목록
│   │   │   └── TradeHistory.tsx      # 체결 내역
│   │   ├── strategy/                 # 전략 관련 컴포넌트
│   │   │   ├── StrategyCard.tsx      # 전략 카드
│   │   │   ├── StrategyForm.tsx      # 전략 파라미터 폼
│   │   │   ├── ParameterSlider.tsx   # 파라미터 슬라이더
│   │   │   └── StrategyStatus.tsx    # 전략 상태 배지
│   │   ├── backtest/                 # 백테스트 컴포넌트
│   │   │   ├── BacktestForm.tsx      # 백테스트 설정 폼
│   │   │   ├── ResultSummary.tsx     # 결과 요약 카드
│   │   │   ├── MonthlyHeatmap.tsx    # 월별 수익률 히트맵
│   │   │   ├── DrawdownChart.tsx     # 드로다운 차트
│   │   │   └── TradeTable.tsx        # 거래 목록 테이블
│   │   └── risk/                     # 리스크 컴포넌트
│   │       ├── RiskMetricCard.tsx    # 리스크 메트릭 카드
│   │       ├── ExposureChart.tsx     # 노출도 차트
│   │       └── CorrelationMap.tsx    # 상관관계 히트맵
│   │
│   ├── hooks/                        # 커스텀 훅
│   │   ├── useWebSocket.ts           # WebSocket 연결 관리
│   │   ├── useTickerStream.ts        # 실시간 시세 구독
│   │   ├── useOrderBook.ts           # 오더북 데이터 구독
│   │   ├── usePositions.ts           # 포지션 데이터 (React Query)
│   │   ├── useStrategies.ts          # 전략 데이터 (React Query)
│   │   ├── useBacktest.ts            # 백테스트 실행/결과
│   │   ├── useRiskMetrics.ts         # 리스크 메트릭 실시간
│   │   └── useAuth.ts               # 인증 상태 관리
│   │
│   ├── lib/                          # 유틸리티 & 설정
│   │   ├── api.ts                    # API 클라이언트 (axios/fetch 래퍼)
│   │   ├── ws.ts                     # WebSocket 클라이언트 클래스
│   │   ├── constants.ts              # 상수 정의
│   │   ├── utils/
│   │   │   ├── format.ts            # 숫자/날짜/가격 포맷
│   │   │   ├── decimal.ts           # Decimal 연산 유틸
│   │   │   └── validation.ts        # 입력값 검증 유틸
│   │   └── config.ts                # 환경 설정
│   │
│   ├── types/                        # TypeScript 타입 정의
│   │   ├── market.ts                 # 시장 데이터 타입 (Ticker, OHLCV, OrderBook)
│   │   ├── trading.ts                # 트레이딩 타입 (Order, Position, Trade)
│   │   ├── strategy.ts               # 전략 타입 (Strategy, Signal, Config)
│   │   ├── risk.ts                   # 리스크 타입 (RiskMetric, RiskCheck)
│   │   ├── backtest.ts               # 백테스트 타입 (BacktestResult, TradeRecord)
│   │   ├── api.ts                    # API 응답 타입 (ApiResponse, Pagination)
│   │   └── ws.ts                     # WebSocket 이벤트 타입
│   │
│   └── stores/                       # Zustand 스토어
│       ├── useTradeStore.ts          # 트레이딩 상태 (선택 심볼, 타임프레임)
│       ├── useSettingsStore.ts       # 사용자 설정 (테마, 알림)
│       └── useNotificationStore.ts   # 알림/토스트 상태
│
├── public/                           # 정적 파일
├── tailwind.config.ts
├── next.config.ts
├── tsconfig.json
├── package.json
└── .env.local                        # 환경변수 (Git 제외)
```

### 3.2 백엔드 (Python FastAPI)
```
backend/
├── app/
│   ├── main.py                       # FastAPI 앱 진입점 + 미들웨어 설정
│   ├── config.py                     # pydantic Settings (환경변수 관리)
│   ├── dependencies.py               # 의존성 주입 (DB 세션, 인증 등)
│   │
│   ├── api/                          # API 라우터
│   │   ├── __init__.py
│   │   ├── auth.py                   # 인증 엔드포인트
│   │   ├── exchanges.py              # 거래소 연동 엔드포인트
│   │   ├── strategies.py             # 전략 CRUD + 시작/중지
│   │   ├── backtest.py               # 백테스트 실행/결과
│   │   ├── positions.py              # 포지션 & 주문
│   │   ├── trades.py                 # 거래 내역 & 통계
│   │   ├── risk.py                   # 리스크 상태/설정
│   │   ├── market.py                 # 시장 데이터 조회
│   │   └── alerts.py                 # 알림 설정
│   │
│   ├── models/                       # SQLAlchemy ORM 모델
│   │   ├── __init__.py
│   │   ├── user.py                   # User 모델
│   │   ├── exchange_key.py           # ExchangeKey 모델
│   │   ├── strategy.py               # Strategy 모델
│   │   ├── position.py               # Position 모델
│   │   ├── order.py                  # Order 모델
│   │   ├── trade.py                  # Trade 모델
│   │   ├── backtest.py               # Backtest 모델
│   │   ├── daily_performance.py      # DailyPerformance 모델
│   │   └── alert_rule.py             # AlertRule 모델
│   │
│   ├── schemas/                      # Pydantic 스키마 (요청/응답)
│   │   ├── __init__.py
│   │   ├── common.py                 # 공통 응답 포맷 (ApiResponse)
│   │   ├── auth.py                   # 인증 스키마
│   │   ├── exchange.py               # 거래소 스키마
│   │   ├── strategy.py               # 전략 스키마
│   │   ├── position.py               # 포지션 스키마
│   │   ├── order.py                  # 주문 스키마
│   │   ├── backtest.py               # 백테스트 스키마
│   │   └── risk.py                   # 리스크 스키마
│   │
│   ├── services/                     # 비즈니스 로직 (핵심 엔진)
│   │   ├── __init__.py
│   │   ├── exchange/                 # 거래소 커넥터
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # ExchangeConnector 추상 클래스
│   │   │   ├── binance.py            # Binance Futures 커넥터
│   │   │   ├── bybit.py              # Bybit 커넥터
│   │   │   └── factory.py            # 커넥터 팩토리
│   │   ├── strategy/                 # 전략 엔진
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # BaseStrategy 추상 클래스
│   │   │   ├── dual_ma.py            # Dual MA Crossover 전략
│   │   │   ├── rsi_divergence.py     # RSI Divergence 전략
│   │   │   ├── breakout.py           # Breakout Momentum 전략
│   │   │   ├── grid.py               # Grid Trading 전략
│   │   │   ├── orchestrator.py       # 전략 실행/관리 오케스트레이터
│   │   │   └── registry.py           # 전략 레지스트리 (이름 → 클래스 매핑)
│   │   ├── risk/                     # 리스크 관리
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # RiskManager 메인 클래스
│   │   │   ├── checks.py             # 개별 리스크 체크 함수들
│   │   │   ├── metrics.py            # 리스크 메트릭 계산
│   │   │   └── circuit_breaker.py    # 서킷 브레이커 (매매 중단 로직)
│   │   ├── backtest/                 # 백테스트 엔진
│   │   │   ├── __init__.py
│   │   │   ├── engine.py             # BacktestEngine 메인
│   │   │   ├── simulator.py          # 주문 체결 시뮬레이터
│   │   │   ├── metrics.py            # 백테스트 결과 지표 계산
│   │   │   └── optimizer.py          # 파라미터 최적화
│   │   ├── trading/                  # 트레이딩 엔진
│   │   │   ├── __init__.py
│   │   │   ├── engine.py             # 주문 실행 엔진
│   │   │   ├── position_manager.py   # 포지션 관리 (TP/SL/트레일링)
│   │   │   └── order_tracker.py      # 주문 상태 추적
│   │   ├── data/                     # 데이터 파이프라인
│   │   │   ├── __init__.py
│   │   │   ├── market_data.py        # 시장 데이터 수집/저장
│   │   │   ├── websocket_manager.py  # WebSocket 스트림 관리
│   │   │   └── cache.py              # Redis 캐시 레이어
│   │   └── notification/             # 알림 시스템
│   │       ├── __init__.py
│   │       ├── manager.py            # 알림 매니저
│   │       ├── telegram.py           # 텔레그램 봇
│   │       ├── discord.py            # 디스코드 웹훅
│   │       └── templates.py          # 알림 메시지 템플릿
│   │
│   ├── core/                         # 공통 핵심 모듈
│   │   ├── __init__.py
│   │   ├── security.py               # 암호화/복호화 (AES-256-GCM)
│   │   ├── auth.py                   # JWT 토큰 관리
│   │   ├── exceptions.py             # 커스텀 예외 클래스
│   │   ├── logging.py                # 로깅 설정 (민감정보 마스킹)
│   │   └── database.py               # DB 연결 & 세션 관리
│   │
│   └── utils/                        # 유틸리티
│       ├── __init__.py
│       ├── decimal_utils.py          # Decimal 연산 헬퍼
│       ├── time_utils.py             # UTC 시간 변환 유틸
│       └── rate_limiter.py           # Rate Limit 관리
│
├── migrations/                       # Alembic 마이그레이션
│   └── versions/
├── tests/                            # 테스트
│   ├── unit/                         # 단위 테스트
│   │   ├── test_strategies/
│   │   ├── test_risk/
│   │   └── test_backtest/
│   ├── integration/                  # 통합 테스트
│   └── conftest.py                   # 테스트 픽스처
│
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env                              # 환경변수 (Git 제외)
```

### 3.3 루트 디렉토리
```
trading/                              # 프로젝트 루트
├── CLAUDE.md                         # ← 이 파일 (Claude 개발 운영 지침서)
├── crypto-autotrading-guide.md       # 원본 프로젝트 기획 지침서
├── crypto-trader/                    # 프론트엔드 (Next.js)
├── backend/                          # 백엔드 (FastAPI)
├── docker-compose.yml                # 개발 환경 (PostgreSQL + Redis)
├── .gitignore
└── .env.example                      # 환경변수 템플릿
```

---

## 4. 기술 스택 요약

| 영역 | 기술 |
|------|------|
| 프론트엔드 | Next.js 14+ (App Router), TypeScript strict |
| 상태관리 | Zustand + TanStack Query |
| UI | Tailwind CSS + shadcn/ui, 다크 모드 기본 |
| 차트 | Lightweight Charts (TradingView) + Recharts |
| 백엔드 | Python FastAPI + asyncio |
| 트레이딩 | ccxt (멀티 거래소) |
| DB | PostgreSQL (Supabase) + Redis |
| 인증 | Clerk 또는 Supabase Auth |
| 알림 | Telegram Bot + Discord Webhook |
| 배포 | Vercel (프론트) + AWS EC2 (백엔드) + Supabase (DB/Auth) |

---

## 5. 배포 & 인프라 구조 (확정)

### 5.1 배포 아키텍처
```
GitHub Repository (mono repo)
    │
    ├──→ Vercel (자동배포: git push → 자동 빌드)
    │    └─ crypto-trader/ (Next.js 프론트엔드)
    │    └─ 비용: $0 (무료)
    │
    └──→ AWS EC2 t2.micro (수동 또는 GitHub Actions 배포)
         └─ backend/ (FastAPI 트레이딩 엔진, 24/7 상시 가동)
         └─ 비용: $0 (Free Tier, 남은 11개월)
              ※ 기존 EC2 인스턴스는 Stop 처리
              ※ Elastic IP 해제 필수 (과금 방지)

Supabase (관리형 서비스)
    ├─ PostgreSQL DB (500MB 무료)
    │   └─ 전략, 주문, 포지션, 거래내역, 사용자 데이터
    ├─ Supabase Auth (50,000 MAU 무료)
    │   └─ 로그인, 회원가입, JWT, 2FA
    └─ 비용: $0 (무료)

Upstash Redis (서버리스)
    └─ 실시간 캐싱 (가격, 오더북, 세션)
    └─ 비용: $0 (무료 10,000 요청/일)
```

### 5.2 월 비용 총합: $0

| 서비스 | 용도 | 월 비용 |
|--------|------|--------|
| **Vercel** | 프론트엔드 배포 | $0 |
| **AWS EC2 t2.micro** | 백엔드 24/7 가동 | $0 (Free Tier) |
| **Supabase** | DB + Auth | $0 |
| **Upstash Redis** | 실시간 캐싱 | $0 |
| **합계** | | **$0/월** |

### 5.3 AWS Free Tier 만료 대비 (11개월 후)
- Railway ($5/월) 또는 Fly.io로 백엔드 이전
- Dockerfile 기반이므로 이전 간단

### 5.4 배포 전 AWS 체크리스트
```
□ 기존 EC2 인스턴스 Stop (삭제 아님)
□ 기존 Elastic IP 해제 (Release)
□ 새 t2.micro 인스턴스 생성 (Ubuntu 22.04)
□ 보안 그룹: 포트 8000(FastAPI), 443(HTTPS), 22(SSH) 오픈
□ EBS 합산 30GB 이내 확인
□ Python 3.11+, Docker 설치
```

---

## 6. 개발 순서 (Phase별)


### Phase 1: Foundation (기반)
1. 프로젝트 초기 셋업 (Next.js + FastAPI + Docker)
2. 데이터베이스 스키마 생성
3. 인증 시스템
4. 거래소 커넥터 v1 (Binance)
5. 기본 대시보드 레이아웃

### Phase 2: Core Trading (핵심 매매)
1. 전략 엔진 프레임워크
2. 내장 전략 2개 (Dual MA + RSI Divergence)
3. 주문 실행 엔진
4. 포지션 관리 (TP/SL/트레일링)
5. 실시간 WebSocket 파이프라인
6. TradingView 차트

### Phase 3: Backtest & Risk (백테스트 & 리스크)
1. 백테스트 엔진
2. 백테스트 시각화
3. 리스크 관리 엔진
4. 리스크 대시보드

### Phase 4: Alerts & Polish (알림 & 완성도)
1. 텔레그램/디스코드 알림
2. 추가 전략 구현
3. 거래 내역 & 성과 분석
4. 반응형 UI

### Phase 5: Advanced (고급)
1. 멀티 거래소 지원
2. 커스텀 전략 빌더
3. 고급 백테스트
4. 성능 최적화

---

## 7. 코드 작성 컨벤션

### 프론트엔드 (TypeScript)
- 컴포넌트: `PascalCase.tsx` (예: TradingChart.tsx)
- 훅: `useCamelCase.ts` (예: useWebSocket.ts)
- 유틸: `camelCase.ts` (예: formatCurrency.ts)
- 상수: `SCREAMING_SNAKE_CASE` (예: MAX_LEVERAGE)
- 타입: `PascalCase` (예: StrategyConfig)

### 백엔드 (Python)
- 모듈: `snake_case.py` (예: trading_engine.py)
- 클래스: `PascalCase` (예: RiskManager)
- 함수: `snake_case` (예: calculate_position_size)
- API: `kebab-case` (예: /api/exchange-keys)

### 공통
- API 응답: `{ success, data, error, timestamp }` 포맷
- 에러: 커스텀 에러 클래스 사용
- 로그: DEBUG / INFO / WARNING / ERROR / CRITICAL
- 환경변수로 모든 설정값 관리

---

## 8. 파일 수정 시 체크리스트

```
□ 파일 줄 수가 제한 이내인가?
□ 기능별 섹션 주석이 있는가?
□ 타입 정의가 완전한가? (TypeScript strict / Python type hints)
□ 에러 핸들링이 포함되어 있는가?
□ 금액 계산에 Decimal을 사용했는가?
□ 시간 처리가 UTC 기준인가?
□ 민감 정보가 노출되지 않는가?
□ import 경로가 올바른가?
□ 관련 테스트가 있는가?
```

---

## 9. 색상 & 디자인 상수

```
수익(Profit):  #22C55E (Green)  + ▲ 아이콘
손실(Loss):    #EF4444 (Red)    + ▼ 아이콘
중립(Neutral): #94A3B8 (Slate)
숫자 폰트:     JetBrains Mono
텍스트 폰트:   Inter
테마:          다크 모드 기본 + 라이트 모드 지원
```
## 10. 설명 및 대답
모든 설명과 대답은 한국어로 한다.