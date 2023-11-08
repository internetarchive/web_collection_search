# Web Archive Search Index API and UI

An API wrapper to the Elasticsearch index of web archival collections and a web UI to explore those indexes. A part of the [story-indexer stack](https://github.com/mediacloud/story-indexer). Mantained as a separate repository for future legibility. 

## ES Index

The API service expects the following ES index schema, where `title` and `snippet` fields must have the `fielddata` enabled (if they have the type `text`).
This is currently defined in the story-indexer stack, but is replicated here for convenience. 
<details>

```json
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
    }
}
```

</details>

## Run Services

This service is not designed to be run stand-alone, rather it is deployed as a component in the [story-indexer stack](https://github.com/mediacloud/story-indexer). Configurations is set using environment variables by setting corresponding upper-case names of the cofig parameters.
Environment variables that accept a list (e.g., `ESHOSTS` and `INDEXES`) can have commas or spaces as separators. Configuration via a config file in the syntax of the provided config.yml.sample can be used for testing.


Then run the API and UI services using Docker Compose:

```
$ docker compose up
```

Access an interactive API documentation and a collection index explorer in a web browser:

- API: http://localhost:8000/docs
- UI: http://localhost:8001/

