# Import all the models, so that Base has them before being
# imported by Alembic
from .base_class import Base  # noqa
from ..models.user import User  # noqa
from ..models.user_attribute import UserAttribute  # noqa
from ..models.invitation import Invitation  # noqa
