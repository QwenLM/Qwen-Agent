"""
Attraction Query Tool - Query and recommend attractions (Multilingual)
"""
import os
from typing import Dict, Optional, Union

from .base_travel_tool import BaseTravelTool, register_tool


@register_tool('query_attraction_details')
class AttractionDetailsQueryTool(BaseTravelTool):
    """Tool for querying detailed attraction information (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': lambda name: f"未找到景点 {name} 的详细信息",
            'attraction_id': "景点ID",
            'attraction_name': "景点名称",
            'city': "所属城市",
            'address': "地址",
            'coordinates': "经纬度坐标",
            'latitude': "纬度",
            'longitude': "经度",
            'description': "景点简介",
            'rating': "用户评分",
            'visitor_rating': "（游客平均评价）",
            'opening_hours': "开放时间",
            'to': "至",
            'closed_dates': "闭馆日期",
            'min_visit_hours': "建议最短游玩时长",
            'max_visit_hours': "建议最长游玩时长",
            'hours_unit': "小时",
            'ticket_price': "门票价格",
            'currency_unit': "元",
            'attraction_type': "景点类型",
            'db_loaded': lambda count, path: f"✓ 景点数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 景点数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': lambda name: f"Detailed information not found for attraction {name}",
            'attraction_id': "Attraction ID",
            'attraction_name': "Attraction Name",
            'city': "City",
            'address': "Address",
            'coordinates': "Coordinates",
            'latitude': "Latitude",
            'longitude': "Longitude",
            'description': "Description",
            'rating': "Rating",
            'visitor_rating': "(average visitor rating)",
            'opening_hours': "Opening Hours",
            'to': "to",
            'closed_dates': "Closed Dates",
            'min_visit_hours': "Minimum Visit Duration",
            'max_visit_hours': "Maximum Visit Duration",
            'hours_unit': "hours",
            'ticket_price': "Ticket Price",
            'currency_unit': "RMB",
            'attraction_type': "Attraction Type",
            'db_loaded': lambda count, path: f"✓ Attraction database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Attraction database not found at {path}",
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
        Execute attraction details query
        
        Args:
            params: Query parameters containing attraction_name
            
        Returns:
            Formatted text string of query results
        """
        def format_result_as_text(result: dict) -> str:
            """Format attraction details dictionary into readable text"""
            lines = []
            lines.append(f"{self.fields['attraction_id']}：{result.get('attraction_id', '')}")
            lines.append(f"{self.fields['attraction_name']}：{result.get('attraction_name', '')}")
            lines.append(f"{self.fields['city']}：{result.get('city', '')}")
            lines.append(f"{self.fields['address']}：{result.get('address', '')}")
            lines.append(f"{self.fields['coordinates']}：{self.fields['latitude']} {result.get('latitude', '')}，{self.fields['longitude']} {result.get('longitude', '')}")
            lines.append(f"{self.fields['description']}：{result.get('description', '')}")
            lines.append(f"{self.fields['rating']}：{result.get('rating', '')}{self.fields['visitor_rating']}")
            
            # Handle opening hours
            opening_time = result.get('opening_time', '')
            closing_time = result.get('closing_time', '')
            if opening_time == closing_time:
                lines.append(f"{self.fields['opening_hours']}：{opening_time}")
            else:
                lines.append(f"{self.fields['opening_hours']}：{opening_time} {self.fields['to']} {closing_time}")
            
            lines.append(f"{self.fields['closed_dates']}：{result.get('closing_dates', '')}")
            lines.append(f"{self.fields['min_visit_hours']}：{result.get('min_visit_hours', '')} {self.fields['hours_unit']}")
            lines.append(f"{self.fields['max_visit_hours']}：{result.get('max_visit_hours', '')} {self.fields['hours_unit']}")
            lines.append(f"{self.fields['ticket_price']}：{result.get('ticket_price', 0)} {self.fields['currency_unit']}")
            lines.append(f"{self.fields['attraction_type']}：{result.get('attraction_type', '')}")
            
            return "\n".join(lines)

        params = self._verify_json_format_args(params)
        
        attraction_name = params.get('attraction_name')
        
        # Database not loaded
        if self.data is None:
            return self.fields['db_not_loaded']
        
        # Query from CSV
        df = self.data
        rows = df[df['attraction_name'] == attraction_name]
        if rows.empty:
            return self.fields['not_found'](attraction_name)
        row = rows.iloc[0]
        
        # Convert numpy scalars to Python basic types
        def to_num(v):
            try:
                if v == v:  # Filter NaN
                    return float(v)
                return None
            except Exception:
                return None

        rating_val = to_num(row.get("rating", None))
        min_hours_val = to_num(row.get("min_visit_hours", None))
        max_hours_val = to_num(row.get("max_visit_hours", None))
        ticket_price_val = to_num(row.get("ticket_price", None))

        # Build result
        result = {
            "attraction_id": str(row.get("attraction_id", "")),
            "attraction_name": str(row.get("attraction_name", attraction_name)),
            "city": str(row.get("city", "")),
            "address": str(row.get("address", "")),
            "latitude": str(row.get("latitude", "")),
            "longitude": str(row.get("longitude", "")),
            "description": str(row.get("description", "")),
            "rating": rating_val if rating_val is not None else "",
            "opening_time": str(row.get("opening_time", "")),
            "closing_time": str(row.get("closing_time", "")),
            "closing_dates": str(row.get("closing_dates", "")),
            "min_visit_hours": min_hours_val if min_hours_val is not None else "",
            "max_visit_hours": max_hours_val if max_hours_val is not None else "",
            "ticket_price": ticket_price_val if ticket_price_val is not None else "0",
            "attraction_type": str(row.get("attraction_type", ""))
        }
        
        return format_result_as_text(result)


@register_tool('recommend_attractions')
class AttractionRecommendTool(BaseTravelTool):
    """Tool for recommending attractions (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'db_not_loaded': "数据库未加载",
            'not_found': "未找到景点推荐",
            'recommendations': "推荐的景点有：\n",
            'attraction_suffix': lambda name, desc, atype: f"{name}，{desc}这是一个{atype}类型的景点",
            'db_loaded': lambda count, path: f"✓ 景点数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 景点数据库未找到于 {path}",
        },
        'en': {
            'db_not_loaded': "Database not loaded",
            'not_found': "No attraction recommendations found",
            'recommendations': "Recommended attractions:\n",
            'attraction_suffix': lambda name, desc, atype: f"{name}, {desc}. This is a {atype} type attraction",
            'db_loaded': lambda count, path: f"✓ Attraction database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Attraction database not found at {path}",
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
        Execute attraction recommendation
        
        Args:
            params: Query parameters containing city and optional attraction_type
            
        Returns:
            Formatted text string of recommendations
        """
        params = self._verify_json_format_args(params)
        
        city = params.get('city')
        attraction_type = params.get('attraction_type', '')
        
        # Database not loaded
        if self.data is None:
            return self.fields['db_not_loaded']
        
        df = self.data
        rows = df  # Return all data without city filtering
        if attraction_type:
            rows = rows[rows['attraction_type'] == attraction_type]
        
        if rows.empty:
            return self.fields['not_found']
        
        all_rows = list(rows.iterrows())

        # Build result string
        result_lines = [self.fields['recommendations']]
        
        for _, r in all_rows:
            attraction_name = r.get("attraction_name", "")
            description = r.get("description", "")
            attraction_type = r.get("attraction_type", "")
            
            result_lines.append(
                self.fields['attraction_suffix'](attraction_name, description, attraction_type)
            )
        
        return "\n".join(result_lines)
