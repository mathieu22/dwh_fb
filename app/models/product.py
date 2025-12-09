"""
Modèle Product - Articles/Produits avec audit
"""
from decimal import Decimal

from app.extensions import db
from app.core.audit_mixin import AuditMixin, SoftDeleteMixin, register_audit_listeners


class Product(db.Model, AuditMixin, SoftDeleteMixin):
    """
    Modèle Produit/Article avec historisation complète.
    """
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    prix = db.Column(db.Numeric(10, 2), nullable=False)
    photo_url = db.Column(db.String(500), nullable=True)
    sku = db.Column(db.String(50), unique=True, nullable=True)  # Code produit unique
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Foreign Keys
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)

    # Relations
    stock = db.relationship('Stock', backref='product', uselist=False, lazy='joined')
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic')

    def __repr__(self):
        return f'<Product {self.nom}>'

    @property
    def current_stock(self):
        """Retourne le stock actuel"""
        if self.stock:
            return self.stock.quantity
        return 0

    @property
    def is_low_stock(self):
        """Vérifie si le stock est faible"""
        if self.stock:
            return self.stock.quantity <= self.stock.seuil_alerte
        return True

    @property
    def is_out_of_stock(self):
        """Vérifie si le produit est en rupture"""
        return self.current_stock <= 0

    def to_dict(self, include_stock=True):
        """Conversion en dictionnaire"""
        data = {
            'id': self.id,
            'nom': self.nom,
            'description': self.description,
            'prix': float(self.prix) if self.prix else 0,
            'photo_url': self.photo_url,
            'sku': self.sku,
            'is_active': self.is_active,
            'category_id': self.category_id,
            'category_nom': self.category.nom if self.category else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }

        if include_stock:
            data['stock'] = {
                'quantity': self.current_stock,
                'is_low_stock': self.is_low_stock,
                'is_out_of_stock': self.is_out_of_stock,
                'seuil_alerte': self.stock.seuil_alerte if self.stock else 10
            }

        return data


# Enregistrer les listeners d'audit
register_audit_listeners(Product)
