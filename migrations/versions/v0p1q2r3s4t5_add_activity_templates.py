"""add activity_templates and activity_template_sections

Revision ID: v0p1q2r3s4t5
Revises: u9o0p1q2r3s4
Create Date: 2026-06-22
"""
import json
from datetime import datetime
from alembic import op
import sqlalchemy as sa

revision = 'v0p1q2r3s4t5'
down_revision = 'u9o0p1q2r3s4'
branch_labels = None
depends_on = None

_NOW = datetime.utcnow()


def upgrade():
    # ── 建立 activity_templates ──────────────────────────────────────────────
    op.create_table(
        'activity_templates',
        sa.Column('id',          sa.Integer(),     nullable=False, primary_key=True),
        sa.Column('name',        sa.String(100),   nullable=False),
        sa.Column('description', sa.Text(),        nullable=True),
        sa.Column('theme_color', sa.String(30),    nullable=True, server_default='purple'),
        sa.Column('is_default',  sa.Boolean(),     nullable=False, server_default='false'),
        sa.Column('created_at',  sa.DateTime(),    nullable=True),
        sa.Column('updated_at',  sa.DateTime(),    nullable=True),
    )

    # ── 建立 activity_template_sections ──────────────────────────────────────
    op.create_table(
        'activity_template_sections',
        sa.Column('id',           sa.Integer(),     nullable=False, primary_key=True),
        sa.Column('template_id',  sa.Integer(),     nullable=False),
        sa.Column('type',         sa.String(50),    nullable=False),
        sa.Column('title',        sa.String(200),   nullable=True),
        sa.Column('content_json', sa.Text(),        nullable=True),
        sa.Column('sort_order',   sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('is_active',    sa.Boolean(),     nullable=False, server_default='true'),
        sa.Column('created_at',   sa.DateTime(),    nullable=True),
        sa.Column('updated_at',   sa.DateTime(),    nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['activity_templates.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_activity_template_sections_template_id',
                    'activity_template_sections', ['template_id'])

    # ── 種入 BTS 標準演唱會範本 ────────────────────────────────────────────────
    conn = op.get_bind()

    # 插入範本主體
    conn.execute(sa.text(
        "INSERT INTO activity_templates (name, description, theme_color, is_default, created_at, updated_at) "
        "VALUES (:name, :desc, :color, :default, :now, :now)"
    ), {
        'name':    'BTS 標準演唱會範本',
        'desc':    '標準演唱會包車活動範本，包含完整九個區塊：Hero、特色、車型、流程、集合地點、FAQ、注意事項、CTA、頁尾。',
        'color':   'purple',
        'default': True,
        'now':     _NOW,
    })
    tmpl_id = conn.execute(sa.text("SELECT lastval()")).scalar()

    # 九個預設區塊
    sections = [
        (1, 'hero', 'Hero Banner', {
            'title':         'BTS WORLD TOUR',
            'subtitle':      'BTS 高雄演唱會包車服務',
            'tour_name':     'WORLD TOUR',
            'route':         '台北 ↔ 高雄',
            'event_date':    '2025/08/17',
            'venue':         '高雄巨蛋',
            'price':         2000,
            'image_url':     '',
            'primary_btn':   '立即預約',
            'secondary_btn': '了解詳情',
        }),
        (2, 'highlights', '服務特色', {
            'items': [
                {'icon': '🚌', 'title': '舒適直達',   'desc': '點對點接送，免等台鐵高鐵'},
                {'icon': '🎪', 'title': '散場接送',   'desc': '演唱會結束直接上車返程'},
                {'icon': '💺', 'title': '豪華座艙',   'desc': '寬敞商旅車，旅途舒適'},
                {'icon': '📱', 'title': 'LINE 通知',  'desc': '成團、出發前即時通知'},
            ],
        }),
        (3, 'vehicle_showcase', '車型介紹', {
            'vehicles': [
                {
                    'name':  '九座商旅車',
                    'image': '',
                    'desc':  '最多乘載 9 人，寬敞行李空間，適合團體出行。',
                },
                {
                    'name':  'NX200 專屬包車',
                    'image': '',
                    'desc':  '豪華 SUV，4 人以下專屬包車，舒適私密。',
                },
            ],
        }),
        (4, 'process', '預約流程', {
            'steps': [
                {'icon': '📝', 'title': '線上預約', 'desc': '填寫人數、出發地資訊'},
                {'icon': '💰', 'title': '支付訂金', 'desc': '匯款 NT$300 訂金保留座位'},
                {'icon': '📱', 'title': '等待成團', 'desc': '達 8 人即成團，LINE 即時通知'},
                {'icon': '🚌', 'title': '準時出發', 'desc': '依集合地點準時上車出發'},
            ],
        }),
        (5, 'meeting_point', '集合地點', {
            'locations': [
                {
                    'name':         '台北集合點',
                    'address':      '台北市中正區忠孝西路一段（台北車站旁）',
                    'map_url':      '',
                    'meeting_time': '出發前 30 分鐘',
                    'desc':         '請準時抵達，司機將在現場等候。',
                },
            ],
        }),
        (6, 'faq', '常見問題', {
            'items': [
                {'q': '幾個人才可以報名？',       'a': '1 人即可報名，費用固定 NT$2,000（訂金 NT$300）。'},
                {'q': '何時確認成團？',           'a': '同場次累計 8 人即自動成團，系統將發送 LINE 通知。'},
                {'q': '散場後多久發車？',          'a': '演唱會結束後約 30-60 分鐘，依現場人潮安排。'},
                {'q': '行李可以帶多少？',          'a': '每人限一件 28 吋行李箱，手提行李不限。'},
                {'q': '如何取消訂單？',           'a': '請聯絡客服，訂金退還依退費規則辦理。'},
            ],
        }),
        (7, 'terms', '注意事項', {
            'deposit_rule': '訂金 NT$300，尾款於出發當日現金交付司機。',
            'refund_rule':  '活動官方取消退全額。個人取消：出發前 7 天以上退 80%，3-7 天退 50%，3 天內不退款。',
            'ride_rules': [
                '請準時抵達集合地點，逾時 15 分鐘視同棄車，不退款。',
                '車內禁止飲食（飲水除外）、吸菸、攜帶酒精。',
                '請妥善保管個人財物，遺失概不負責。',
                '若有特殊需求（輪椅、嬰兒車等），請提前告知。',
            ],
        }),
        (8, 'cta', '立即預約', {
            'title':    '準備好出發了嗎？',
            'desc':     '現在預約，確保您的座位！名額有限，請盡早預訂。',
            'btn_text': '立即預約',
        }),
        (9, 'footer', '頁尾', {
            'contact':   'LINE ID: @bts-shuttle',
            'copyright': '© 2024 BTS Shuttle 包車服務',
            'social': [
                {'platform': 'LINE',      'url': 'https://line.me/'},
                {'platform': 'Instagram', 'url': 'https://instagram.com/'},
            ],
        }),
    ]

    for sort_order, sec_type, title, content in sections:
        conn.execute(sa.text(
            "INSERT INTO activity_template_sections "
            "(template_id, type, title, content_json, sort_order, is_active, created_at, updated_at) "
            "VALUES (:tid, :type, :title, :content, :sort, true, :now, :now)"
        ), {
            'tid':     tmpl_id,
            'type':    sec_type,
            'title':   title,
            'content': json.dumps(content, ensure_ascii=False),
            'sort':    sort_order,
            'now':     _NOW,
        })


def downgrade():
    op.drop_table('activity_template_sections')
    op.drop_table('activity_templates')
