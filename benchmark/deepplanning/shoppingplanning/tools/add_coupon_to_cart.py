import json
import re
from typing import Union, Dict, Tuple, List
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

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

@register_tool('add_coupon_to_cart')
class AddCouponToCartTool(BaseShoppingTool):
    """
    Tool to add coupons to cart. Validates coupon existence, user ownership, and eligibility based on cart total.
    """

    def __init__(self, cfg: Dict = None):
        super().__init__(cfg)
        self.cart_data: Dict = {}
        self.user_data: Dict = {}

        default_cart_path = Path(__file__).parent.parent / 'database' / 'case_0' / 'cart.json'
        default_user_path = Path(__file__).parent.parent / 'database' / 'case_0' / 'user_info.json'

        if self.cfg and 'database_path' in self.cfg and self.cfg['database_path']:
            cart_path = Path(self.cfg['database_path']) / 'cart.json'
            user_path = Path(self.cfg['database_path']) / 'user_info.json'
        else:
            cart_path = default_cart_path
            user_path = default_user_path

        self.cart_path = cart_path
        self.user_path = user_path
        self._load_cart(cart_path)
        self._load_user(user_path)

    def _load_cart(self, path: Path):
        """Load cart data from JSON file."""
        default_cart = {
            "items": [],
            "used_coupons": [],
            "summary": {"total_items_count": 0, "total_price": 0.0},
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
                    if 'used_coupons' not in self.cart_data:
                        self.cart_data['used_coupons'] = []
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

    def _load_user(self, path: Path):
        """Load user data from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.user_data = {}
                    return

                data = json.loads(content)
                if isinstance(data, dict):
                    self.user_data = data
                else:
                    self.user_data = {}
        except (FileNotFoundError, Exception):
            self.user_data = {}

    def _save_cart(self):
        """Save cart data to file."""
        with open(self.cart_path, 'w', encoding='utf-8') as f:
            json.dump(self.cart_data, f, ensure_ascii=False, indent=4)

    def _parse_coupon(self, coupon_name: str) -> Tuple[float, float]:
        """
        Parse coupon string, return discount and threshold.
        e.g., "Cross-store: ¥30 off every ¥300" -> (30.0, 300.0)
        """
        pattern = r'¥([\d,]+)\s+off\s+every\s+¥([\d,]+)'
        match = re.search(pattern, coupon_name)
        if not match:
            return None, None

        discount_str = match.group(1).replace(',', '')
        threshold_str = match.group(2).replace(',', '')

        try:
            discount = float(discount_str)
            threshold = float(threshold_str)
            return discount, threshold
        except ValueError:
            return None, None

    def _calculate_base_total(self) -> float:
        """Calculate cart's base total price (without any coupon discount)."""
        items = self.cart_data.get('items', [])
        total = 0.0
        for item in items:
            price = float(item.get('price') or item.get('items_price', 0.0))
            quantity = int(item.get('quantity', 0))
            total += price * quantity
        return round(total, 2)

    def _calculate_max_coupon_usage(self, coupon_name: str, base_total: float) -> int:
        """
        Calculate max usage of a coupon based on base_total.
        """
        discount, threshold = self._parse_coupon(coupon_name)
        if discount is None or threshold is None:
            return 0

        if base_total < threshold:
            return 0

        max_usage = int(base_total // threshold)
        return max_usage

    def _calculate_total_discount(self, used_coupons: List[Dict]) -> float:
        """Calculate total discount for all used coupons."""
        total_discount = 0.0
        for coupon in used_coupons:
            coupon_name = coupon.get('coupon_name', '')
            quantity = int(coupon.get('quantity', 0))
            discount, _ = self._parse_coupon(coupon_name)
            if discount is not None:
                total_discount += discount * quantity
        return round(total_discount, 2)

    def _validate_coupon_combination(self, base_total: float, used_coupons: List[Dict]) -> Tuple[bool, str]:
        """
        Check if the combination of coupons is valid.
        Rules:
        1. The same coupon can be used multiple times - the total cart must meet threshold * quantity.
        2. Different coupons can be used at the same time - the cart total must satisfy the sum of all thresholds.
        For example, with cart total >= 2200 you can use both "Same-brand: ¥300 off every ¥1,200" and "VIP: ¥200 off every ¥1,000"
        """
        coupon_usage = {}
        for coupon in used_coupons:
            coupon_name = coupon.get('coupon_name', '')
            quantity = int(coupon.get('quantity', 0))
            if coupon_name not in coupon_usage:
                coupon_usage[coupon_name] = 0
            coupon_usage[coupon_name] += quantity

        total_threshold_required = 0.0
        for coupon_name, total_quantity in coupon_usage.items():
            discount, threshold = self._parse_coupon(coupon_name)
            if discount is None or threshold is None:
                return False, f"Invalid coupon format: {coupon_name}"
            coupon_threshold = threshold * total_quantity
            total_threshold_required += coupon_threshold

        if base_total < total_threshold_required:
            return False, (
                f"Cart total {base_total} is insufficient for this combination of coupons"
                f" (requires at least {total_threshold_required})"
            )
        return True, ""

    def _update_summary(self):
        """Update cart summary statistics, including discount."""
        items = self.cart_data.get('items', [])
        total_items_count = sum(item.get('quantity', 0) for item in items)
        base_total = self._calculate_base_total()
        used_coupons = self.cart_data.get('used_coupons', [])
        total_discount = self._calculate_total_discount(used_coupons)
        final_price = max(0.0, base_total - total_discount)

        if 'summary' not in self.cart_data:
            self.cart_data['summary'] = {}

        self.cart_data['summary']['total_items_count'] = total_items_count
        self.cart_data['summary']['total_price'] = round(final_price, 2)

    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Add coupon to cart.
        Args:
            - coupon_name: Coupon name (required)
            - quantity: Quantity to add (optional, default: 1)
        """
        self._load_cart(self.cart_path)
        self._load_user(self.user_path)

        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        coupon_name = params_dict.get('coupon_name')
        quantity = params_dict.get('quantity', 1)

        if not coupon_name:
            return self.format_result_as_json({
                "error": "coupon_name is required",
            })

        if not isinstance(quantity, (int, float)) or quantity <= 0:
            return self.format_result_as_json({
                "error": "quantity must be a positive number",
            })

        quantity = int(quantity)

        # 1. Validate if coupon exists
        if coupon_name not in VALID_COUPONS:
            return self.format_result_as_json({
                "error": f"Coupon not found: '{coupon_name}'. Valid coupons are: {', '.join(VALID_COUPONS)}",
            })

        # 2. Validate user ownership
        user_coupons = self.user_data.get('coupons', {})
        user_owned_quantity = user_coupons.get(coupon_name, 0)

        # Calculate currently used quantity
        used_coupons = self.cart_data.get('used_coupons', [])
        currently_used = 0
        for coupon in used_coupons:
            if coupon.get('coupon_name') == coupon_name:
                currently_used += int(coupon.get('quantity', 0))

        total_needed = currently_used + quantity

        if total_needed > user_owned_quantity:
            return self.format_result_as_json({
                "error": (
                    f"Insufficient coupon quantity: User owns {user_owned_quantity} of '{coupon_name}', "
                    f"cart already uses {currently_used}, cannot add {quantity} more"
                ),
            })

        # 3. Check VIP status (if VIP coupon)
        if coupon_name.startswith("VIP:"):
            is_vip = self.user_data.get('is_vip', False)
            if not is_vip:
                return self.format_result_as_json({
                    "error": (
                        f"VIP coupon '{coupon_name}' requires VIP status, but user is not a VIP"
                    ),
                })

        # 4. Update or add coupon to used_coupons
        coupon_found = False
        for coupon in used_coupons:
            if coupon.get('coupon_name') == coupon_name:
                coupon['quantity'] = total_needed
                coupon_found = True
                break

        if not coupon_found:
            used_coupons.append({
                "coupon_name": coupon_name,
                "quantity": quantity
            })

        # 5. Check coupon combination validity
        base_total = self._calculate_base_total()
        is_valid, error_msg = self._validate_coupon_combination(base_total, used_coupons)
        if not is_valid:
            # Rollback changes
            if coupon_found:
                for coupon in used_coupons:
                    if coupon.get('coupon_name') == coupon_name:
                        coupon['quantity'] = currently_used
                        break
            else:
                used_coupons.pop()
            self.cart_data['used_coupons'] = used_coupons

            return self.format_result_as_json({
                "error": error_msg,
            })

        # 6. Update summary and persist changes
        self._update_summary()
        self.cart_data['used_coupons'] = [dict(coupon) for coupon in used_coupons]

        try:
            self._save_cart()
        except Exception as e:
            return self.format_result_as_json({
                "error": f"Failed to save cart: {str(e)}",
            })

        return self.format_result_as_json(self.cart_data)
