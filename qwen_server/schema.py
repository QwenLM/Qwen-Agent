# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pydantic import BaseModel


class PathConfig(BaseModel):
    work_space_root: str
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

    class Config:
        protected_namespaces = ()


class GlobalConfig(BaseModel):
    path: PathConfig
    server: ServerConfig
