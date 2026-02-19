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

import uuid
from typing import List

try:
    import chromadb
except ImportError:
    chromadb = None

from qwen_agent.llm.schema import Message
from qwen_agent.utils.utils import extract_text_from_message


class ConversationMemory:
    """Persistent conversation memory using vector database for retrieval."""

    def __init__(self, persist_dir: str = './chroma_db', collection_name: str = 'conversations'):
        if chromadb is None:
            raise ImportError('chromadb is required for ConversationMemory. Install with: pip install chromadb')
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_conversation(self, messages: List[Message]):
        """Add conversation messages to memory."""
        docs = []
        metadatas = []
        ids = []
        for msg in messages:
            text = extract_text_from_message(msg, add_upload_info=False)
            if text:
                docs.append(text)
                metadatas.append({
                    'role': msg.role,
                    'timestamp': str(msg.timestamp) if hasattr(msg, 'timestamp') else '',
                    'name': msg.name or ''
                })
                ids.append(str(uuid.uuid4()))
        if docs:
            self.collection.add(documents=docs, metadatas=metadatas, ids=ids)

    def retrieve_relevant(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve relevant past conversations based on query."""
        if not query:
            return []
        results = self.collection.query(query_texts=[query], n_results=top_k)
        return results['documents'][0] if results['documents'] else []

    def clear_memory(self):
        """Clear all stored conversations."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(name=self.collection.name)
