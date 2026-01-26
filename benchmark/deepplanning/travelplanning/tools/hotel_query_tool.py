"""
Hotel Query Tool - Query hotel information (Multilingual)
"""
import os
from typing import Dict, Optional, Union

from .base_travel_tool import BaseTravelTool, register_tool


@register_tool('query_hotel_info')
class HotelQueryTool(BaseTravelTool):
    """Tool for querying hotel information (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': lambda dest, checkin, checkout: f"未找到满足条件的 {dest} 在 {checkin} 到 {checkout} 的酒店信息,请检查参数信息或减少约束条件",
            'db_loaded': lambda count, path: f"✓ 酒店数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 酒店数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': lambda dest, checkin, checkout: f"No hotel information found in {dest} from {checkin} to {checkout}, please check parameters or reduce constraints",
            'db_loaded': lambda count, path: f"✓ Hotel database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Hotel database not found at {path}",
        }
    }
    
    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.database_path = cfg.get('database_path') if cfg else None
        
        # Get language-specific fields
        self.fields = self.LANG_FIELDS.get(self.language, self.LANG_FIELDS['en'])
        
        if self.database_path and os.path.exists(self.database_path):
            self.data = self.load_csv_database(self.database_path)
            print(self.fields['db_loaded'](len(self.data), self.database_path))
        else:
            if self.database_path:
                print(self.fields['db_not_found'](self.database_path))
            self.data = None
    
    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Execute hotel query
        
        Args:
            params: Query parameters containing destination, checkinDate, checkoutDate,
                   and optional parameters: poiName, hotelTags, hotelStar, hotelBrands
            
        Returns:
            JSON string of query results
        """
        params = self._verify_json_format_args(params)
        
        destination = params.get('destination')
        checkin_date = params.get('checkinDate')
        checkout_date = params.get('checkoutDate')
        hotel_star = params.get('hotelStar', '')
        hotel_brands = params.get('hotelBrands', '')
        
        if self.data is None:
            return self.fields['db_not_loaded']
        
        # Query from CSV database - return all data without city filtering
        query_result = self.data
        
        # Filter by optional parameters
        if hotel_star:
            query_result = query_result[query_result['hotel_star'] == hotel_star]
        if hotel_brands:
            query_result = query_result[query_result['brand'] == hotel_brands]
        
        if query_result.empty:
            return self.fields['not_found'](destination, checkin_date, checkout_date)
        
        def is_nan(v):
            try:
                return v != v
            except Exception:
                return False

        def to_str(v: object) -> str:
            if v is None:
                return ''
            if is_nan(v):
                return ''
            return str(v)

        # Build result list
        results = []
        for _, row in query_result.iterrows():
            tags_field = row.get('tags', None)
            tags_list = []
            if isinstance(tags_field, str) and tags_field.strip():
                tags_list = tags_field.split('|')

            stock_raw = row.get('stock', 0)
            try:
                stock_val = int(float(stock_raw)) if stock_raw not in (None, '') else 0
            except Exception:
                stock_val = 0

            result = {
                "name": to_str(row.get('name', '')),
                "address": to_str(row.get('address', '')),
                "latitude": to_str(row.get('latitude', '')),
                "longitude": to_str(row.get('longitude', '')),
                "decorationTime": to_str(row.get('decoration_time', '')),
                "hotelStar": to_str(row.get('hotel_star', '')),
                "price": to_str(row.get('price', '')),
                "score": to_str(row.get('score', '')),
                "brand": to_str(row.get('brand', '')),
            }
            
            # If CSV has services field, add to result
            if 'services' in row.index:
                services_field = row.get('services', None)
                if services_field and isinstance(services_field, str) and services_field.strip():
                    # services field separated by semicolon, convert to list
                    services_list = services_field.split(';')
                    result['services'] = services_list
            
            results.append(result)
        
        return self.format_result_as_json(results)
