import json
import os
from typing import Union, Dict, List
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

# List of valid coupons
VALID_COUPONS = [
    "Cross-store: ¥30 off every ¥300",
    "Cross-store: ¥60 off every ¥500",
    "Cross-store: ¥120 off every ¥900",
    "Cross-store: ¥200 off every ¥1,200",
    "Cross-store: ¥300 off every ¥1,500",
    "Same-brand: ¥25 off every ¥200",
    "Same-brand: ¥60 off every ¥400",
    "Same-brand: ¥180 off every ¥1,000",
    "Same-brand: ¥300 off every ¥1,200",
    "VIP: ¥200 off every ¥1,000",
]

@register_tool('filter_by_applicable_coupons')
class FilterByApplicableCouponsTool(BaseShoppingTool):
    """
    Tool to filter products by applicable coupons.
    - If product_ids are provided, filter only those products.
    - If product_ids are not provided, filter the entire product database.
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
        """Load .jsonl format product database"""
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

        coupon_names = params_dict.get('coupon_names', [])
        product_ids = params_dict.get('product_ids')

        if not all(coupon in VALID_COUPONS for coupon in coupon_names):
            return self.format_result_as_json({
                "error": f"Invalid coupon names: {coupon_names}. Valid coupons are: {VALID_COUPONS}"
            })

        if not coupon_names:
            return self.format_result_as_json({"filtered_products_ids": []})

        if product_ids:
            search_space = [self.products_map[pid] for pid in product_ids if pid in self.products_map]
            missing_ids = [pid for pid in product_ids if pid not in self.products_map]
            if missing_ids:
                return self.format_result_as_json({
                    "error": f"Some product_ids not found in database: {missing_ids}"
                })
        else:
            search_space = self.products

        input_coupon_set = set(coupon_names)

        filtered_products = [
            product for product in search_space
            if input_coupon_set.issubset(set(product.get('applicable_coupons', [])))
        ]

        output_data = [product.get("product_id") for product in filtered_products]

        return self.format_result_as_json({"filtered_products_ids": output_data})
