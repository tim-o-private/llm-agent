from core.tools.crud_tool import CRUDTool, CRUDToolInput
from utils.logging_utils import get_logger

logger = get_logger(__name__)

# All CRUD tool configuration is now in the agent_tools table and loaded dynamically.
# No explicit CRUD tool subclasses are needed here. 