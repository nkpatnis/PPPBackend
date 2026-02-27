from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.product import MaterialSnapshot, Product, ProductEntry
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductListItem,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()


def _build_entries_and_snapshots(data: ProductCreate):
    entries = [
        ProductEntry(material_id=e.material_id, quantity_str=e.quantity_str)
        for e in data.entries
    ]
    snapshots = [
        MaterialSnapshot(
            material_id=s.material_id,
            name=s.name,
            unit=s.unit,
            price_amount=s.price_amount,
            price_quantity=s.price_quantity,
            market_price_per_unit=s.market_price_per_unit,
            quantity_used=s.quantity_used,
            line_cost=s.line_cost,
        )
        for s in data.material_snapshots
    ]
    return entries, snapshots


@router.get("", response_model=List[ProductListItem])
def list_products(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Product).filter(Product.user_id == current_user.id)
    if search:
        query = query.filter(Product.product_name.ilike(f"%{search}%"))
    return query.order_by(Product.updated_at.desc()).all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entries, snapshots = _build_entries_and_snapshots(data)
    product = Product(
        user_id=current_user.id,
        product_name=data.product_name,
        batch_output_quantity=data.batch_output_quantity,
        packaging_cost_per_unit=data.packaging_cost_per_unit,
        margin_percentage=data.margin_percentage,
        total_material_cost=data.result.total_material_cost,
        cost_per_unit=data.result.cost_per_unit,
        final_cost_per_unit=data.result.final_cost_per_unit,
        selling_price=data.result.selling_price,
        entries=entries,
        material_snapshots=snapshots,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.product_name is not None:
        product.product_name = data.product_name
    if data.batch_output_quantity is not None:
        product.batch_output_quantity = data.batch_output_quantity
    if data.packaging_cost_per_unit is not None:
        product.packaging_cost_per_unit = data.packaging_cost_per_unit
    if data.margin_percentage is not None:
        product.margin_percentage = data.margin_percentage
    if data.result is not None:
        product.total_material_cost = data.result.total_material_cost
        product.cost_per_unit = data.result.cost_per_unit
        product.final_cost_per_unit = data.result.final_cost_per_unit
        product.selling_price = data.result.selling_price
    if data.entries is not None:
        for entry in list(product.entries):
            db.delete(entry)
        product.entries = [
            ProductEntry(material_id=e.material_id, quantity_str=e.quantity_str)
            for e in data.entries
        ]
    if data.material_snapshots is not None:
        for snap in list(product.material_snapshots):
            db.delete(snap)
        product.material_snapshots = [
            MaterialSnapshot(
                material_id=s.material_id,
                name=s.name,
                unit=s.unit,
                price_amount=s.price_amount,
                price_quantity=s.price_quantity,
                market_price_per_unit=s.market_price_per_unit,
                quantity_used=s.quantity_used,
                line_cost=s.line_cost,
            )
            for s in data.material_snapshots
        ]

    product.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_products(
    ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Product).filter(Product.user_id == current_user.id)
    if ids:
        query = query.filter(Product.id.in_(ids))
    for product in query.all():
        db.delete(product)
    db.commit()
