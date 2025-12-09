"""
Schemas Stock - Sérialisation et validation des stocks
"""
from marshmallow import Schema, fields, validate

from app.models.stock import MovementType


class StockSchema(Schema):
    """Schema pour la lecture d'un stock"""
    id = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    product_nom = fields.Str(dump_only=True)
    quantity = fields.Int()
    seuil_alerte = fields.Int()
    is_low_stock = fields.Bool(dump_only=True)
    is_out_of_stock = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class StockMovementSchema(Schema):
    """Schema pour la lecture d'un mouvement de stock"""
    id = fields.Int(dump_only=True)
    stock_id = fields.Int()
    product_id = fields.Int()
    product_nom = fields.Str(dump_only=True)
    movement_type = fields.Str()
    quantity = fields.Int()
    quantity_before = fields.Int()
    quantity_after = fields.Int()
    reference = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    created_by = fields.Int(dump_only=True)


class StockMovementCreateSchema(Schema):
    """Schema pour la création d'un mouvement de stock"""
    product_id = fields.Int(required=True)
    movement_type = fields.Str(
        required=True,
        validate=validate.OneOf([mt.value for mt in MovementType])
    )
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    reference = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)


class StockUpdateSchema(Schema):
    """Schema pour la mise à jour du seuil d'alerte"""
    seuil_alerte = fields.Int(validate=validate.Range(min=0))
