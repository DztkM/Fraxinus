from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import UserDefinedType

class LtreeType(UserDefinedType):
    """
    PostgreSQL LTREE custom type.
    """
    cache_ok = True

    def get_col_spec(self, **kw):
        return "ltree"

class Base(DeclarativeBase):
    pass
