"""
Activity Template Blueprint

後台管理：
  GET  /admin/activity-templates              範本列表
  POST /admin/activity-templates/create       建立範本
  GET  /admin/activity-templates/<id>/edit    編輯範本
  POST /admin/activity-templates/<id>/edit    儲存編輯
  POST /admin/activity-templates/<id>/delete  刪除範本
  POST /admin/activity-templates/<id>/clone   複製範本
  POST /admin/activity-templates/<id>/set-default  設為預設

區塊管理：
  GET  /admin/activity-templates/<id>/sections                 區塊列表
  POST /admin/activity-templates/<id>/sections                 新增區塊
  GET  /admin/activity-templates/<id>/sections/<sid>/edit      編輯區塊
  POST /admin/activity-templates/<id>/sections/<sid>/edit      儲存區塊
  POST /admin/activity-templates/<id>/sections/<sid>/delete    刪除區塊
  POST /admin/activity-templates/<id>/sections/<sid>/toggle    切換啟用（JSON）
  POST /admin/activity-templates/<id>/sections/reorder         排序（JSON）

建立活動流程：
  GET  /admin/event-pages/from-template       選擇範本 + 填寫基本資訊
  POST /admin/event-pages/from-template       建立活動並複製區塊

另存為範本：
  POST /admin/event-pages/<id>/save-as-template
"""
import json
from datetime import datetime

from flask import (Blueprint, flash, jsonify, redirect,
                   render_template, request, session, url_for)

from app import db, csrf
from app.models.activity_template import (
    ActivityTemplate, ActivityTemplateSection,
    SECTION_TYPES, SECTION_TYPE_LABELS,
)
from app.models.event_page import EventPage
from app.models.event_section import EventSection

activity_template_bp = Blueprint('activity_template', __name__)


def _require_admin():
    if not session.get('admin_id'):
        return redirect(url_for('auth.login_page'))


# ── 列表 ──────────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates')
@activity_template_bp.route('/admin/activity-templates/')
def at_list():
    guard = _require_admin()
    if guard:
        return guard
    templates = ActivityTemplate.query.order_by(
        ActivityTemplate.is_default.desc(),
        ActivityTemplate.created_at.desc(),
    ).all()
    return render_template('admin/activity_templates/list.html', templates=templates)


# ── 建立 ──────────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/create', methods=['GET', 'POST'])
def at_create():
    guard = _require_admin()
    if guard:
        return guard

    if request.method == 'GET':
        return render_template('admin/activity_templates/form.html',
                               mode='create', tmpl=None)

    name        = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip() or None
    theme_color = request.form.get('theme_color', 'purple') or 'purple'

    if not name:
        flash('範本名稱為必填。', 'error')
        return redirect(url_for('activity_template.at_create'))

    tmpl = ActivityTemplate(
        name=name, description=description,
        theme_color=theme_color, is_default=False,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.session.add(tmpl)
    db.session.commit()
    flash(f'已建立範本「{name}」。', 'success')
    return redirect(url_for('activity_template.at_sections', tmpl_id=tmpl.id))


# ── 編輯 ──────────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/edit',
                             methods=['GET', 'POST'])
def at_edit(tmpl_id):
    guard = _require_admin()
    if guard:
        return guard

    tmpl = ActivityTemplate.query.get_or_404(tmpl_id)

    if request.method == 'GET':
        return render_template('admin/activity_templates/form.html',
                               mode='edit', tmpl=tmpl)

    tmpl.name        = request.form.get('name', tmpl.name).strip()
    tmpl.description = request.form.get('description', '').strip() or None
    tmpl.theme_color = request.form.get('theme_color', tmpl.theme_color or 'purple') or 'purple'
    tmpl.updated_at  = datetime.utcnow()
    db.session.commit()
    flash(f'已更新範本「{tmpl.name}」。', 'success')
    return redirect(url_for('activity_template.at_list'))


# ── 刪除 ──────────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/delete', methods=['POST'])
def at_delete(tmpl_id):
    guard = _require_admin()
    if guard:
        return guard

    tmpl = ActivityTemplate.query.get_or_404(tmpl_id)
    name = tmpl.name
    db.session.delete(tmpl)
    db.session.commit()
    flash(f'已刪除範本「{name}」。', 'success')
    return redirect(url_for('activity_template.at_list'))


# ── 複製 ──────────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/clone', methods=['POST'])
def at_clone(tmpl_id):
    guard = _require_admin()
    if guard:
        return guard

    src = ActivityTemplate.query.get_or_404(tmpl_id)
    clone = ActivityTemplate(
        name=f'{src.name}（副本）',
        description=src.description,
        theme_color=src.theme_color,
        is_default=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(clone)
    db.session.flush()
    for s in src.sections.all():
        db.session.add(ActivityTemplateSection(
            template_id=clone.id, type=s.type, title=s.title,
            content_json=s.content_json, sort_order=s.sort_order,
            is_active=s.is_active,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        ))
    db.session.commit()
    flash(f'已複製範本為「{clone.name}」。', 'success')
    return redirect(url_for('activity_template.at_sections', tmpl_id=clone.id))


# ── 設為預設 ──────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/set-default', methods=['POST'])
def at_set_default(tmpl_id):
    guard = _require_admin()
    if guard:
        return guard

    ActivityTemplate.query.update({'is_default': False})
    tmpl = ActivityTemplate.query.get_or_404(tmpl_id)
    tmpl.is_default = True
    tmpl.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f'「{tmpl.name}」已設為預設範本。', 'success')
    return redirect(url_for('activity_template.at_list'))


# ── 區塊列表 ──────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/sections',
                             methods=['GET', 'POST'])
def at_sections(tmpl_id):
    guard = _require_admin()
    if guard:
        return guard

    tmpl = ActivityTemplate.query.get_or_404(tmpl_id)

    if request.method == 'POST':
        sec_type     = request.form.get('type', '')
        title        = request.form.get('title', '').strip() or None
        content_json = request.form.get('content_json', '').strip()
        max_order    = db.session.query(
            db.func.max(ActivityTemplateSection.sort_order)
        ).filter_by(template_id=tmpl_id).scalar() or 0

        if not content_json:
            content_json = json.dumps({}, ensure_ascii=False)
        try:
            json.loads(content_json)
        except json.JSONDecodeError:
            flash('Content JSON 格式錯誤。', 'error')
            return redirect(url_for('activity_template.at_sections', tmpl_id=tmpl_id))

        sec = ActivityTemplateSection(
            template_id=tmpl_id, type=sec_type, title=title,
            content_json=content_json, sort_order=max_order + 1,
            is_active=True,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db.session.add(sec)
        db.session.commit()
        flash('已新增區塊。', 'success')
        return redirect(url_for('activity_template.at_sections', tmpl_id=tmpl_id))

    sections = tmpl.sections.order_by(ActivityTemplateSection.sort_order).all()
    return render_template('admin/activity_templates/sections.html',
                           tmpl=tmpl, sections=sections,
                           section_types=SECTION_TYPES,
                           type_labels=SECTION_TYPE_LABELS)


# ── 區塊編輯 ──────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/sections/<int:sec_id>/edit',
                             methods=['GET', 'POST'])
def at_section_edit(tmpl_id, sec_id):
    guard = _require_admin()
    if guard:
        return guard

    tmpl = ActivityTemplate.query.get_or_404(tmpl_id)
    sec  = ActivityTemplateSection.query.filter_by(id=sec_id, template_id=tmpl_id).first_or_404()

    if request.method == 'POST':
        sec.title        = request.form.get('title', '').strip() or None
        content_json     = request.form.get('content_json', '').strip()
        try:
            json.loads(content_json)
            sec.content_json = content_json
        except json.JSONDecodeError:
            flash('Content JSON 格式錯誤，請修正後再儲存。', 'error')
            return render_template('admin/activity_templates/section_edit.html',
                                   tmpl=tmpl, sec=sec,
                                   type_labels=SECTION_TYPE_LABELS)
        sec.updated_at = datetime.utcnow()
        db.session.commit()
        flash('區塊已儲存。', 'success')
        return redirect(url_for('activity_template.at_sections', tmpl_id=tmpl_id))

    return render_template('admin/activity_templates/section_edit.html',
                           tmpl=tmpl, sec=sec, type_labels=SECTION_TYPE_LABELS)


# ── 區塊刪除 ──────────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/sections/<int:sec_id>/delete',
                             methods=['POST'])
def at_section_delete(tmpl_id, sec_id):
    guard = _require_admin()
    if guard:
        return guard

    sec = ActivityTemplateSection.query.filter_by(id=sec_id, template_id=tmpl_id).first_or_404()
    db.session.delete(sec)
    db.session.commit()
    flash('區塊已刪除。', 'success')
    return redirect(url_for('activity_template.at_sections', tmpl_id=tmpl_id))


# ── 區塊啟用切換（JSON）─────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/sections/<int:sec_id>/toggle',
                             methods=['POST'])
def at_section_toggle(tmpl_id, sec_id):
    guard = _require_admin()
    if guard:
        return jsonify({'ok': False}), 401

    sec = ActivityTemplateSection.query.filter_by(id=sec_id, template_id=tmpl_id).first_or_404()
    sec.is_active  = not sec.is_active
    sec.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'is_active': sec.is_active})


# ── 排序（JSON）──────────────────────────────────────────────────────────────

@activity_template_bp.route('/admin/activity-templates/<int:tmpl_id>/sections/reorder',
                             methods=['POST'])
@csrf.exempt
def at_section_reorder(tmpl_id):
    guard = _require_admin()
    if guard:
        return jsonify({'ok': False}), 401

    data = request.get_json() or {}
    order = data.get('order', [])
    for i, item in enumerate(order):
        ActivityTemplateSection.query.filter_by(
            id=item['id'], template_id=tmpl_id
        ).update({'sort_order': i + 1})
    db.session.commit()
    return jsonify({'ok': True})


# ══ 從範本建立活動 ═════════════════════════════════════════════════════════════

@activity_template_bp.route('/admin/event-pages/from-template', methods=['GET', 'POST'])
def ep_from_template():
    guard = _require_admin()
    if guard:
        return guard

    templates = ActivityTemplate.query.order_by(
        ActivityTemplate.is_default.desc(),
        ActivityTemplate.created_at.desc(),
    ).all()
    default_tmpl = next((t for t in templates if t.is_default), None)

    if request.method == 'GET':
        return render_template('admin/activity_templates/from_template.html',
                               templates=templates, default_tmpl=default_tmpl)

    # POST → 建立活動
    tmpl_id    = request.form.get('template_id', type=int)
    artist     = request.form.get('artist_name', '').strip()
    title      = request.form.get('title', '').strip()
    event_date = request.form.get('event_date', '').strip() or None
    venue      = request.form.get('venue', '').strip() or None
    price      = int(request.form.get('price', 2000) or 2000)
    deposit    = int(request.form.get('deposit', 300) or 300)
    theme      = request.form.get('theme_color', 'purple') or 'purple'

    if not artist or not title:
        flash('藝人名稱與活動名稱為必填。', 'error')
        return redirect(url_for('activity_template.ep_from_template'))

    # 產生 slug
    import re
    base = re.sub(r'[^\w一-鿿]', '-', artist.lower())
    base = re.sub(r'-+', '-', base).strip('-') or 'event'
    slug = base
    counter = 1
    while EventPage.query.filter_by(slug=slug).first():
        slug = f'{base}-{counter}'
        counter += 1

    ep = EventPage(
        title=title, slug=slug, artist_name=artist,
        event_name=title, event_date=event_date, venue=venue,
        price=price, deposit=deposit, theme_color=theme,
        status='草稿',
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.session.add(ep)
    db.session.flush()

    # 複製範本區塊 → event_sections
    if tmpl_id:
        tmpl = ActivityTemplate.query.get(tmpl_id)
        if tmpl:
            for ts in tmpl.sections.order_by(ActivityTemplateSection.sort_order).all():
                es = EventSection(
                    event_id=ep.id, type=ts.type, title=ts.title,
                    content_json=ts.content_json, sort_order=ts.sort_order,
                    is_active=ts.is_active,
                    created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
                )
                db.session.add(es)

    db.session.commit()
    flash(f'已從範本建立活動「{title}」，請繼續編輯區塊內容。', 'success')
    return redirect(url_for('event_page.ep_sections', ep_id=ep.id))


# ══ 另存為範本 ════════════════════════════════════════════════════════════════

@activity_template_bp.route('/admin/event-pages/<int:ep_id>/save-as-template', methods=['POST'])
def ep_save_as_template(ep_id):
    guard = _require_admin()
    if guard:
        return guard

    ep        = EventPage.query.get_or_404(ep_id)
    tmpl_name = request.form.get('template_name', '').strip() or f'{ep.artist_name} 標準範本'

    tmpl = ActivityTemplate(
        name=tmpl_name,
        description=f'從活動「{ep.title}」另存的範本。',
        theme_color=ep.theme_color or 'purple',
        is_default=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(tmpl)
    db.session.flush()

    sections = ep.sections.filter_by(is_active=True).order_by(EventSection.sort_order).all()
    for es in sections:
        db.session.add(ActivityTemplateSection(
            template_id=tmpl.id, type=es.type, title=es.title,
            content_json=es.content_json, sort_order=es.sort_order,
            is_active=True,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        ))

    db.session.commit()
    flash(f'已將活動另存為範本「{tmpl_name}」（{len(sections)} 個區塊）。', 'success')
    return redirect(url_for('activity_template.at_list'))
