# Web Archive Search Index API and UI

An API wrapper to the Elasticsearch index of web archival collections and a web UI to explore those indexes.

## ES Index

The API service expects the following ES index schema, where `title` and `snippet` fields must have the `fielddata` enabled (if they have the type `text`) and `first_captured` field stores 14-digit datetime in the format `YYYYMMDDhhmmss`.

<details>
<summary>$ curl -s http://localhost:9200/collection_index_name/_mappings | jq</summary>

```json
{
  "collection_index_name": {
    "mappings": {
      "properties": {
        "domain": {
          "type": "keyword"
        },
        "first_captured": {
          "type": "keyword"
        },
        "host": {
          "type": "keyword"
        },
        "language": {
          "type": "keyword"
        },
        "publication_date": {
          "type": "date"
        },
        "snippet": {
          "type": "text",
          "fielddata": true
        },
        "surt_url": {
          "type": "keyword"
        },
        "text_extraction_method": {
          "type": "keyword"
        },
        "title": {
          "type": "text",
          "fielddata": true
        },
        "tld": {
          "type": "keyword"
        },
        "url": {
          "type": "keyword"
        },
        "version": {
          "type": "keyword"
        }
      }
    }
  }
}
```

</details>

## Run Services

To run it clone this repository and update the config file to point to ES hosts and list index names (and optionally some other properties):

```
$ cp config.yml.sample config.yml
$ open config.yml
```

Alternatively, these configs can also be set using environment variables by setting corresponding upper-case names of the cofig parameters.
Environment variables that accept a list (e.g., `ESHOSTS` and `INDEXES`) can have commas or spaces as separators.

If the config file name/location is different, specify it with `CONFIG` environment variable.

Then run the API and UI services using Docker Compose:

```
$ docker compose up
```

Access an interactive API documentation and a collection index explorer in a web browser:

- API: http://localhost:8000/docs
- UI: http://localhost:8001/

## Docker compose
