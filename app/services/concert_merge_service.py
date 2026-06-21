"""
concert_merge_service — 跨來源演唱會資料合併服務。

當 KKTIX 與 TixCraft 抓到同一場演唱會時，不建立兩筆重複資料，
而是更新既有記錄的 source_type / source_urls，保留所有來源連結。

合併策略（依優先順序）：
  1. crawler_hash 完全相同 → 已由 BaseCrawler.save() 處理（update 模式）
  2. 同日期 + 活動名稱完全相同 → 直接合併
  3. 同日期 + 活動名稱高度相似（≥ 0.8 Jaccard） → 合併並記 log

使用方式：
    from app.services.concert_merge_service import merge_concert
    was_merged = merge_concert(record)  # True=已合併，False=需新建
"""
from __future__ import annotations

import json
import re
from datetime import datetime


def merge_concert(record: dict) -> bool:
    """
    嘗試將 record 與既有 Concert 合併。
    成功合併 → 回傳 True（呼叫方不需新建資料）。
    找不到候選 → 回傳 False（呼叫方應新建資料）。
    """
    from app import db
    from app.models.concert import Concert

    date_val   = record.get("concert_date")
    name       = (record.get("name") or "").strip()
    source_url = record.get("source_url") or ""
    source_type = record.get("source_type") or ""

    if not date_val or not name:
        return False

    # 查同日期的既有演唱會
    candidates = Concert.query.filter_by(concert_date=date_val).all()
    if not candidates:
        return False

    for existing in candidates:
        similarity = _name_similarity(name, existing.name or "")
        if similarity >= 0.8:
            _do_merge(existing, record, source_url, source_type)
            db.session.commit()
            return True

    return False


def _do_merge(existing, record: dict, new_url: str, new_source_type: str):
    """將 record 資訊合併進 existing Concert。"""
    # 更新 source_urls（JSON list）
    try:
        urls: list[str] = json.loads(existing.source_urls or "[]")
    except (json.JSONDecodeError, TypeError):
        urls = [existing.source_url] if existing.source_url else []

    if new_url and new_url not in urls:
        urls.append(new_url)
    existing.source_urls = json.dumps(urls, ensure_ascii=False)

    # 更新 source_type（合併成 KKTIX,TIXCRAFT 這種格式）
    types_set: set[str] = set()
    if existing.source_type:
        types_set.update(existing.source_type.split(","))
    if new_source_type:
        types_set.add(new_source_type)
    existing.source_type = ",".join(sorted(types_set))

    # 若 source_url 原本為空，填入新 URL
    if not existing.source_url and new_url:
        existing.source_url = new_url

    # 補齊城市 / 場館（若原本為空或「待確認」）
    if record.get("city") and (not existing.city or existing.city == "待確認"):
        existing.city = record["city"]
    if record.get("venue") and (not existing.venue or existing.venue == "待確認"):
        existing.venue = record["venue"]

    existing.updated_at = datetime.utcnow()


def _name_similarity(a: str, b: str) -> float:
    """
    Jaccard 相似度（token 層面）。
    移除年份、特殊字元後計算。
    """
    def tokenize(s: str) -> set[str]:
        s = re.sub(r"20\d{2}", "", s)
        s = re.sub(r"[^\w一-鿿]+", " ", s, flags=re.UNICODE)
        return {t.lower() for t in s.split() if t}

    set_a = tokenize(a)
    set_b = tokenize(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union        = set_a | set_b
    return len(intersection) / len(union)


def get_source_stats() -> dict:
    """
    回傳各來源的演唱會統計。
    供 /api/crawlers/sources 使用。
    """
    from app import db
    from app.models.concert import Concert

    total   = Concert.query.count()
    kktix   = Concert.query.filter(Concert.source_type.like("%KKTIX%")).count()
    tixcraft = Concert.query.filter(Concert.source_type.like("%TIXCRAFT%")).count()
    merged  = Concert.query.filter(Concert.source_type.like("%,%")).count()
    unknown = Concert.query.filter(
        (Concert.source_type == None) | (Concert.source_type == "")
    ).count()

    return {
        "total":    total,
        "kktix":    kktix,
        "tixcraft": tixcraft,
        "merged":   merged,
        "unknown":  unknown,
    }
