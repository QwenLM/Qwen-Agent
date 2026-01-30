"""
Road Route Query Tool - Query distance and duration between locations (Multilingual)
"""
import os
from typing import Dict, Optional, Union

from .base_travel_tool import BaseTravelTool, register_tool


@register_tool('query_road_route_info')
class RoadRouteInfoQueryTool(BaseTravelTool):
    """Tool for querying distance and duration information between two locations (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': lambda origin, dest: f"未找到从 {origin} 到 {dest} 的交通信息",
            'coord_not_in_range': lambda coord: f"坐标 {coord} 不在查询范围内，请检查：\n1. 坐标是否源自有效的工具查询结果，而非手动输入或编造；\n2. 坐标数值精度是否与查询结果保持完全一致,6位小数",
            'db_loaded': lambda count, path: f"✓ 交通距离数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 交通距离数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': lambda origin, dest: f"No transportation information found from {origin} to {dest}",
            'coord_not_in_range': lambda coord: f"Coordinate {coord} is not in query range, please check:\n1. Whether coordinate comes from valid tool query result, not manual input or fabrication;\n2. Whether coordinate precision is exactly consistent with query result, 6 decimal places",
            'db_loaded': lambda count, path: f"✓ Road route database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Road route database not found at {path}",
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
        Execute road route query
        
        Args:
            params: Query parameters containing:
                - origin: Coordinate string in format "latitude,longitude"
                - destination: Coordinate string in format "latitude,longitude"
                - mode: Transportation mode (walking, driving, taxi)
            
        Returns:
            JSON string of query results
        """
        params = self._verify_json_format_args(params)
        
        origin = params.get('origin')
        destination = params.get('destination')
        
        if self.data is None:
            return self.fields['db_not_loaded']
        
        # Check if coordinates exist in database
        coord_existence_result = self._check_coordinate_existence(origin, destination)
        if coord_existence_result:
            return coord_existence_result
        
        # Query directly using coordinates
        query_result = self.data[
            (self.data['origin'] == origin) &
            (self.data['destination'] == destination)
        ]
        
        if query_result.empty:
            return self.fields['not_found'](origin, destination)
        
        # Build return result
        row = query_result.iloc[0]
        result = {
            "origin": row.get('origin', origin),
            "destination": row.get('destination', destination),
            "distance_in_meters": int(row.get('distance_meters', 0)),
            "duration_in_minutes": int(row.get('duration_minutes', 0)),
            "cost": int(row.get('cost', 0))
        }
        
        return self.format_result_as_json(result)
    
    def _check_coordinate_existence(self, origin: str, destination: str) -> str:
        """
        Check if coordinates exist in database
        
        Args:
            origin: Origin coordinate string
            destination: Destination coordinate string
            
        Returns:
            Error message string, empty string if no error
        """
        # Get all unique origin and destination coordinates from database
        all_origins = set(self.data['origin'].unique())
        all_destinations = set(self.data['destination'].unique())
        
        # Merge all coordinates
        all_coords = all_origins | all_destinations
        
        # Check origin coordinate
        if origin not in all_coords:
            return self.fields['coord_not_in_range'](origin)
        
        # Check destination coordinate
        if destination not in all_coords:
            return self.fields['coord_not_in_range'](destination)
        
        return ""
