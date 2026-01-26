# RAG (Retrieval-Augmented Generation)

Qwen-Agent provides built-in RAG (Retrieval-Augmented Generation) capabilities to enhance responses by retrieving relevant content from a given set of documents. This allows the language model to ground its answers in specific, user-provided knowledge sources.

## Core Components

### 1. Document Parsing
- Supported file types: `.pdf`, `.docx`, `.pptx`, `.txt`, `.csv`, `.tsv`, `.xlsx`, `.xls`, and `.html`.
- Documents are split into text chunks using a configurable chunk size (`parser_page_size`, default: 500 tokens).
- Parsing is handled by the `DocParser` tool, which converts files into structured records ready for retrieval.

### 2. Keyword-Based Retrieval with BM25
- By default, Qwen-Agent uses the BM25 algorithm (via the `rank_bm25` library) for sparse keyword matching.
- The user query (or auto-generated keywords) is matched against document chunks to find the most relevant passages.
- Retrieval strategies can be customized via `rag_searchers` (e.g., `keyword_search`, `front_page_search`, or hybrid combinations).
- Retrieved results are truncated to fit within a token limit (`max_ref_token`, default: 20000 tokens) to avoid exceeding context windows.

### Optional: Keyword Generation
- To improve retrieval accuracy, Qwen-Agent can use an LLM to generate structured, multilingual keywords from the user query.
- Default strategy: `SplitQueryThenGenKeyword` — decomposes the query and produces comma-separated keywords in both Chinese and English.
- If no LLM is available, the original query is used directly for retrieval.

## How to Use

RAG is automatically enabled in the `Assistant` agent:

```python
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message, ContentItem

agent = Assistant(...)
response = agent.run(messages=[Message(role="user", content=[ContentItem(text="How long is the product warranty?"), ContentItem(file="manual.pdf")])])
```

Under the hood, Qwen-Agent:
1. Parses the provided files into text chunks,
2. Retrieves relevant chunks based on the query using BM25,
3. Returns the retrieved content as a structured JSON string (via the `retrieval` tool).

## Dependencies

RAG functionality requires additional Python packages. Install them with:

```bash
pip install "qwen-agent[rag]"
```

---

> In summary, Qwen-Agent’s RAG implementation offers a lightweight yet effective retrieval system based on document chunking and BM25 keyword matching—ideal for augmenting LLM responses with precise, source-grounded information without requiring embeddings or vector databases.
