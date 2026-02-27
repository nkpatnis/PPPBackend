from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MaterialCreate(BaseModel):
    name: str
    unit: str
    price_amount: float
    price_quantity: float


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    price_amount: Optional[float] = None
    price_quantity: Optional[float] = None


class MaterialResponse(BaseModel):
    id: int
    name: str
    unit: str
    price_amount: float
    price_quantity: float
    market_price_per_unit: float
    created_at: datetime

    model_config = {"from_attributes": True}
