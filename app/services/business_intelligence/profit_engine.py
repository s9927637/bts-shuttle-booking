"""
profit_engine — 獲利能力分數 + 財務預估計算引擎。

成本模型（每趟次）：
  車輛成本  每台車 NT$1,500（8 座小巴估算，含司機）
  平台成本  NT$500 固定（系統費用）
  客服成本  每人 NT$50

收入模型：
  每人票價  NT$2,000（預設，可未來由 EventTemplate 動態讀取）

profitability_score（0–100）規則：
  利潤率 > 40% → 80–100
  利潤率 25–40% → 60–79
  利潤率 10–25% → 40–59
  利潤率 0–10%  → 20–39
  利潤率 < 0    → 0–19
"""
from __future__ import annotations

import math

_PRICE_PER_PERSON   = 2_000   # 每人票價（NT$）
_VEHICLE_CAPACITY   = 8       # 每台車座位數
_VEHICLE_COST       = 1_500   # 每台車成本（NT$）
_PLATFORM_COST      = 500     # 固定平台費（NT$）
_SERVICE_COST_PP    = 50      # 每人客服成本（NT$）


def compute_profit(passengers: int) -> dict:
    """
    計算財務預估值。
    回傳 {revenue, vehicles, cost, profit, margin_pct}。
    """
    vehicles = max(math.ceil(passengers / _VEHICLE_CAPACITY), 1)

    revenue = passengers * _PRICE_PER_PERSON
    cost    = (
        vehicles * _VEHICLE_COST
        + _PLATFORM_COST
        + passengers * _SERVICE_COST_PP
    )
    profit  = revenue - cost
    margin  = (profit / revenue * 100) if revenue > 0 else 0.0

    return {
        "revenue":    revenue,
        "vehicles":   vehicles,
        "cost":       cost,
        "profit":     profit,
        "margin_pct": round(margin, 1),
    }


def compute_profitability_score(passengers: int) -> int:
    """依預估利潤率計算 profitability_score（0–100）。"""
    if passengers <= 0:
        return 0

    result = compute_profit(passengers)
    margin = result["margin_pct"]

    if margin > 40:
        return min(80 + int((margin - 40) * 2), 100)
    elif margin >= 25:
        return 60 + int((margin - 25) / 15 * 20)
    elif margin >= 10:
        return 40 + int((margin - 10) / 15 * 20)
    elif margin >= 0:
        return 20 + int(margin / 10 * 20)
    else:
        return max(0, 10 + int(margin))
