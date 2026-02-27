from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProductEntry(Base):
    __tablename__ = "product_entries"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity_str = Column(String(50), nullable=False)


class MaterialSnapshot(Base):
    __tablename__ = "material_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(Integer, nullable=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    price_amount = Column(Float, nullable=False)
    price_quantity = Column(Float, nullable=False)
    market_price_per_unit = Column(Float, nullable=False)
    quantity_used = Column(Float, nullable=False)
    line_cost = Column(Float, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name = Column(String(255), nullable=False, index=True)
    batch_output_quantity = Column(Float, nullable=False)
    packaging_cost_per_unit = Column(Float, nullable=False)
    margin_percentage = Column(Float, nullable=False)
    # Flattened result fields
    total_material_cost = Column(Float, nullable=False)
    cost_per_unit = Column(Float, nullable=False)
    final_cost_per_unit = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    entries = relationship(
        "ProductEntry", cascade="all, delete-orphan", lazy="joined"
    )
    material_snapshots = relationship(
        "MaterialSnapshot", cascade="all, delete-orphan", lazy="joined"
    )

    @property
    def result(self):
        return SimpleNamespace(
            total_material_cost=self.total_material_cost,
            cost_per_unit=self.cost_per_unit,
            final_cost_per_unit=self.final_cost_per_unit,
            selling_price=self.selling_price,
        )
