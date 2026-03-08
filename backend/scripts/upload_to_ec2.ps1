# ==============================================
# EC2 업로드 스크립트 (PowerShell)
#
# 사용법:
#   .\scripts\upload_to_ec2.ps1
#
# 사전 설정:
#   아래 변수를 본인 환경에 맞게 수정
# ==============================================

# ← 본인 환경에 맞게 수정
$EC2_HOST = "ubuntu@YOUR_EC2_IP"
$KEY_FILE = "C:\Users\ailee\.ssh\your-key.pem"
$REMOTE_DIR = "~/trading/backend"
$LOCAL_DIR = "C:\Users\ailee\github\trading\backend"

Write-Host "=== EC2 업로드 시작 ===" -ForegroundColor Cyan

# 1. 파일 전송 (scp)
Write-Host "파일 전송 중..." -ForegroundColor Yellow
scp -i $KEY_FILE -r `
    "$LOCAL_DIR\app" `
    "$LOCAL_DIR\scripts" `
    "$LOCAL_DIR\requirements.txt" `
    "$LOCAL_DIR\Dockerfile" `
    "$LOCAL_DIR\supervisord.conf" `
    "$LOCAL_DIR\docker-compose.prod.yml" `
    "$LOCAL_DIR\.dockerignore" `
    "${EC2_HOST}:${REMOTE_DIR}/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "파일 전송 실패!" -ForegroundColor Red
    exit 1
}

# 2. 원격에서 배포 실행
Write-Host "원격 배포 실행..." -ForegroundColor Yellow
ssh -i $KEY_FILE $EC2_HOST "cd $REMOTE_DIR && bash scripts/deploy_ec2.sh deploy"

Write-Host ""
Write-Host "=== 배포 완료 ===" -ForegroundColor Green
Write-Host "상태 확인: ssh -i $KEY_FILE $EC2_HOST 'cd $REMOTE_DIR && bash scripts/deploy_ec2.sh status'"
Write-Host "로그 확인: ssh -i $KEY_FILE $EC2_HOST 'cd $REMOTE_DIR && bash scripts/deploy_ec2.sh logs'"
