import json
import os
from pathlib import Path
from typing import Union, Dict, List

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

from base_shopping_tool import BaseShoppingTool, register_tool

# BM25 similarity score threshold; only products with score above this value are returned
BM25_SCORE_THRESHOLD = 2

@register_tool('search_products')
class SearchProductsTool(BaseShoppingTool):
    """
    Handle open-ended natural language user queries by performing semantic matching
    using the BM25 algorithm on key product fields.
    """

    def __init__(self, cfg: Dict = None):
        """
        Initialize the tool, load the product database, and prepare for BM25 matching.
        """
        super().__init__(cfg)

        self.products: List[Dict] = []
        self.bm25 = None

        default_db_path = os.path.join(
            os.path.dirname(__file__), '..', 'database', 'case_0', 'products.jsonl'
        )

        if self.cfg and 'database_path' in self.cfg and self.cfg['database_path']:
            db_path = Path(self.cfg['database_path']) / 'products.jsonl'
        else:
            db_path = default_db_path

        self._load_and_prepare_database(db_path)

    def _load_and_prepare_database(self, path: str):
        """Load database and build corpus for BM25 indexing."""
        corpus = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        product = json.loads(line)
                        self.products.append(product)

                        # Create a "rich text" document for each product by concatenating key fields
                        searchable_text = " ".join([
                            product.get('brand', ''),
                            product.get('color', ''),
                            product.get('size', ''),
                            product.get('thickness', ''),
                            product.get('elasticity', ''),
                            product.get('version_type', ''),
                            product.get('collar_type', ''),
                            product.get('suitable_season', ''),
                            product.get('target_demographic', ''),
                            product.get('name', ''),
                        ])
                        corpus.append(searchable_text)

            if corpus:
                # Lowercase and split for case-insensitive tokenization
                tokenized_corpus = [doc.lower().split() for doc in corpus]
                self.bm25 = BM25Okapi(tokenized_corpus)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Main logic for BM25-based product search.
        """
        if not self.bm25:
            return self.format_result_as_json({
                "error": "BM25 index is not available. Check database loading."
            })

        try:
            params_dict = self._verify_json_format_args(params)
        except ValueError as e:
            return self.format_result_as_json({"error": str(e)})

        query = params_dict.get('query')
        limit = params_dict.get('limit', 20)

        if not query:
            return self.format_result_as_json({"product_ids": []})

        # Tokenize and lowercase query for case-insensitive search
        tokenized_query = query.lower().split()

        # Calculate BM25 scores for all documents
        doc_scores = self.bm25.get_scores(tokenized_query)

        # Collect products with scores above the threshold
        results_with_scores = []
        for i, score in enumerate(doc_scores):
            if score > BM25_SCORE_THRESHOLD:
                results_with_scores.append({
                    "product_id": self.products[i]['product_id'],
                    "name": self.products[i]['name'],
                    "score": score
                })

        # Sort by score descending, then limit result count
        sorted_results = sorted(results_with_scores, key=lambda x: x['score'], reverse=True)
        limited_results = sorted_results[:limit]

        final_product_ids = [item['product_id'] for item in limited_results]

        return self.format_result_as_json({"product_ids": final_product_ids})

