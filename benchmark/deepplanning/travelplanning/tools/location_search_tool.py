"""
Location Search Tool - Query location coordinates (Multilingual)
"""
import os
from typing import Dict, Optional, Union

from .base_travel_tool import BaseTravelTool, register_tool


@register_tool('search_location')
class LocationSearchTool(BaseTravelTool):
    """Tool for querying location latitude and longitude coordinates (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': lambda place: f"未找到地点 {place} 的坐标信息, 请检查：1. 地点名称是否来自其他工具的返回结果; 2. 地点名称是否与工具返回结果保持完全一致，不得缩写、改名或添加额外描述",
            'db_loaded': lambda count, path: f"✓ 地点坐标数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 地点坐标数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': lambda place: f"Coordinate information not found for location {place}, please check: 1. Whether the place name comes from other tool results; 2. Whether the place name is exactly consistent with tool results, no abbreviation, renaming or additional description allowed",
            'db_loaded': lambda count, path: f"✓ Location coordinate database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Location coordinate database not found at {path}",
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
        Execute location coordinate query
        
        Args:
            params: Query parameters containing place_name
            
        Returns:
            JSON string of query results
        """
        params = self._verify_json_format_args(params)
        
        place_name = params.get('place_name')
        
        if self.data is None:
            return self.fields['db_not_loaded']
        
        # Query from CSV database
        col_name = 'poi_name' if 'poi_name' in self.data.columns else 'place_name'
        query_result = self.data[self.data[col_name] == place_name]
        
        if query_result.empty:
            return self.fields['not_found'](place_name)
        
        # Build return result
        row = query_result.iloc[0]
        result = {
            "place_name": row.get('poi_name', row.get('place_name', place_name)),
            "latitude": str(row.get('latitude', '')),
            "longitude": str(row.get('longitude', '')),
        }
        
        return self.format_result_as_json(result)
