import json
import os
from typing import Union, Dict, List, Any
from functools import reduce
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

@register_tool('sort_products')
class SortProductsTool(BaseShoppingTool):
    """
    A tool to sort a list of products according to a specified attribute.
    - If product_ids are provided, only those products are sorted.
    - If product_ids are not provided, the entire product database is sorted.
    - The 'sort_by' and 'order' inputs are case-insensitive.
    """

    def __init__(self, cfg: Dict = None):
        super().__init__(cfg)
        self.products: List[Dict] = []
        self.products_map: Dict[str, Dict] = {}

        default_db_path = os.path.join(
            os.path.dirname(__file__), '..', 'database', 'case_0', 'products.jsonl'
        )

        if self.cfg and 'database_path' in self.cfg and self.cfg['database_path']:
            db_path = Path(self.cfg['database_path']) / 'products.jsonl'
        else:
            db_path = default_db_path

        self._load_database(db_path)

    def _load_database(self, path: str):
        """Load the .jsonl format product database."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        product = json.loads(line)
                        self.products.append(product)
                        self.products_map[product['product_id']] = product
        except Exception:
            pass

    def _get_nested_value(self, obj: Dict, key_path: str) -> Any:
        """Safely fetch a value from a nested dictionary given a dot-separated key path, e.g. 'sales_volume.monthly'."""
        try:
            return reduce(lambda d, key: d.get(key) if isinstance(d, dict) else None, key_path.split('.'), obj)
        except (TypeError, AttributeError):
            return None

    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        sort_by = params_dict.get('sort_by', '').lower()
        order = params_dict.get('order', 'desc').lower()
        product_ids = params_dict.get('product_ids')

        if not sort_by:
            return self.format_result_as_json({"error": "Missing required parameter: sort_by."})
        if order not in ['asc', 'desc']:
            return self.format_result_as_json({"error": f"Invalid value for 'order': '{params_dict.get('order')}'. Must be 'asc' or 'desc'."})

        if product_ids:
            search_space = [self.products_map[pid] for pid in product_ids if pid in self.products_map]
        else:
            search_space = self.products

        if not search_space:
            return self.format_result_as_json({"sorted_product_ids": []})

        try:
            first_product_value = self._get_nested_value(search_space[0], sort_by)
            if first_product_value is None:
                raise ValueError(f"Sort key '{sort_by}' cannot be found in product data or is null. Please check again.")

            def sort_key_func(product):
                val = self._get_nested_value(product, sort_by)
                if isinstance(val, str):
                    return val.lower()
                if isinstance(val, (int, float)):
                    return val
                if order == 'desc':
                    return -float('inf')
                else:
                    return float('inf')

            sorted_products = sorted(
                search_space,
                key=sort_key_func,
                reverse=(order == 'desc')
            )
            sorted_ids = [p['product_id'] for p in sorted_products]

        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})
        except Exception as e:
            return self.format_result_as_json({"error": f"An error occurred during sorting on key '{sort_by}': {e}"})

        return self.format_result_as_json({"sorted_product_ids": sorted_ids})
