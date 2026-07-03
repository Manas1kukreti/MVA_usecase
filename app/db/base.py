"""SQLAlchemy declarative base and metadata."""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass
