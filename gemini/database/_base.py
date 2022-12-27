from sqlalchemy.orm.decl_api import DeclarativeMeta, registry

mapper_registry = registry()


class Base(metaclass=DeclarativeMeta):
    __abstract__ = True

    registry = mapper_registry
    metadata = mapper_registry.metadata

    __init__ = mapper_registry.constructor
    __tablename__: str
