
from fastapi import APIRouter

from app.api.v1.endpoints import auth, import_data, materials, products, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(import_data.router, prefix="/import", tags=["import"])
