import json
import os
from typing import Union, Dict, List, Any
from functools import reduce
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path


@register_tool('filter_by_range')
class FilterByRangeTool(BaseShoppingTool):
    """
    Tool to filter products by a numeric value range.
    - If product_ids are provided, filter among those products.
    - If not provided, filter the entire product database.
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
        """Load .jsonl format product database."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        product = json.loads(line)
                        self.products.append(product)
                        self.products_map[product['product_id']] = product
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _get_nested_value(self, obj: Dict, key_path: str) -> Any:
        """
        Safely get values from nested dictionaries, e.g. 'sales_volume.monthly'
        """
        try:
            return reduce(
                lambda d, key: d.get(key) if isinstance(d, dict) else None,
                key_path.split('.'),
                obj
            )
        except (TypeError, AttributeError):
            return None

    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        condition_key = params_dict.get('condition_key')
        operator = params_dict.get('operator')
        value = params_dict.get('value')
        product_ids = params_dict.get('product_ids')

        if not all([condition_key, operator, value is not None]):
            return self.format_result_as_json({
                "error": "Missing required parameters: condition_key, operator, or value."
            })

        if product_ids:
            search_space = [self.products_map[pid] for pid in product_ids if pid in self.products_map]
            missing_ids = [pid for pid in product_ids if pid not in self.products_map]
            if missing_ids:
                return self.format_result_as_json({
                    "error": f"Some product_ids not found in database: {missing_ids}"
                })
        else:
            search_space = self.products

        filtered_ids = []
        for p in search_space:
            product_value = self._get_nested_value(p, condition_key)

            # Make sure values are comparable
            if product_value is None:
                raise ValueError("condition_key cannot be found in product data, please check again.")

            try:
                # Try to convert both values to float for comparison
                product_value_f = float(product_value)
                value_f = float(value)
                match = False
                if operator == '>' and product_value_f > value_f:
                    match = True
                elif operator == '>=' and product_value_f >= value_f:
                    match = True
                elif operator == '<' and product_value_f < value_f:
                    match = True
                elif operator == '<=' and product_value_f <= value_f:
                    match = True
                elif operator == '==' and product_value_f == value_f:
                    match = True

                if match:
                    filtered_ids.append(p)
            except (ValueError, TypeError):
                # Skip values if they cannot be cast to float for comparison
                continue

        output_data = [p.get("product_id") for p in filtered_ids]

        return self.format_result_as_json({"filtered_products_ids": output_data})

