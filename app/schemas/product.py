"""
Schemas Product - Sérialisation et validation des produits
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class StockInfoSchema(Schema):
    """Schema pour les informations de stock intégrées au produit"""
    quantity = fields.Int()
    is_low_stock = fields.Bool()
    is_out_of_stock = fields.Bool()
    seuil_alerte = fields.Int()


class ProductSchema(Schema):
    """Schema pour la lecture d'un produit"""
    id = fields.Int(dump_only=True)
    nom = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    prix = fields.Float(required=True)
    photo_url = fields.Str(allow_none=True)
    sku = fields.Str(allow_none=True)
    is_active = fields.Bool()
    category_id = fields.Int(required=True)
    category_nom = fields.Str(dump_only=True)
    stock = fields.Nested(StockInfoSchema, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    created_by = fields.Int(dump_only=True)
    updated_by = fields.Int(dump_only=True)


class ProductCreateSchema(Schema):
    """Schema pour la création d'un produit"""
    nom = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    prix = fields.Float(required=True, validate=validate.Range(min=0))
    photo_url = fields.Str(allow_none=True, validate=validate.Length(max=500))
    sku = fields.Str(allow_none=True, validate=validate.Length(max=50))
    is_active = fields.Bool(load_default=True)
    category_id = fields.Int(required=True)
    stock_initial = fields.Int(load_default=0, validate=validate.Range(min=0))
    seuil_alerte = fields.Int(load_default=10, validate=validate.Range(min=0))

    @validates('category_id')
    def validate_category_exists(self, value):
        from app.models.category import Category
        category = Category.query.filter_by(id=value, is_deleted=False).first()
        if not category:
            raise ValidationError('Catégorie non trouvée.')

    @validates('sku')
    def validate_sku_unique(self, value):
        if value:
            from app.models.product import Product
            existing = Product.query.filter_by(sku=value, is_deleted=False).first()
            if existing:
                raise ValidationError('Ce SKU est déjà utilisé.')


class ProductUpdateSchema(Schema):
    """Schema pour la mise à jour d'un produit"""
    nom = fields.Str(validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    prix = fields.Float(validate=validate.Range(min=0))
    photo_url = fields.Str(allow_none=True, validate=validate.Length(max=500))
    sku = fields.Str(allow_none=True, validate=validate.Length(max=50))
    is_active = fields.Bool()
    category_id = fields.Int()
