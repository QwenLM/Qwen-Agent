"""
Train Query Tool - Query train ticket information (Multilingual)
"""
import os
from typing import Dict, Optional, Union

from .base_travel_tool import BaseTravelTool, register_tool


@register_tool('query_train_info')
class TrainQueryTool(BaseTravelTool):
    """Tool for querying train ticket information (supports zh/en)"""
    
    # Language-specific field mappings
    LANG_FIELDS = {
        'zh': {
            'segment': lambda idx: f"第{idx}段",
            'remaining_seats': "剩余票数量",
            'sufficient': "充足",
            'no_info': "未查询到信息",
            'not_found': lambda o, d, date: f"未找到从 {o} 到 {d} 在 {date} 的火车票信息",
            'station_sep': '站',
            'db_loaded': lambda count, path: f"✓ 火车票数据库加载成功: {count} 条记录 (路径: {path})",
            'db_not_found': lambda path: f"⚠ 警告: 火车票数据库未找到于 {path}",
        },
        'en': {
            'segment': lambda idx: f"Segment {idx}",
            'remaining_seats': "Remaining Seats",
            'sufficient': "Available",
            'no_info': "No information found",
            'not_found': lambda o, d, date: f"No train information found from {o} to {d} on {date}",
            'station_sep': ' Station',
            'db_loaded': lambda count, path: f"✓ Train database loaded: {count} records (path: {path})",
            'db_not_found': lambda path: f"⚠ Warning: Train database not found at {path}",
        }
    }
    
    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.database_path = cfg.get('database_path') if cfg else None
        
        # Get language-specific fields
        self.fields = self.LANG_FIELDS.get(self.language, self.LANG_FIELDS['en'])
        
        # Load database
        if self.database_path and os.path.exists(self.database_path):
            self.data = self.load_csv_database(self.database_path)
            print(self.fields['db_loaded'](len(self.data), self.database_path))
        else:
            if self.database_path:
                print(self.fields['db_not_found'](self.database_path))
            self.data = None
    
    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Execute train ticket query
        
        Args:
            params: Query parameters containing origin, destination, depDate
            
        Returns:
            JSON string of query results
        """
        # Verify parameter format
        params = self._verify_json_format_args(params)
        
        origin = params.get('origin')
        destination = params.get('destination')
        dep_date = params.get('depDate')
        seat_class = params.get('seatClassName', '')
        
        # If database not loaded
        if self.data is None:
            return self.fields['no_info']
        
        # Query from CSV database
        import pandas as pd
        query_result = self.data[
            (self.data['origin_city'] == origin) &
            (self.data['destination_city'] == destination) &
            (self.data['dep_date'] == dep_date)
        ]
        if seat_class:
            query_result = query_result[query_result['seat_class'] == seat_class]

        if query_result.empty:
            return self.fields['not_found'](origin, destination, dep_date)
        
        # Build result grouped by route_index
        routes = []
        for route_idx in sorted(query_result['route_index'].unique()):
            route_segments = query_result[query_result['route_index'] == route_idx].sort_values('segment_index')
            
            route_data = {}
            route_price = None
            
            for idx, row in enumerate(route_segments.itertuples(), 1):
                seat_status = row.seat_status
                if seat_status is None or str(seat_status).strip() == "" or str(seat_status).lower() == "nan":
                    seat_status = self.fields['sufficient']
                
                # Use language-specific field names
                segment = {
                    self.fields['segment'](idx): {
                        "arrCityName": row.destination_city,
                        "arrStationCode": row.arr_station_code,
                        "arrStationName": row.arr_station_name,
                        "depCityName": row.origin_city if idx == 1 else prev_row.arr_station_name.split(self.fields['station_sep'])[0],
                        "depStationCode": row.dep_station_code,
                        "depStationName": row.dep_station_name,
                        "duration": int(row.duration),
                        "arrDateTime": row.arr_datetime,
                        "depDateTime": row.dep_datetime,
                        "marketingTransportName": row.train_type,
                        "marketingTransportNo": row.train_no,
                        "seatClassName": row.seat_class,
                        self.fields['remaining_seats']: seat_status
                    }
                }
                route_data.update(segment)
                if idx == 1:
                    try:
                        route_price = float(row.price)
                    except Exception:
                        route_price = None
                prev_row = row
            
            route_data["price"] = route_price if route_price is not None else 0
            routes.append([route_data])
        
        return self.format_result_as_json(routes)
