# --- 트레이딩 봇 백엔드 Docker 이미지 ---
# 용도: AWS EC2 배포
# 두 프로세스 실행:
#   1. FastAPI 서버 (API + WebSocket)
#   2. 모의매매 트레이딩 루프 (paper trading)

FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 + supervisor 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 로그 디렉토리
RUN mkdir -p /app/logs

# supervisor 설정 복사
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 포트 노출
EXPOSE 8000

# supervisor로 두 프로세스 동시 실행
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
