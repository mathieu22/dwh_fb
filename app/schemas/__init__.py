"""
Schemas Marshmallow - Sérialisation et validation
"""
from .user import UserSchema, UserCreateSchema, UserUpdateSchema, LoginSchema
from .category import CategorySchema, CategoryCreateSchema, CategoryUpdateSchema
from .product import ProductSchema, ProductCreateSchema, ProductUpdateSchema
from .stock import StockSchema, StockMovementSchema, StockMovementCreateSchema
from .order import OrderSchema, OrderCreateSchema, OrderUpdateSchema, OrderItemSchema

__all__ = [
    'UserSchema', 'UserCreateSchema', 'UserUpdateSchema', 'LoginSchema',
    'CategorySchema', 'CategoryCreateSchema', 'CategoryUpdateSchema',
    'ProductSchema', 'ProductCreateSchema', 'ProductUpdateSchema',
    'StockSchema', 'StockMovementSchema', 'StockMovementCreateSchema',
    'OrderSchema', 'OrderCreateSchema', 'OrderUpdateSchema', 'OrderItemSchema'
]
