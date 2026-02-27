from typing import List

from pydantic import BaseModel


class ImportMaterialIn(BaseModel):
    name: str
    unit: str
    price_amount: float
    price_quantity: float


class ImportProductLineIn(BaseModel):
    product_name: str
    batch_output_quantity: float
    packaging_cost_per_unit: float
    margin_percentage: float
    material_name: str
    quantity_used: float


class BulkImportRequest(BaseModel):
    materials: List[ImportMaterialIn] = []
    product_lines: List[ImportProductLineIn] = []


class ImportError(BaseModel):
    row: int
    field: str
    message: str


class ImportResult(BaseModel):
    materials_added: int
    materials_duplicated: int
    products_added: int
    products_skipped: int
    errors: List[ImportError]
