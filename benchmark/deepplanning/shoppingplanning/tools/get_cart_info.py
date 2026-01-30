import json
import os
from typing import Union, Dict, List, Optional
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

@register_tool('get_cart_info')
class GetCartInfoTool(BaseShoppingTool):
    """
    Tool for retrieving cart information, including item lists and summary statistics.
    """

    def __init__(self, cfg: Dict = None):
        super().__init__(cfg)
        self.cart_data: Dict = {}
        default_db_path = Path(__file__).parent.parent / 'database' / 'case_0' / 'cart.json'

        if self.cfg and 'database_path' in self.cfg and self.cfg['database_path']:
            db_path = Path(self.cfg['database_path']) / 'cart.json'
        else:
            db_path = default_db_path

        self.db_path = db_path
        self._load_database(db_path)

    def _load_database(self, path: Path):
        """Load the cart data from a JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.cart_data = {
                        "items": [],
                        "summary": {
                            "total_items_count": 0,
                            "total_price": 0.0
                        }
                    }
                    return

                data = json.loads(content)
                if isinstance(data, dict):
                    self.cart_data = data
                    if 'items' not in self.cart_data:
                        self.cart_data['items'] = []
                    if 'summary' not in self.cart_data:
                        self.cart_data['summary'] = {
                            "total_items_count": len(self.cart_data.get('items', [])),
                            "total_price": 0.0
                        }
                else:
                    self.cart_data = {
                        "items": [],
                        "summary": {
                            "total_items_count": 0,
                            "total_price": 0.0
                        }
                    }
        except FileNotFoundError:
            self.cart_data = {
                "items": [],
                "summary": {
                    "total_items_count": 0,
                    "total_price": 0.0
                }
            }
        except json.JSONDecodeError:
            self.cart_data = {
                "items": [],
                "summary": {
                    "total_items_count": 0,
                    "total_price": 0.0
                }
            }
        except Exception:
            self.cart_data = {
                "items": [],
                "summary": {
                    "total_items_count": 0,
                    "total_price": 0.0
                }
            }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Retrieve the current cart information including items and summary.
        """
        try:
            params_dict = self._verify_json_format_args(params) if params else {}
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        self._load_database(self.db_path)
        return self.format_result_as_json(self.cart_data)
