"""
Schemas Order - Sérialisation et validation des commandes
"""
from marshmallow import Schema, fields, validate, validates, ValidationError

from app.models.order import OrderStatus


class OrderItemSchema(Schema):
    """Schema pour une ligne de commande"""
    id = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    product_nom = fields.Str(dump_only=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    prix_unitaire = fields.Float(dump_only=True)
    prix_total = fields.Float(dump_only=True)


class OrderItemCreateSchema(Schema):
    """Schema pour créer une ligne de commande"""
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))

    @validates('product_id')
    def validate_product_exists(self, value):
        from app.models.product import Product
        product = Product.query.filter_by(id=value, is_deleted=False).first()
        if not product:
            raise ValidationError('Produit non trouvé.')


class OrderSchema(Schema):
    """Schema pour la lecture d'une commande"""
    id = fields.Int(dump_only=True)
    numero = fields.Str(dump_only=True)
    status = fields.Str()
    client_nom = fields.Str(required=True)
    client_telephone = fields.Str(allow_none=True)
    client_email = fields.Email(allow_none=True)
    adresse_livraison = fields.Str(allow_none=True)
    montant_total = fields.Float()
    montant_remise = fields.Float()
    montant_livraison = fields.Float()
    date_confirmation = fields.DateTime(dump_only=True)
    date_preparation = fields.DateTime(dump_only=True)
    date_expedition = fields.DateTime(dump_only=True)
    date_livraison = fields.DateTime(dump_only=True)
    notes = fields.Str(allow_none=True)
    user_id = fields.Int()
    livreur_id = fields.Int(allow_none=True)
    items = fields.Nested(OrderItemSchema, many=True)
    items_count = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    created_by = fields.Int(dump_only=True)
    updated_by = fields.Int(dump_only=True)


class OrderCreateSchema(Schema):
    """Schema pour la création d'une commande"""
    client_nom = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    client_telephone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    client_email = fields.Email(allow_none=True)
    adresse_livraison = fields.Str(allow_none=True)
    montant_remise = fields.Float(load_default=0, validate=validate.Range(min=0))
    montant_livraison = fields.Float(load_default=0, validate=validate.Range(min=0))
    notes = fields.Str(allow_none=True)
    items = fields.Nested(OrderItemCreateSchema, many=True, required=True, validate=validate.Length(min=1))


class OrderUpdateSchema(Schema):
    """Schema pour la mise à jour d'une commande"""
    client_nom = fields.Str(validate=validate.Length(min=1, max=200))
    client_telephone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    client_email = fields.Email(allow_none=True)
    adresse_livraison = fields.Str(allow_none=True)
    montant_remise = fields.Float(validate=validate.Range(min=0))
    montant_livraison = fields.Float(validate=validate.Range(min=0))
    notes = fields.Str(allow_none=True)
    livreur_id = fields.Int(allow_none=True)


class OrderStatusUpdateSchema(Schema):
    """Schema pour le changement de statut"""
    status = fields.Str(
        required=True,
        validate=validate.OneOf([s.value for s in OrderStatus])
    )
