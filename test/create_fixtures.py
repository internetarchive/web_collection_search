import json
import logging
import os
import hashlib
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError

from test import INDEX_NAME, ELASTICSEARCH_URL, FIXTURES_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

es_client = Elasticsearch(hosts=[ELASTICSEARCH_URL], basic_auth=("elastic", "changeme"), verify_certs=False)

# first create the index
es_mappings = {
    "properties": {
        "original_url": {"type": "keyword"},
        "url": {"type": "keyword"},
        "normalized_url": {"type": "keyword"},
        "canonical_domain": {"type": "keyword"},
        "publication_date": {"type": "date", "ignore_malformed": True},
        "language": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "full_language": {"type": "keyword"},
        "text_extraction": {"type": "keyword"},
        "article_title": {
            "type": "text",
            "fields": {"keyword": {"type": "keyword"}},
        },
        "normalized_article_title": {
            "type": "text",
            "fields": {"keyword": {"type": "keyword"}},
        },
        "text_content": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "indexed_date": {"type": "date"},
    }
}

es_client.indices.create(index=INDEX_NAME, mappings=es_mappings, ignore=400)  # Ignore 400 to handle index already exists
logger.info(f"Index '{INDEX_NAME}' with field mappings created successfully (or already exists.")

# now import the fixtures
with open(os.path.join(FIXTURES_DIR, "fake-data.json"), "r") as f:
    imported_count = 0
    fixtures = json.load(f)
    logger.info(f"Loaded {len(fixtures)} fixtures to import")
    for fixture in fixtures:
        url_hash = hashlib.sha256(fixture['url'].encode("utf-8")).hexdigest()
        try:
            response = es_client.index(index=INDEX_NAME, id=url_hash, document=fixture)
            imported_count += 1
        except ConflictError:
            logger.warning("  duplicate fixture, ignoring")
    logger.info(f"  Imported {imported_count}")
