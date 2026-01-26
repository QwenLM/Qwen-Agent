import json
import os
from typing import Union, Dict, List
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

@register_tool('get_product_details')
class GetProductDetailsTool(BaseShoppingTool):
    """
    Tool to retrieve complete product details given one or more product_ids.
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
        """Load product database in .jsonl format."""
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
        """
        Core logic for retrieving product details.
        """
        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        product_ids = params_dict.get('product_ids', [])

        if not product_ids:
            return self.format_result_as_json({"products": []})

        # Find all requested products that exist in the database
        detailed_products = [
            self.products_map[pid] for pid in product_ids if pid in self.products_map
        ]
        
        return self.format_result_as_json({"products": detailed_products})

