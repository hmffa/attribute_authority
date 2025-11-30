import re
from typing import Any
from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base:
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        # Regex to convert CamelCase to snake_case
        # It inserts an underscore before any capital letter that is not at the start of the string
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name + "s"