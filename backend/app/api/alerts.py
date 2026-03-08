"""
알림 API 엔드포인트
- 알림 규칙 CRUD
- 사용처: 알림 설정 페이지
"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter()


@router.get("")
async def list_alerts():
    """알림 설정 목록"""
    return success_response({"alerts": []})


@router.post("")
async def create_alert():
    """알림 규칙 생성"""
    return success_response({"message": "알림 생성 (구현 예정)"})


@router.put("/{alert_id}")
async def update_alert(alert_id: str):
    """알림 규칙 수정"""
    return success_response({"message": f"알림 {alert_id} 수정 (구현 예정)"})


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """알림 규칙 삭제"""
    return success_response({"message": f"알림 {alert_id} 삭제 (구현 예정)"})
