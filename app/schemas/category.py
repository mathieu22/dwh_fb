"""
Schemas Category - Sérialisation et validation des catégories
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class CategorySchema(Schema):
    """Schema pour la lecture d'une catégorie"""
    id = fields.Int(dump_only=True)
    nom = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    ordre = fields.Int()
    is_active = fields.Bool()
    products_count = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    created_by = fields.Int(dump_only=True)
    updated_by = fields.Int(dump_only=True)


class CategoryCreateSchema(Schema):
    """Schema pour la création d'une catégorie"""
    nom = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True, validate=validate.Length(max=500))
    ordre = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)

    @validates('nom')
    def validate_nom_unique(self, value):
        from app.models.category import Category
        existing = Category.query.filter_by(nom=value, is_deleted=False).first()
        if existing:
            raise ValidationError('Une catégorie avec ce nom existe déjà.')


class CategoryUpdateSchema(Schema):
    """Schema pour la mise à jour d'une catégorie"""
    nom = fields.Str(validate=validate.Length(min=1, max=100))
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True, validate=validate.Length(max=500))
    ordre = fields.Int()
    is_active = fields.Bool()
