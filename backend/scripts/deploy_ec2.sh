#!/bin/bash
# ==============================================
# EC2 배포 스크립트
#
# 사용법:
#   1. EC2에 SSH 접속
#   2. 이 스크립트 실행: bash scripts/deploy_ec2.sh
#
# 최초 설치:
#   bash scripts/deploy_ec2.sh setup
#
# 업데이트 배포:
#   bash scripts/deploy_ec2.sh deploy
#
# 상태 확인:
#   bash scripts/deploy_ec2.sh status
#
# 로그 확인:
#   bash scripts/deploy_ec2.sh logs
# ==============================================

set -e

PROJECT_DIR="$HOME/trading/backend"

case "${1:-deploy}" in

  # --- 최초 설치 ---
  setup)
    echo "=== EC2 초기 설치 ==="

    # Docker 설치
    if ! command -v docker &> /dev/null; then
      echo "Docker 설치 중..."
      sudo apt-get update
      sudo apt-get install -y ca-certificates curl gnupg
      sudo install -m 0755 -d /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      sudo chmod a+r /etc/apt/keyrings/docker.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      sudo apt-get update
      sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
      sudo usermod -aG docker $USER
      echo "Docker 설치 완료. 로그아웃 후 재접속하세요."
    else
      echo "Docker 이미 설치됨: $(docker --version)"
    fi

    # 디렉토리 생성
    mkdir -p $HOME/trading/backend

    echo ""
    echo "=== 설치 완료 ==="
    echo "다음 단계:"
    echo "  1. 로컬에서 파일 전송:"
    echo "     scp -r -i KEY.pem backend/ ubuntu@EC2_IP:~/trading/backend/"
    echo "  2. EC2에서 .env 파일 생성:"
    echo "     nano $PROJECT_DIR/.env"
    echo "  3. 배포:"
    echo "     cd $PROJECT_DIR && bash scripts/deploy_ec2.sh deploy"
    ;;

  # --- 배포 (빌드 + 시작) ---
  deploy)
    echo "=== 배포 시작 ==="
    cd $PROJECT_DIR

    # 기존 컨테이너 중지 (삭제 아님)
    echo "기존 컨테이너 중지..."
    docker compose -f docker-compose.prod.yml down 2>/dev/null || true

    # 빌드 + 시작
    echo "빌드 + 시작..."
    docker compose -f docker-compose.prod.yml up -d --build

    echo ""
    echo "=== 배포 완료 ==="
    docker compose -f docker-compose.prod.yml ps
    ;;

  # --- 중지 ---
  stop)
    echo "=== 컨테이너 중지 ==="
    cd $PROJECT_DIR
    docker compose -f docker-compose.prod.yml stop
    echo "중지 완료 (컨테이너 유지, 삭제 아님)"
    ;;

  # --- 재시작 ---
  restart)
    echo "=== 재시작 ==="
    cd $PROJECT_DIR
    docker compose -f docker-compose.prod.yml restart
    ;;

  # --- 상태 확인 ---
  status)
    cd $PROJECT_DIR
    echo "=== 컨테이너 상태 ==="
    docker compose -f docker-compose.prod.yml ps
    echo ""
    echo "=== 리소스 사용량 ==="
    docker stats --no-stream trading-bot 2>/dev/null || echo "컨테이너 미실행"
    ;;

  # --- 로그 확인 ---
  logs)
    cd $PROJECT_DIR
    docker compose -f docker-compose.prod.yml logs -f --tail=100
    ;;

  # --- 모의매매 로그만 ---
  logs-trading)
    cd $PROJECT_DIR
    docker exec trading-bot tail -f /app/logs/paper_trading.log
    ;;

  # --- FastAPI 로그만 ---
  logs-api)
    cd $PROJECT_DIR
    docker exec trading-bot tail -f /app/logs/fastapi.log
    ;;

  *)
    echo "사용법: $0 {setup|deploy|stop|restart|status|logs|logs-trading|logs-api}"
    exit 1
    ;;
esac
