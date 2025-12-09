"""
Schemas User - Sérialisation et validation des utilisateurs
"""
from marshmallow import Schema, fields, validate, validates, ValidationError

from app.core.security import UserRoles


class UserSchema(Schema):
    """Schema pour la lecture d'un utilisateur"""
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    nom = fields.Str(required=True)
    prenom = fields.Str(required=True)
    telephone = fields.Str(allow_none=True)
    role = fields.Str(required=True)
    is_active = fields.Bool()
    last_login = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    created_by = fields.Int(dump_only=True)
    updated_by = fields.Int(dump_only=True)


class UserCreateSchema(Schema):
    """Schema pour la création d'un utilisateur"""
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=6))
    nom = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    prenom = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    telephone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    role = fields.Str(validate=validate.OneOf(UserRoles.ALL_ROLES), load_default='simple_utilisateur')
    is_active = fields.Bool(load_default=True)

    @validates('email')
    def validate_email_unique(self, value):
        from app.models.user import User
        existing = User.query.filter_by(email=value, is_deleted=False).first()
        if existing:
            raise ValidationError('Cet email est déjà utilisé.')


class UserUpdateSchema(Schema):
    """Schema pour la mise à jour d'un utilisateur"""
    email = fields.Email()
    password = fields.Str(load_only=True, validate=validate.Length(min=6))
    nom = fields.Str(validate=validate.Length(min=1, max=100))
    prenom = fields.Str(validate=validate.Length(min=1, max=100))
    telephone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    role = fields.Str(validate=validate.OneOf(UserRoles.ALL_ROLES))
    is_active = fields.Bool()


class LoginSchema(Schema):
    """Schema pour le login"""
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
