from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.material import Material
from app.models.user import User
from app.schemas.material import MaterialCreate, MaterialResponse, MaterialUpdate

router = APIRouter()


@router.get("", response_model=List[MaterialResponse])
def list_materials(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Material).filter(Material.user_id == current_user.id)
    if search:
        query = query.filter(Material.name.ilike(f"%{search}%"))
    return query.order_by(Material.created_at.desc()).all()


@router.post("", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    data: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    market_price = data.price_amount / data.price_quantity if data.price_quantity else 0.0
    material = Material(
        user_id=current_user.id,
        name=data.name,
        unit=data.unit,
        price_amount=data.price_amount,
        price_quantity=data.price_quantity,
        market_price_per_unit=market_price,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.put("/{material_id}", response_model=MaterialResponse)
def update_material(
    material_id: int,
    data: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    material = (
        db.query(Material)
        .filter(Material.id == material_id, Material.user_id == current_user.id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    if data.name is not None:
        material.name = data.name
    if data.unit is not None:
        material.unit = data.unit
    if data.price_amount is not None:
        material.price_amount = data.price_amount
    if data.price_quantity is not None:
        material.price_quantity = data.price_quantity

    material.market_price_per_unit = (
        material.price_amount / material.price_quantity
        if material.price_quantity
        else 0.0
    )
    db.commit()
    db.refresh(material)
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    material = (
        db.query(Material)
        .filter(Material.id == material_id, Material.user_id == current_user.id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    db.delete(material)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_materials(
    ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Material).filter(Material.user_id == current_user.id)
    if ids:
        query = query.filter(Material.id.in_(ids))
    query.delete(synchronize_session=False)
    db.commit()
