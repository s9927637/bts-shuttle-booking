"""
data_quality_validator — 演唱會資料品質驗證。

使用方式：
    from app.services.data_quality_validator import validate_concert, ValidationResult
    result = validate_concert(record)
    if not result.is_valid:
        print(result.errors)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    is_valid: bool
    errors:   list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_concert(record: dict) -> ValidationResult:
    """
    驗證單筆演唱會資料。
    必填：活動名稱、活動日期、場館（或城市）。
    """
    errors:   list[str] = []
    warnings: list[str] = []

    name         = (record.get("name") or "").strip()
    artist       = (record.get("artist") or "").strip()
    concert_date = record.get("concert_date")
    venue        = (record.get("venue") or "").strip()
    city         = (record.get("city") or "").strip()

    # ── 必填欄位 ──────────────────────────────────────────────────────────────

    if not name:
        errors.append("活動名稱不可空白")
    elif len(name) < 2:
        errors.append(f"活動名稱過短（{name!r}），至少需 2 個字元")

    if concert_date is None:
        errors.append("活動日期不可空白")

    if not venue or venue in ("待確認", "TBD", ""):
        if not city or city in ("待確認", "TBD", ""):
            warnings.append("場館與城市均未填，請人工確認")
        else:
            warnings.append(f"場館未填，城市為「{city}」")

    # ── 軟性警告 ──────────────────────────────────────────────────────────────

    if not artist or artist in ("未知藝人", "unknown"):
        warnings.append("藝人名稱未辨識，已設為預設值")

    if not record.get("source_url"):
        warnings.append("缺少 source_url")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_batch(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    批次驗證。
    回傳 (valid_records, invalid_records)。
    invalid_records 每筆附帶 _validation_errors 欄位。
    """
    valid:   list[dict] = []
    invalid: list[dict] = []

    for rec in records:
        result = validate_concert(rec)
        if result.is_valid:
            valid.append(rec)
        else:
            invalid.append({**rec, "_validation_errors": result.errors})

    return valid, invalid
