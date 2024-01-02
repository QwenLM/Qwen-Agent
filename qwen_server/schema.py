from pydantic import BaseModel


class PathConfig(BaseModel):
    work_space_root: str
    database_root: str
    download_root: str
    code_interpreter_ws: str


class ServerConfig(BaseModel):
    server_host: str
    fast_api_port: int
    app_in_browser_port: int
    workstation_port: int
    model_server: str
    api_key: str
    llm: str
    max_ref_token: int
    max_days: int
    functions: list

    class Config:
        protected_namespaces = ()


class GlobalConfig(BaseModel):
    path: PathConfig
    server: ServerConfig
