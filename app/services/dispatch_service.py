"""
Dispatch Service — 排車邏輯
"""
from app import db
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.models.dispatch import Dispatch, DispatchOrder

MAX_CAPACITY = 8
FORBIDDEN_STATUSES = {"待付款", "待確認", "已取消", "退款中", "已退款", "已完成"}


def calculate_capacity(dispatch: Dispatch) -> int:
    """回傳該 dispatch 目前已分配的乘客人數。"""
    return sum(
        do.order.passenger_count
        for do in dispatch.dispatch_orders
        if do.order
    )


def create_dispatch(departure_date: str, vehicle_id: int, driver_id: int = None) -> Dispatch:
    """建立一個新的排車記錄。"""
    d = Dispatch(
        departure_date=departure_date,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        status="排車中",
    )
    db.session.add(d)
    db.session.flush()  # 取得 id
    return d


def assign_order(dispatch: Dispatch, order: Order) -> bool:
    """將訂單指定到某個 dispatch，若容量不足回傳 False。"""
    current = calculate_capacity(dispatch)
    if current + order.passenger_count > MAX_CAPACITY:
        return False

    do = DispatchOrder(dispatch_id=dispatch.id, order_id=order.id)
    order.dispatch_id = dispatch.id
    db.session.add(do)
    return True


def auto_dispatch(departure_date: str) -> dict:
    """
    自動排車：
    Priority 1: 相同 group_id 的訂單優先同車
    Priority 2: 依建立時間排序
    Priority 3: 優先塞滿車
    - 同一 group 若總人數 > MAX_CAPACITY，不自動排車，回傳警告
    - 同一訂單不拆車
    """
    orders = (
        Order.query
        .filter_by(departure_date=departure_date, payment_status="訂金已確認")
        .filter(Order.dispatch_id.is_(None))
        .order_by(Order.created_at.asc())
        .all()
    )

    if not orders:
        return {"dispatches_created": 0, "orders_assigned": 0, "warnings": []}

    existing_dispatches = (
        Dispatch.query
        .filter_by(departure_date=departure_date)
        .all()
    )

    active = [d for d in existing_dispatches if calculate_capacity(d) < MAX_CAPACITY]

    # 群組分析：計算每個 group 的總人數
    from collections import defaultdict
    group_pax = defaultdict(int)
    group_orders_map = defaultdict(list)
    solo_orders = []

    for o in orders:
        if o.group_id:
            group_pax[o.group_id] += o.passenger_count
            group_orders_map[o.group_id].append(o)
        else:
            solo_orders.append(o)

    warnings = []
    dispatches_created = 0
    orders_assigned = 0
    assigned_ids = set()

    def _get_or_create_vehicle():
        used_vehicle_ids = {d.vehicle_id for d in existing_dispatches}
        return Vehicle.query.filter(Vehicle.id.notin_(used_vehicle_ids)).first()

    def _place_order(order, preferred_dispatch=None):
        nonlocal dispatches_created, orders_assigned
        targets = [preferred_dispatch] if preferred_dispatch else []
        targets += [d for d in active if d is not preferred_dispatch]

        for dispatch in targets:
            if assign_order(dispatch, order):
                orders_assigned += 1
                assigned_ids.add(order.id)
                if calculate_capacity(dispatch) >= MAX_CAPACITY:
                    if dispatch in active:
                        active.remove(dispatch)
                return dispatch

        # 需要新車
        free_vehicle = _get_or_create_vehicle()
        if free_vehicle is None:
            return None
        new_d = create_dispatch(departure_date=departure_date, vehicle_id=free_vehicle.id)
        existing_dispatches.append(new_d)
        nonlocal dispatches_created
        dispatches_created += 1
        if assign_order(new_d, order):
            orders_assigned += 1
            assigned_ids.add(order.id)
            if calculate_capacity(new_d) < MAX_CAPACITY:
                active.append(new_d)
        return new_d

    # Priority 1：處理群組訂單
    for gid, g_orders in group_orders_map.items():
        total = group_pax[gid]
        if total > MAX_CAPACITY:
            warnings.append(f"同行群組 {gid} 共 {total} 人，超過單車容量，請管理員手動安排。")
            continue

        # 找一台有足夠空間的車放整個群組
        placed_dispatch = None
        for d in active:
            if calculate_capacity(d) + total <= MAX_CAPACITY:
                placed_dispatch = d
                break

        if placed_dispatch is None:
            free_vehicle = _get_or_create_vehicle()
            if free_vehicle is None:
                warnings.append(f"同行群組 {gid} 無可用車輛。")
                continue
            placed_dispatch = create_dispatch(departure_date=departure_date, vehicle_id=free_vehicle.id)
            existing_dispatches.append(placed_dispatch)
            dispatches_created += 1
            if calculate_capacity(placed_dispatch) < MAX_CAPACITY:
                active.append(placed_dispatch)

        for o in g_orders:
            if assign_order(placed_dispatch, o):
                orders_assigned += 1
                assigned_ids.add(o.id)
        if calculate_capacity(placed_dispatch) >= MAX_CAPACITY and placed_dispatch in active:
            active.remove(placed_dispatch)

    # Priority 2：處理無群組訂單
    for order in solo_orders:
        if order.id not in assigned_ids:
            _place_order(order)

    db.session.commit()
    return {"dispatches_created": dispatches_created, "orders_assigned": orders_assigned, "warnings": warnings}


def remove_order_from_dispatch(order: Order) -> bool:
    """將訂單從目前的 dispatch 移除。"""
    if order.dispatch_id is None:
        return False

    DispatchOrder.query.filter_by(order_id=order.id).delete()
    order.dispatch_id = None
    db.session.commit()
    return True


def move_order_to_dispatch(order: Order, target_dispatch: Dispatch) -> bool:
    """將訂單從原 dispatch 移至目標 dispatch（drag & drop 用）。"""
    # 先移除
    DispatchOrder.query.filter_by(order_id=order.id).delete()
    order.dispatch_id = None

    # 再指派
    if not assign_order(target_dispatch, order):
        db.session.rollback()
        return False

    db.session.commit()
    return True
