from collections import defaultdict

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.material import Material
from app.models.product import MaterialSnapshot, Product, ProductEntry
from app.models.user import User
from app.schemas.import_schema import BulkImportRequest, ImportError, ImportResult

router = APIRouter()


@router.post("", response_model=ImportResult, status_code=status.HTTP_200_OK)
def bulk_import(
    data: BulkImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    errors: list[ImportError] = []
    materials_added = 0
    materials_duplicated = 0
    products_added = 0
    products_skipped = 0

    # Phase 1: Import materials — skip case-insensitive duplicates
    existing_materials = (
        db.query(Material).filter(Material.user_id == current_user.id).all()
    )
    name_to_material: dict[str, Material] = {
        m.name.lower(): m for m in existing_materials
    }

    for mat in data.materials:
        key = mat.name.lower()
        if key in name_to_material:
            materials_duplicated += 1
            continue
        market_price = mat.price_amount / mat.price_quantity if mat.price_quantity else 0.0
        new_mat = Material(
            user_id=current_user.id,
            name=mat.name,
            unit=mat.unit,
            price_amount=mat.price_amount,
            price_quantity=mat.price_quantity,
            market_price_per_unit=market_price,
        )
        db.add(new_mat)
        name_to_material[key] = new_mat
        materials_added += 1

    # Flush to assign IDs to newly added materials before referencing them
    db.flush()

    # Phase 2: Import products — group lines by product_name
    groups: dict[str, list] = defaultdict(list)
    for line in data.product_lines:
        groups[line.product_name].append(line)

    for row_offset, (product_name, lines) in enumerate(groups.items()):
        first = lines[0]
        entries = []
        snapshots = []
        total_material_cost = 0.0
        skip = False

        for line_idx, line in enumerate(lines):
            mat = name_to_material.get(line.material_name.lower())
            if not mat:
                errors.append(
                    ImportError(
                        row=row_offset + line_idx,
                        field="material_name",
                        message=f"Material '{line.material_name}' not found",
                    )
                )
                skip = True
                continue

            market_price = (
                mat.price_amount / mat.price_quantity if mat.price_quantity else 0.0
            )
            line_cost = market_price * line.quantity_used
            total_material_cost += line_cost

            entries.append(
                ProductEntry(
                    material_id=mat.id,
                    quantity_str=str(line.quantity_used),
                )
            )
            snapshots.append(
                MaterialSnapshot(
                    material_id=mat.id,
                    name=mat.name,
                    unit=mat.unit,
                    price_amount=mat.price_amount,
                    price_quantity=mat.price_quantity,
                    market_price_per_unit=market_price,
                    quantity_used=line.quantity_used,
                    line_cost=line_cost,
                )
            )

        if skip:
            products_skipped += 1
            continue

        batch_output = first.batch_output_quantity
        packaging = first.packaging_cost_per_unit
        margin = first.margin_percentage
        cost_per_unit = total_material_cost / batch_output if batch_output else 0.0
        final_cost_per_unit = cost_per_unit + packaging
        selling_price = final_cost_per_unit * (1 + margin / 100.0)

        product = Product(
            user_id=current_user.id,
            product_name=product_name,
            batch_output_quantity=batch_output,
            packaging_cost_per_unit=packaging,
            margin_percentage=margin,
            total_material_cost=total_material_cost,
            cost_per_unit=cost_per_unit,
            final_cost_per_unit=final_cost_per_unit,
            selling_price=selling_price,
            entries=entries,
            material_snapshots=snapshots,
        )
        db.add(product)
        products_added += 1

    db.commit()

    return ImportResult(
        materials_added=materials_added,
        materials_duplicated=materials_duplicated,
        products_added=products_added,
        products_skipped=products_skipped,
        errors=errors,
    )
