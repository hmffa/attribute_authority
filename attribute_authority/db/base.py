# Import all the models, so that Base has them before being
# imported by Alembic
from .base_class import Base  # noqa
from ..models.user import User  # noqa
from ..models.attribute import Attribute  # noqa
from ..models.invitation import Invitation  # noqa
from ..models.privilege import Privilege  # noqa
from ..models.user_attribute_value import UserAttributeValue  # noqa

