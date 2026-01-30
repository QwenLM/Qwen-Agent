import json
from typing import Union, Dict
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

@register_tool('delete_product_from_cart')
class DeleteProductFromCartTool(BaseShoppingTool):
    """
    Tool to remove products from cart. Validates product existence and cart presence.
    """

    def __init__(self, cfg: Dict = None):
        super().__init__(cfg)
        self.cart_data: Dict = {}
        self.products_map: Dict[str, Dict] = {}

        default_cart_path = Path(__file__).parent.parent / 'database' / 'case_0' / 'cart.json'
        default_products_path = Path(__file__).parent.parent / 'database' / 'case_0' / 'products.jsonl'

        if self.cfg and 'database_path' in self.cfg and self.cfg['database_path']:
            cart_path = Path(self.cfg['database_path']) / 'cart.json'
            products_path = Path(self.cfg['database_path']) / 'products.jsonl'
        else:
            cart_path = default_cart_path
            products_path = default_products_path

        self.cart_path = cart_path
        self._load_cart(cart_path)
        self._load_products(products_path)

    def _load_cart(self, path: Path):
        """Load cart data from JSON file."""
        default_cart = {
            "items": [],
            "summary": {"total_items_count": 0, "total_price": 0.0}
        }
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.cart_data = default_cart
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
                    self.cart_data = default_cart
        except FileNotFoundError:
            self.cart_data = default_cart
        except (json.JSONDecodeError, Exception):
            self.cart_data = default_cart

    def _load_products(self, path: Path):
        """Load products from JSONL file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        product = json.loads(line)
                        self.products_map[product['product_id']] = product
        except (FileNotFoundError, Exception):
            pass

    def _save_cart(self):
        """Save cart data to file."""
        with open(self.cart_path, 'w', encoding='utf-8') as f:
            json.dump(self.cart_data, f, ensure_ascii=False, indent=4)

    def _update_summary(self):
        """Update cart summary statistics."""
        items = self.cart_data.get('items', [])
        total_items_count = sum(item.get('quantity', 0) for item in items)
        total_price = sum(item.get('price', 0.0) * item.get('quantity', 0) for item in items)

        if 'summary' not in self.cart_data:
            self.cart_data['summary'] = {}

        self.cart_data['summary']['total_items_count'] = total_items_count
        self.cart_data['summary']['total_price'] = round(total_price, 2)

    def _cleanup_zero_quantity_items(self):
        """Remove items with quantity 0 from cart."""
        items = self.cart_data.get('items', [])
        self.cart_data['items'] = [item for item in items if item.get('quantity', 0) > 0]

    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Remove product from cart.
        Args:
            - product_id: Product ID (required)
            - quantity: Quantity to remove (optional, default: 1)
        """
        # Reload cart data to ensure the latest state
        self._load_cart(self.cart_path)

        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        product_id = params_dict.get('product_id')
        quantity = params_dict.get('quantity', 1)

        if not product_id:
            return self.format_result_as_json({
                "error": "product_id is required"
            })

        if not isinstance(quantity, (int, float)) or quantity <= 0:
            return self.format_result_as_json({
                "error": "quantity must be a positive number"
            })

        quantity = int(quantity)

        if product_id not in self.products_map:
            return self.format_result_as_json({
                "error": f"Product not found: product_id '{product_id}'"
            })

        items = self.cart_data.get('items', [])
        existing_item_index = -1

        for idx, item in enumerate(items):
            if item.get('product_id') == product_id:
                existing_item_index = idx
                break

        if existing_item_index < 0:
            return self.format_result_as_json({
                "error": f"Product not in cart: product_id '{product_id}'"
            })

        existing_item = items[existing_item_index]
        existing_quantity = existing_item.get('quantity', 0)

        new_quantity = max(0, existing_quantity - quantity)
        existing_item['quantity'] = new_quantity

        if new_quantity == 0:
            items.pop(existing_item_index)
        else:
            items[existing_item_index] = existing_item

        self.cart_data['items'] = items
        self._cleanup_zero_quantity_items()
        self._update_summary()

        try:
            self._save_cart()
        except Exception as e:
            return self.format_result_as_json({
                "error": f"Failed to save cart: {str(e)}"
            })

        return self.format_result_as_json(self.cart_data)