"""
Base Shopping Tool - Independent Base Tool Class

Framework-agnostic, designed to be compatible with the qwen-agent BaseTool interface.
Intended to be usable both as a standalone open-source tool and easily integrated into the qwen-agent framework.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Type

# Pandas lazy import flag (only imported if CSV is used)
PANDAS_AVAILABLE = None


# ========== Tool Schema Loader ==========

def load_tool_schemas(schema_file: str = 'shopping_tool_schema.json') -> Dict[str, dict]:
    """
    Load shopping tool definitions from a JSON file.

    Args:
        schema_file: Path to the tool definition JSON file (default 'shopping_tool_schema.json')

    Returns:
        Dictionary of tool definitions in the format {tool_name: schema_dict}

    Example:
        >>> schemas = load_tool_schemas()
        >>> product_schema = schemas['search_products']
    """
    # Try provided path; if not found, try relative to module file
    if not os.path.exists(schema_file):
        schema_file = os.path.join(os.path.dirname(__file__), schema_file)

    if not os.path.exists(schema_file):
        return {}

    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            schemas_list = json.load(f)
        schemas = {}
        for schema in schemas_list:
            if 'function' in schema:
                tool_name = schema['function']['name']
                schemas[tool_name] = schema['function']
        return schemas
    except Exception:
        return {}


def get_tool_schema(tool_name: str, schemas: Optional[Dict[str, dict]] = None) -> dict:
    """
    Retrieve the schema for a specific shopping tool.

    Args:
        tool_name: Name of the tool
        schemas: Dictionary of tool definitions (if None, will auto-load)

    Returns:
        The tool's schema dictionary

    Raises:
        KeyError if the tool_name is not found
    """
    if schemas is None:
        schemas = load_tool_schemas()

    if tool_name not in schemas:
        raise KeyError(f"Tool definition for '{tool_name}' not found.")

    return schemas[tool_name]


# Global cache for tool definitions
_TOOL_SCHEMAS_CACHE: Optional[Dict[str, dict]] = None

def get_cached_tool_schemas() -> Dict[str, dict]:
    """Retrieve cached shopping tool definitions (cached on first load)."""
    global _TOOL_SCHEMAS_CACHE
    if _TOOL_SCHEMAS_CACHE is None:
        _TOOL_SCHEMAS_CACHE = load_tool_schemas()
    return _TOOL_SCHEMAS_CACHE


# ========== Tool Registration Mechanism ==========

TOOL_REGISTRY: Dict[str, Type] = {}


def register_tool(name: str, allow_overwrite: bool = False):
    """
    Shopping tool registration decorator.

    Args:
        name: Tool name (must be unique)
        allow_overwrite: Whether to allow overwriting an existing tool with the same name

    Returns:
        Decorator function

    Example:
        @register_tool('search_products')
        class ProductSearchTool(BaseShoppingTool):
            ...
    """
    def decorator(cls):
        if name in TOOL_REGISTRY:
            if allow_overwrite:
                pass  # Allow overwrite, skip warning/notice
            else:
                raise ValueError(
                    f"Tool '{name}' already exists! Please ensure tool name is unique."
                )

        if hasattr(cls, 'name') and cls.name and (cls.name != name):
            raise ValueError(
                f"{cls.__name__}.name='{cls.name}' conflicts with @register_tool(name='{name}')"
            )

        # Set tool name
        cls.name = name

        # Try to load description and parameters from JSON
        try:
            schemas = get_cached_tool_schemas()
            if name in schemas:
                schema = schemas[name]
                cls.description = schema.get('description', '')
                cls.parameters = schema.get('parameters', {})
        except Exception:
            pass  # If loading fails, keep empty; will try again on instantiation

        # Register in global registry
        TOOL_REGISTRY[name] = cls

        return cls

    return decorator


# ========== Base Tool Class ==========

class BaseShoppingTool(ABC):
    """
    Base class for shopping tools, providing all required core features.

    Design principles:
    1. Fully independent, not depending on any frameworks
    2. Implements key qwen-agent BaseTool interface for easy integration
    3. Supports OpenAI Function Calling schema
    4. Provides parameter validation and database support
    5. Loads tool definition from JSON file (default 'shopping_tool_schema.json')

    Usage:
    - Standalone: directly inherit from this class
    - Integration into qwen-agent: via an adapter class

    Example for JSON-based definition:
    ```python
    @register_tool('get_product_details')
    class ProductDetailTool(BaseShoppingTool):
        # Definition will be auto-loaded from shopping_tool_schema.json
        pass
    ```
    """

    # Class attributes - can be defined/overridden by subclasses or loaded from JSON
    name: str = ''
    description: str = ''
    parameters: Union[List[dict], dict] = {}

    def __init__(self, cfg: Optional[Dict] = None):
        """
        Initialize the shopping tool.

        Args:
            cfg: Tool configuration dictionary, may include:
                - database_path: Path to database file
                - load_schema: Whether to load definition from JSON (default True)
        """
        self.cfg = cfg or {}
        self.database_path = None
        self.data = None

        # If class attribute is not defined, try loading from JSON
        if not self.__class__.name and self.cfg.get('load_schema', True):
            self._load_schema_from_json()

        # Use class attributes if not set on the instance
        if not hasattr(self, 'name') or not self.name:
            self.name = self.__class__.name
            self.description = self.__class__.description
            self.parameters = self.__class__.parameters

        if not self.name:
            raise ValueError(
                f"{self.__class__.__name__}.name must be set, "
                f"either by setting the class attribute or using the registration decorator."
            )

        # Parameter format validation (only check if non-empty)
        if isinstance(self.parameters, dict) and self.parameters:
            if not self._is_valid_schema(self.parameters):
                raise ValueError(
                    "parameters must adhere to a valid JSON schema format.\n"
                    f"current parameters: {self.parameters}\n"
                    f"tool name: {self.name}"
                )

    def _load_schema_from_json(self):
        """Load tool definition from shopping_tool_schema.json, if available."""
        # Try to get tool name from registry
        tool_name = None
        for name, cls in TOOL_REGISTRY.items():
            if cls == self.__class__:
                tool_name = name
                break

        if not tool_name:
            # If not in registry, check class attribute
            if hasattr(self.__class__, 'name') and self.__class__.name:
                tool_name = self.__class__.name
            else:
                return  # Cannot find tool name, skip loading

        schemas = get_cached_tool_schemas()

        if tool_name in schemas:
            schema = schemas[tool_name]
            self.name = schema.get('name', tool_name)
            self.description = schema.get('description', '')
            self.parameters = schema.get('parameters', {})

    @staticmethod
    def _is_valid_schema(schema: dict) -> bool:
        """Check if schema is a valid JSON schema object definition."""
        try:
            assert isinstance(schema, dict)
            assert 'type' in schema
            assert schema['type'] == 'object'
            assert 'properties' in schema
            assert 'required' in schema
            assert isinstance(schema['properties'], dict)
            assert isinstance(schema['required'], list)
            return True
        except (AssertionError, KeyError):
            return False

    @abstractmethod
    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Core method for executing the shopping tool.

        Args:
            params: Tool parameters, as either JSON string or dict
            **kwargs: Extra parameters (e.g., user_id, session_id, etc.)

        Returns:
            JSON string of result

        Notes:
        - Must be implemented by subclasses
        - Must return a result in JSON string format
        - Recommended to use format_result_as_json for output formatting
        """
        raise NotImplementedError

    def _verify_json_format_args(self, params: Union[str, dict], strict_json: bool = False) -> dict:
        """
        Validate and parse parameters (for general shopping scenarios).

        Args:
            params: Can be a JSON string or a dict
            strict_json: Whether to strictly require JSON parsing

        Returns:
            Parsed parameter dict

        Raises:
            ValueError: If parameters are invalid or required fields are missing
        """
        if isinstance(params, str):
            try:
                params_json: dict = json.loads(params)
            except json.JSONDecodeError as e:
                raise ValueError(f'Parameters must be a valid JSON string! Error: {e}')
        else:
            params_json: dict = params

        # Check required parameters
        if isinstance(self.parameters, list):
            for param in self.parameters:
                if param.get('required', False):
                    if param['name'] not in params_json:
                        raise ValueError(f"Missing required argument: {param['name']}")
        elif isinstance(self.parameters, dict):
            required_params = self.parameters.get('required', [])
            for param_name in required_params:
                if param_name not in params_json:
                    raise ValueError(f"Missing required argument: {param_name}")

        return params_json

    def load_json_database(self, path: str) -> dict:
        """
        Load a JSON-format product/order database.

        Args:
            path: File path

        Returns:
            Loaded JSON data

        Raises:
            FileNotFoundError if file is not found
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Database file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_csv_database(self, path: str):
        """
        Load product/order database in CSV format (e.g., catalog, inventory).

        Args:
            path: File path

        Returns:
            Loaded DataFrame

        Raises:
            FileNotFoundError if file not found
            ImportError if pandas is not installed or import fails
        """
        global PANDAS_AVAILABLE

        if not os.path.exists(path):
            raise FileNotFoundError(f"Database file not found: {path}")

        # Lazy import pandas (only when needed)
        if PANDAS_AVAILABLE is None:
            try:
                os.environ['OMP_NUM_THREADS'] = '1'
                os.environ['MKL_NUM_THREADS'] = '1'
                os.environ['OPENBLAS_NUM_THREADS'] = '1'

                import pandas as pd
                PANDAS_AVAILABLE = pd
            except Exception as e:
                PANDAS_AVAILABLE = False
                raise ImportError(
                    f"Failed to import pandas: {e}\n"
                    "Please run: pip install pandas\n"
                    "Or use a JSON-format database."
                )

        if PANDAS_AVAILABLE is False:
            raise ImportError(
                "pandas is not installed or failed to import. Cannot load CSV database.\n"
                "Please run: pip install pandas\n"
                "Or use a JSON-format database."
            )

        pd = PANDAS_AVAILABLE
        # Always read as string to avoid loss of precision for fields like price, SKU, etc.
        return pd.read_csv(path, dtype=str)

    def format_result_as_json(self, result: Union[dict, list]) -> str:
        """
        Format the result as a JSON string (ensure non-ASCII chars are not escaped).

        Args:
            result: Result data (dict or list)

        Returns:
            JSON-formatted string
        """
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ========== OpenAI Function Calling Schema Support ==========

    @property
    def openai_schema(self) -> Dict:
        """
        Retrieve the OpenAI Function Calling style schema.

        Returns:
            Full schema as required by OpenAI Function Calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    @property
    def function(self) -> Dict:
        """
        Retrieve function definition (compatible with qwen-agent BaseTool interface).

        Returns:
            Function definition dict
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    def get_schema(self, format: str = "openai") -> Dict:
        """
        Get the tool schema in the specified format.

        Args:
            format: Schema format ('openai', 'anthropic', 'qwen')

        Returns:
            Schema in the corresponding format

        Raises:
            ValueError: If the format is unrecognized
        """
        if format in ("openai", "qwen"):
            return self.openai_schema
        elif format == "anthropic":
            return {
                "name": self.name,
                "description": self.description,
                "input_schema": self.parameters
            }
        else:
            raise ValueError(
                f"Unsupported format: {format}. Supported: openai, anthropic, qwen"
            )

    @classmethod
    def get_openai_schema_from_class(cls) -> Dict:
        """
        Get OpenAI schema directly from the class definition (no instance needed).

        Returns:
            Schema in OpenAI Function Calling format
        """
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": cls.parameters
            }
        }