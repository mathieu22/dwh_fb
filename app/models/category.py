"""
Modèle Category - Catégories de produits avec audit
"""
from app.extensions import db
from app.core.audit_mixin import AuditMixin, SoftDeleteMixin, register_audit_listeners


class Category(db.Model, AuditMixin, SoftDeleteMixin):
    """
    Modèle Catégorie avec historisation complète.
    """
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    ordre = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relations
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.nom}>'

    def to_dict(self):
        """Conversion en dictionnaire"""
        return {
            'id': self.id,
            'nom': self.nom,
            'description': self.description,
            'image_url': self.image_url,
            'ordre': self.ordre,
            'is_active': self.is_active,
            'products_count': self.products.filter_by(is_deleted=False).count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }


# Enregistrer les listeners d'audit
register_audit_listeners(Category)
