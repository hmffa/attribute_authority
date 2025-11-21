# Import all the models, so that Base has them before being
# imported by Alembic
from .base_class import Base  # noqa
from ..models.user import User  # noqa
from ..models.attribute import Attribute  # noqa
from ..models.invitation import Invitation  # noqa
from ..models.admin_role import AdminRole, UserAdminRole  # noqa
from ..models.attribute_privilege_rule import AttributePrivilegeRule, PrivilegeAction, TargetScope
