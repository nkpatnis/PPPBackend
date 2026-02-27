from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CalculationResultSchema(BaseModel):
    total_material_cost: float
    cost_per_unit: float
    final_cost_per_unit: float
    selling_price: float

    model_config = {"from_attributes": True}


class ProductEntryCreate(BaseModel):
    material_id: Optional[int] = None
    quantity_str: str


class ProductEntryResponse(BaseModel):
    id: int
    product_id: int
    material_id: Optional[int]
    quantity_str: str

    model_config = {"from_attributes": True}


class MaterialSnapshotCreate(BaseModel):
    material_id: Optional[int] = None
    name: str
    unit: str
    price_amount: float
    price_quantity: float
    market_price_per_unit: float
    quantity_used: float
    line_cost: float


class MaterialSnapshotResponse(BaseModel):
    id: int
    product_id: int
    material_id: Optional[int]
    name: str
    unit: str
    price_amount: float
    price_quantity: float
    market_price_per_unit: float
    quantity_used: float
    line_cost: float

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    product_name: str
    entries: List[ProductEntryCreate]
    batch_output_quantity: float
    packaging_cost_per_unit: float
    margin_percentage: float
    result: CalculationResultSchema
    material_snapshots: List[MaterialSnapshotCreate]


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    entries: Optional[List[ProductEntryCreate]] = None
    batch_output_quantity: Optional[float] = None
    packaging_cost_per_unit: Optional[float] = None
    margin_percentage: Optional[float] = None
    result: Optional[CalculationResultSchema] = None
    material_snapshots: Optional[List[MaterialSnapshotCreate]] = None


class ProductResponse(BaseModel):
    id: int
    product_name: str
    entries: List[ProductEntryResponse]
    batch_output_quantity: float
    packaging_cost_per_unit: float
    margin_percentage: float
    result: CalculationResultSchema
    material_snapshots: List[MaterialSnapshotResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    id: int
    product_name: str
    selling_price: float
    final_cost_per_unit: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
