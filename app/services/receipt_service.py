"""
receipt_service.py — 收據 PDF 生成服務

使用 reportlab + Noto Sans TC 字體產生繁體中文 PDF 收據。
"""

import os
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 字體初始化 ─────────────────────────────────────────────────────────────
_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),   # app/
    "static", "fonts", "NotoSansTC-Regular.ttf"
)
_FONT_REGISTERED = False


def _ensure_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    if os.path.exists(_FONT_PATH):
        pdfmetrics.registerFont(TTFont("NotoSansTC", _FONT_PATH))
        _FONT_REGISTERED = True
    else:
        raise FileNotFoundError(f"找不到字體檔案：{_FONT_PATH}")


# ── 付款方式標籤 ───────────────────────────────────────────────────────────
PAYMENT_SOURCE_LABELS = {
    "bank_transfer_report": "銀行匯款",
    "admin_confirmed":      "後台確認",
    "legacy_customer":      "舊客戶補單",
    "cash":                 "現金付款",
}

RECEIPT_TYPE_NOTES = {
    "deposit": [
        "已收到訂金並保留座位。",
        "尾款將於乘車當日以現金支付給司機。",
        "請妥善保存本收據，如有疑問請聯繫客服。",
    ],
    "balance": [
        "已收到本次包車服務尾款。",
        "感謝您的搭乘，祝您觀賞演唱會愉快。",
    ],
    "refund": [
        "退款已完成。",
        "如有任何疑問請聯繫客服。",
    ],
}

RECEIPT_ITEM_LABELS = {
    "deposit": "訂金",
    "balance": "尾款",
    "refund":  "退款",
}


def generate_receipt_pdf(receipt, order, payment=None) -> bytes:
    """
    產生收據 PDF，回傳 bytes。

    Args:
        receipt: Receipt model instance
        order:   Order model instance
        payment: Payment model instance (optional, 用於付款方式顯示)
    Returns:
        PDF bytes
    """
    _ensure_font()

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # ── 樣式定義 ────────────────────────────────────────────────────────────
    def style(name, size=10, bold=False, color=colors.black, leading=None, align="LEFT"):
        return ParagraphStyle(
            name,
            fontName="NotoSansTC",
            fontSize=size,
            textColor=color,
            leading=leading or (size * 1.5),
            alignment={"LEFT": 0, "CENTER": 1, "RIGHT": 2}.get(align, 0),
        )

    s_title      = style("Title",   size=18, color=colors.HexColor("#1a1a2e"), align="CENTER")
    s_subtitle   = style("Sub",     size=11, color=colors.HexColor("#4a4a6a"), align="CENTER")
    s_label      = style("Label",   size=9,  color=colors.HexColor("#6b7280"))
    s_value      = style("Value",   size=9,  color=colors.HexColor("#111827"))
    s_amount     = style("Amount",  size=14, color=colors.HexColor("#111827"), align="RIGHT")
    s_note_head  = style("NoteH",   size=9,  color=colors.HexColor("#374151"))
    s_note_body  = style("NoteB",   size=8,  color=colors.HexColor("#6b7280"))
    s_footer     = style("Footer",  size=7.5,color=colors.HexColor("#9ca3af"), align="CENTER")
    s_void       = style("Void",    size=28, color=colors.HexColor("#ef4444"), align="CENTER")

    story = []

    # ── 標題區 ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("BTS 高雄演唱會來回包車服務", s_title))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"{receipt.type_label}收據", s_subtitle))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 5 * mm))

    # 作廢浮水印
    if receipt.status == "void":
        story.append(Paragraph("【 已 作 廢 】", s_void))
        story.append(Spacer(1, 4 * mm))

    # ── 收據資訊表格 ─────────────────────────────────────────────────────────
    issued_at_str = (
        receipt.issued_at.strftime("%Y 年 %m 月 %d 日")
        if receipt.issued_at else "—"
    )

    info_data = [
        [Paragraph("收據編號", s_label), Paragraph(receipt.receipt_no, s_value)],
        [Paragraph("訂單編號", s_label), Paragraph(order.order_no, s_value)],
        [Paragraph("姓名",     s_label), Paragraph(order.contact_name, s_value)],
        [Paragraph("聯絡電話", s_label), Paragraph(order.phone, s_value)],
        [Paragraph("活動名稱", s_label), Paragraph("BTS WORLD TOUR 'PERMISSION TO DANCE' — 高雄", s_value)],
        [Paragraph("搭乘日期", s_label), Paragraph(order.departure_date, s_value)],
        [Paragraph("付款項目", s_label), Paragraph(RECEIPT_ITEM_LABELS.get(receipt.receipt_type, "—"), s_value)],
        [Paragraph("付款方式", s_label), Paragraph(
            PAYMENT_SOURCE_LABELS.get(payment.payment_source, "—") if payment else "—",
            s_value
        )],
        [Paragraph("開立日期", s_label), Paragraph(issued_at_str, s_value)],
    ]

    col_w = [38 * mm, 120 * mm]
    info_tbl = Table(info_data, colWidths=col_w, hAlign="LEFT")
    info_tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LINEBELOW",    (0, 0), (-1, -2), 0.5, colors.HexColor("#f3f4f6")),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── 金額區塊 ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 4 * mm))

    amount_formatted = f"NT$ {receipt.amount:,}"
    amount_data = [
        [Paragraph("付款金額", s_label), Paragraph(amount_formatted, s_amount)],
    ]
    amount_tbl = Table(amount_data, colWidths=[col_w[0], col_w[1]], hAlign="LEFT")
    amount_tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    story.append(amount_tbl)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 6 * mm))

    # ── 備註 ────────────────────────────────────────────────────────────────
    notes = RECEIPT_TYPE_NOTES.get(receipt.receipt_type, [])
    if notes:
        story.append(Paragraph("備註", s_note_head))
        story.append(Spacer(1, 2 * mm))
        for note in notes:
            story.append(Paragraph(f"・{note}", s_note_body))
        story.append(Spacer(1, 6 * mm))

    # 作廢資訊
    if receipt.status == "void" and receipt.void_reason:
        story.append(Paragraph("作廢原因", s_note_head))
        story.append(Spacer(1, 2 * mm))
        void_at_str = receipt.void_at.strftime("%Y/%m/%d %H:%M") if receipt.void_at else "—"
        story.append(Paragraph(f"{receipt.void_reason}（{void_at_str}，由 {receipt.void_by or '—'} 操作）", s_note_body))
        story.append(Spacer(1, 6 * mm))

    # ── 頁尾 ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("BTS 高雄演唱會來回包車服務", s_footer))
    story.append(Paragraph("客服聯絡方式：LINE 官方帳號", s_footer))
    story.append(Paragraph("本收據由系統自動產生，無須蓋章即可作為付款證明。", s_footer))

    doc.build(story)
    return buf.getvalue()
