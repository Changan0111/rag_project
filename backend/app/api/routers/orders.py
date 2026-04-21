from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Order, OrderItem, Product, Logistics, LogisticsTrack, User
from app.schemas import OrderResponse, LogisticsResponse
from app.api.routers.auth import get_current_user, is_admin
from typing import List, Optional

router = APIRouter(prefix="/orders", tags=["订单"])


class OrderWithUserResponse(OrderResponse):
    username: Optional[str] = None


@router.get("", response_model=List[OrderWithUserResponse])
def get_orders(
    status: str = Query(None, description="订单状态筛选"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order)
    
    if not is_admin(current_user):
        query = query.filter(Order.user_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for order in orders:
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        items_data = []
        for item in order_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            items_data.append({
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "product_name": product.name if product else None,
                "created_at": item.created_at
            })
        
        username = None
        if is_admin(current_user):
            user = db.query(User).filter(User.id == order.user_id).first()
            username = user.username if user else None
        
        result.append({
            "id": order.id,
            "order_no": order.order_no,
            "user_id": order.user_id,
            "username": username,
            "total_amount": order.total_amount,
            "status": order.status,
            "payment_method": order.payment_method,
            "payment_time": order.payment_time,
            "created_at": order.created_at,
            "order_items": items_data
        })
    
    return result


@router.get("/{order_no}", response_model=OrderWithUserResponse)
def get_order_detail(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order).filter(Order.order_no == order_no)
    
    if not is_admin(current_user):
        query = query.filter(Order.user_id == current_user.id)
    
    order = query.first()
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    items_data = []
    for item in order_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        items_data.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "product_name": product.name if product else None,
            "created_at": item.created_at
        })
    
    username = None
    if is_admin(current_user):
        user = db.query(User).filter(User.id == order.user_id).first()
        username = user.username if user else None
    
    return {
        "id": order.id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "username": username,
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_time": order.payment_time,
        "created_at": order.created_at,
        "order_items": items_data
    }


@router.get("/{order_no}/logistics", response_model=LogisticsResponse)
def get_order_logistics(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order).filter(Order.order_no == order_no)
    
    if not is_admin(current_user):
        query = query.filter(Order.user_id == current_user.id)
    
    order = query.first()
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    logistics = db.query(Logistics).filter(Logistics.order_id == order.id).first()
    
    if not logistics:
        raise HTTPException(status_code=404, detail="暂无物流信息")
    
    tracks = db.query(LogisticsTrack).filter(
        LogisticsTrack.logistics_id == logistics.id
    ).order_by(LogisticsTrack.track_time.desc()).all()
    
    return {
        "id": logistics.id,
        "order_id": logistics.order_id,
        "tracking_no": logistics.tracking_no,
        "carrier": logistics.carrier,
        "status": logistics.status,
        "current_location": logistics.current_location,
        "estimated_arrival": logistics.estimated_arrival,
        "created_at": logistics.created_at,
        "tracks": [{
            "id": t.id,
            "logistics_id": t.logistics_id,
            "location": t.location,
            "status": t.status,
            "track_time": t.track_time,
            "created_at": t.created_at
        } for t in tracks]
    }
