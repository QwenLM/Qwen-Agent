"""
Restaurant Query Tool - Recommend and query restaurant information (Multilingual)
"""
import os
from typing import Dict, Optional, Union

from .base_travel_tool import BaseTravelTool, register_tool


@register_tool('recommend_restaurants')
class RestaurantRecommendTool(BaseTravelTool):
    """Tool for recommending nearby restaurants (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': lambda lat, lon: f"未找到坐标 ({lat}, {lon}) 附近的推荐餐厅, 请检查坐标来源",
            'db_loaded': lambda count, path: f"✓ 餐厅推荐数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 餐厅推荐数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': lambda lat, lon: f"No recommended restaurants found near coordinates ({lat}, {lon}), please check coordinate source",
            'db_loaded': lambda count, path: f"✓ Restaurant recommendation database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Restaurant recommendation database not found at {path}",
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
        Execute restaurant recommendation
        
        Args:
            params: Query parameters containing latitude, longitude
            
        Returns:
            JSON string of query results
        """
        params = self._verify_json_format_args(params)
        
        latitude = params.get('latitude')
        longitude = params.get('longitude')
        
        if self.data is None:
            return self.fields['db_not_loaded']

        lat_str = latitude
        lon_str = longitude
        
        # Compatible with both merged and old structures
        if 'query_latitude' in self.data.columns and 'query_longitude' in self.data.columns:
            query_result = self.data[
                (self.data['query_latitude'].astype(str) == lat_str) &
                (self.data['query_longitude'].astype(str) == lon_str)
            ]
        else:
            query_result = self.data.iloc[0:0]
        
        if query_result.empty:
            return self.fields['not_found'](latitude, longitude)
        
        results = []
        for _, row in query_result.iterrows():
            result = {
                "name": row.get('restaurant_name', ''),
                "latitude": str(row.get('latitude', 0)),
                "longitude": str(row.get('longitude', 0)),
                "price_per_person": str(row.get('price_per_person', 0)),
                "cuisine": row.get('cuisine', ''),
                "opening_time": row.get('opening_time', ''),
                "closing_time": row.get('closing_time', ''),
                "nearby_attraction_name": row.get('nearby_attraction_name', ''),
                "rating": str(row.get('rating', 4.5))
            }
            
            # If CSV has tags field, add to return result
            if 'tags' in row.index:
                tags_field = row.get('tags', None)
                if tags_field and isinstance(tags_field, str) and tags_field.strip():
                    tags_list = tags_field.split(';')
                    result['tags'] = tags_list
            
            results.append(result)
        
        return self.format_result_as_json(results)


@register_tool('query_restaurant_details')
class RestaurantDetailsQueryTool(BaseTravelTool):
    """Tool for querying detailed restaurant information (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': lambda name: f"未找到餐厅 {name} 的详细信息",
            'db_loaded': lambda count, path: f"✓ 餐厅详情数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 餐厅详情数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': lambda name: f"Detailed information not found for restaurant {name}",
            'db_loaded': lambda count, path: f"✓ Restaurant details database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Restaurant details database not found at {path}",
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
        Execute restaurant details query
        
        Args:
            params: Query parameters containing restaurant_name
            
        Returns:
            JSON string of query results
        """
        params = self._verify_json_format_args(params)
        
        restaurant_name = params.get('restaurant_name')
        
        if self.data is None:
            return self.format_result_as_json({
                "message": self.fields['db_not_loaded'],
                "restaurant_name": restaurant_name
            })
        
        # Query from CSV database
        if 'restaurant_name' in self.data.columns:
            query_result = self.data[self.data['restaurant_name'] == restaurant_name]
        else:
            query_result = self.data.iloc[0:0]
        
        if query_result.empty:
            return self.format_result_as_json({
                "message": self.fields['not_found'](restaurant_name),
                "restaurant_name": restaurant_name
            })
        
        # Build return result (take first row if duplicates exist)
        row = query_result.iloc[0]
        result = {
            "id": row.get('restaurant_id', ''),
            "name": row.get('restaurant_name', restaurant_name),
            "latitude": str(row.get('latitude', 0)),
            "longitude": str(row.get('longitude', 0)),
            "price_per_person": str(row.get('price_per_person', '100')),
            "cuisine": row.get('cuisine', ''),
            "opening_time": row.get('opening_time', ''),
            "closing_time": row.get('closing_time', ''),
            "nearby_attraction_name": row.get('nearby_attraction_name', ''),
            "rating": str(row.get('rating', 4.0))
        }
        
        # If CSV has tags field, add to return result
        if 'tags' in row.index:
            tags_field = row.get('tags', None)
            if tags_field and isinstance(tags_field, str) and tags_field.strip():
                tags_list = tags_field.split(';')
                result['tags'] = tags_list
        
        return self.format_result_as_json(result)
