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
    - 只處理 payment_status='已付款' AND dispatch_id IS NULL
    - 依建立時間排序
    - 同一訂單不拆車
    - 優先塞滿車後再開新車
    回傳 { "dispatches_created": int, "orders_assigned": int }
    """
    # 取出符合條件的訂單，依建立時間排序
    orders = (
        Order.query
        .filter_by(departure_date=departure_date, payment_status="訂金已確認")
        .filter(Order.dispatch_id.is_(None))
        .order_by(Order.created_at.asc())
        .all()
    )

    if not orders:
        return {"dispatches_created": 0, "orders_assigned": 0}

    # 取出該日期可用車輛（已有 dispatch 且尚未滿的車）
    existing_dispatches = (
        Dispatch.query
        .filter_by(departure_date=departure_date)
        .all()
    )

    # 以可用空間排序，優先塞滿
    active = [d for d in existing_dispatches if calculate_capacity(d) < MAX_CAPACITY]

    dispatches_created = 0
    orders_assigned = 0

    for order in orders:
        placed = False

        # 嘗試放入現有 dispatch
        for dispatch in active:
            if assign_order(dispatch, order):
                placed = True
                orders_assigned += 1
                # 若滿了，移出 active
                if calculate_capacity(dispatch) >= MAX_CAPACITY:
                    active.remove(dispatch)
                break

        if not placed:
            # 需要新車：取一台尚未被 dispatch 使用的車輛
            used_vehicle_ids = {d.vehicle_id for d in existing_dispatches}
            free_vehicle = (
                Vehicle.query
                .filter(Vehicle.id.notin_(used_vehicle_ids))
                .first()
            )

            if free_vehicle is None:
                # 沒有可用車輛，略過
                continue

            new_dispatch = create_dispatch(
                departure_date=departure_date,
                vehicle_id=free_vehicle.id,
            )
            existing_dispatches.append(new_dispatch)
            dispatches_created += 1

            if assign_order(new_dispatch, order):
                orders_assigned += 1
                if calculate_capacity(new_dispatch) < MAX_CAPACITY:
                    active.append(new_dispatch)

    db.session.commit()
    return {"dispatches_created": dispatches_created, "orders_assigned": orders_assigned}


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
