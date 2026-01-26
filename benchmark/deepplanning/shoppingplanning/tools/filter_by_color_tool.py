import json
import os
from typing import Union, Dict, List
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

@register_tool('filter_by_color')
class FilterByColorTool(BaseShoppingTool):
    """
    Tool to filter products by color names.
    - If product_ids are provided, filter among those products.
    - If product_ids are not provided, filter the entire product database.
    - Color matching is case-insensitive.
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

    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        colors_to_filter = params_dict.get('colors', [])
        product_ids = params_dict.get('product_ids')

        if product_ids:
            search_space = [self.products_map[pid] for pid in product_ids if pid in self.products_map]
            missing_ids = [pid for pid in product_ids if pid not in self.products_map]
            if missing_ids:
                return self.format_result_as_json({
                    "error": f"Some product_ids not found in database: {missing_ids}"
                })
        else:
            search_space = self.products

        color_set = set(c.lower() for c in colors_to_filter)

        filtered_results = [
            p for p in search_space
            if p.get('color', '').lower() in color_set
        ]

        output_data = [
            p.get("product_id") for p in filtered_results
        ]

        return self.format_result_as_json({"filtered_products_ids": output_data})
