"""
Auto Group Creation Service

Concert → EventPage 開團流程，含模板套用與 Job 追蹤。
所有業務邏輯集中此處，Route 只負責呼叫。
"""
from datetime import datetime
from typing import Optional

from app import db
from app.models.concert import Concert, ConcertOpportunity, ConcertMetrics
from app.models.event_page import EventPage
from app.models.event_template import EventTemplate
from app.models.group_creation_job import GroupCreationJob
from app.services.event_builder import EventAlreadyExists, build_event_from_concert


# ── 推薦候選清單 ──────────────────────────────────────────────────────────────

def get_recommended_concerts() -> list[dict]:
    """
    回傳推薦開團的演唱會清單。

    規則：
    - Concert 尚未有對應的 EventPage（未軟刪除）
    - Concert 有 ConcertMetrics 資料
    - 依 opportunity_score 降冪排序
    """
    concerts_with_metrics = (
        db.session.query(Concert, ConcertMetrics)
        .join(ConcertMetrics, ConcertMetrics.concert_id == Concert.id)
        .all()
    )

    # 過濾掉已有 EventPage 的 Concert
    existing_concert_ids = {
        ep.concert_id
        for ep in EventPage.query
        .filter(EventPage.concert_id.isnot(None), EventPage.deleted_at.is_(None))
        .all()
    }

    result = []
    for concert, metrics in concerts_with_metrics:
        if concert.id in existing_concert_ids:
            continue
        # 取最高優先商機
        top_opp = (
            ConcertOpportunity.query
            .filter_by(concert_id=concert.id)
            .order_by(
                db.case(
                    (ConcertOpportunity.priority == "高", 0),
                    (ConcertOpportunity.priority == "中", 1),
                    else_=2,
                )
            )
            .first()
        )
        result.append({
            "concert":         concert,
            "metrics":         metrics,
            "top_opportunity": top_opp,
        })

    result.sort(key=lambda x: x["metrics"].opportunity_score or 0, reverse=True)
    return result


# ── 一鍵開團 ─────────────────────────────────────────────────────────────────

class GroupCreationResult:
    def __init__(self, success: bool, job: GroupCreationJob,
                 event_page: Optional[EventPage] = None, error: Optional[str] = None):
        self.success    = success
        self.job        = job
        self.event_page = event_page
        self.error      = error


def create_group(
    concert_id:     int,
    template_id:    Optional[int] = None,
    opportunity_id: Optional[int] = None,
) -> GroupCreationResult:
    """
    從 Concert 建立 EventPage，並記錄 GroupCreationJob。

    - 防呆：若 Concert 已有 EventPage，Job 狀態設為 duplicate，回傳現有 EventPage。
    - 若指定 template_id，以模板覆蓋 price / deposit / departure_city。
    - 呼叫方不需自行 commit — 本函式統一處理。
    """
    concert = Concert.query.get(concert_id)
    if not concert:
        raise ValueError(f"Concert id={concert_id} 不存在")

    template = EventTemplate.query.get(template_id) if template_id else None

    job = GroupCreationJob(
        concert_id     = concert_id,
        opportunity_id = opportunity_id,
        template_id    = template_id,
        status         = "pending",
        created_at     = datetime.utcnow(),
        updated_at     = datetime.utcnow(),
    )
    db.session.add(job)

    try:
        ep = build_event_from_concert(concert)

        # 套用模板
        if template:
            ep.price          = template.price
            ep.deposit        = template.deposit
            if template.departure_city:
                ep.departure_city = template.departure_city

        db.session.flush()  # 取得 ep.id
        job.event_page_id = ep.id
        job.status        = "success"
        job.updated_at    = datetime.utcnow()
        db.session.commit()
        return GroupCreationResult(success=True, job=job, event_page=ep)

    except EventAlreadyExists as exc:
        existing_ep = exc.event_page
        job.event_page_id = existing_ep.id
        job.status        = "duplicate"
        job.error_message = f"EventPage 已存在：{existing_ep.slug}"
        job.updated_at    = datetime.utcnow()
        db.session.commit()
        return GroupCreationResult(success=False, job=job, event_page=existing_ep, error=job.error_message)

    except Exception as exc:
        db.session.rollback()
        job.status        = "error"
        job.error_message = str(exc)[:500]
        job.updated_at    = datetime.utcnow()
        db.session.add(job)
        db.session.commit()
        return GroupCreationResult(success=False, job=job, error=job.error_message)


# ── 開團數統計（Dashboard 用）────────────────────────────────────────────────

def count_created_groups() -> int:
    return GroupCreationJob.query.filter_by(status="success").count()
