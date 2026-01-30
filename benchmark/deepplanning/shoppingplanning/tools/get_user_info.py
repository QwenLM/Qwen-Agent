import json
from typing import Union, Dict, List, Optional
from base_shopping_tool import BaseShoppingTool, register_tool
from pathlib import Path

@register_tool('get_user_info')
class GetUserInfoTool(BaseShoppingTool):
    """
    Tool for retrieving user information. Can get all users, or a specific user by user_id.
    """

    def __init__(self, cfg: Dict = None):
        super().__init__(cfg)
        self.users: List[Dict] = []
        self.users_map: Dict[str, Dict] = {}
        default_db_path = Path(__file__).parent.parent / 'database' / 'case_0' / 'user_info.json'

        if self.cfg and 'database_path' in self.cfg and self.cfg['database_path']:
            db_path = Path(self.cfg['database_path']) / 'user_info.json'
        else:
            db_path = default_db_path
        
        self._load_database(db_path)

    def _load_database(self, path: Path):
        """Load the user database in JSON format."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.users = []
                    self.users_map = {}
                    return
                
                data = json.loads(content)
                if isinstance(data, dict):
                    if 'user_id' in data:
                        self.users = [data]
                        self.users_map[data['user_id']] = data
                    else:
                        self.users = [data]
                        self.users_map = {}
                else:
                    self.users = []
                    self.users_map = {}
        except FileNotFoundError:
            self.users = []
            self.users_map = {}
        except json.JSONDecodeError:
            self.users = []
            self.users_map = {}
        except Exception:
            self.users = []
            self.users_map = {}

    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Retrieve user information. If user_id is provided, returns that user's info;
        otherwise returns all loaded user info.
        """
        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        user_id = params_dict.get('user_id')

        if user_id:
            user = self.users_map.get(user_id)
            if user:
                return self.format_result_as_json(user)
            else:
                return self.format_result_as_json({
                    "error": f"User with user_id '{user_id}' not found",
                    "user": None
                })
        else:
            return self.format_result_as_json(self.users[0] if self.users else {})
