#!/usr/bin/env python3

import base64
import os
import sys

from collections import Counter
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import TransportError
from fastapi import FastAPI, Request, Response, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Union
from urllib.parse import quote_plus

from utils import load_config, env_to_list, list_to_enum


VERSION_1 = "v1"

config = load_config()
config["termfields"] = env_to_list("TERMFIELDS") or config.get("termfields", [])
config["termaggrs"] = env_to_list("TERMAGGRS") or config.get("termaggrs", [])
config["indexes"] = env_to_list("INDEXES") or config.get("indexes", [])
config["eshosts"] = env_to_list("ESHOSTS") or config.get("eshosts", ["http://localhost:9200"])
config["wayback"] = os.getenv("WAYBACK", config.get("wayback", "https://web.archive.org/web")).rstrip("/")
config["maxpage"] = int(os.getenv("MAXPAGE", config.get("maxpage", 1000)))
config["title"] = os.getenv("TITLE", config.get("title", ""))
config["description"] = os.getenv("DESCRIPTION", config.get("description", ""))
config["debug"] = os.getenv("DEBUG", config.get("debug", False))

ES = Elasticsearch(config["eshosts"])

Collection = list_to_enum("Collection", config["indexes"])
TermField = list_to_enum("TermField", config["termfields"])
TermAggr = list_to_enum("TermAggr", config["termaggrs"])

tags = [{
    "name": "info",
    "description": "Informational endpoints with human-readable responses to fill the hierarchy."
}, {
    "name": "data",
    "description": "Data endpoints with machine-readable responses to interact with the collection indexes."
}]
if config["debug"]:
    tags.append({
        "name": "debug",
        "description": "Debugging endpoints with raw data from the backend, not suitable to be enabled in production."
    })


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["link", "x-resume-token"]
)

v1 = FastAPI(
    title=config.get("title", "Interactive API") + " Docs",
    description=config.get("description", "A wrapper API for ES indexes."),
    version=VERSION_1,
    openapi_tags=tags
)


class Query(BaseModel):
    q: str


class PagedQuery(Query):
    resume: Union[str, None] = None


def encode(str: str):
    return base64.b64encode(str.encode(), b"-_").decode()


def decode(str: str):
    return base64.b64decode(str.encode(), b"-_").decode()


def cs_basic_query(q: str):
    return {
        "_source": [
            "title",
            "publication_date",
            "language",
            "domain",
            "url",
            "first_captured"
        ],
        "query": {
            "query_string": {
                "default_field": "snippet",
                "default_operator": "AND",
                "query": q
            }
        }
    }


def cs_overview_query(q: str):
    query = cs_basic_query(q)
    query.update({
        "aggregations": {
            "daily": {
                "date_histogram": {
                    "field": "publication_date",
                    "calendar_interval": "day",
                    "min_doc_count": 1
                }
            },
            "lang": {
                "terms": {
                    "field": "language",
                    "size": 100
                }
            },
            "domain": {
                "terms": {
                    "field": "domain",
                    "size": 100
                }
            },
            "tld": {
                "terms": {
                    "field": "tld",
                    "size": 100
                }
            }
        }
    })
    return query


def cs_terms_query(q: str, field: str = "title", aggr: str = "top"):
    resct = 100
    aggr_map = {
        "top": {
            "terms": {
                "field": field,
                "size": resct,
                "min_doc_count": 10,
                "shard_min_doc_count": 3
            }
        },
        "significant": {
            "significant_terms": {
                "field": field,
                "size": resct,
                "min_doc_count": 10,
                "shard_min_doc_count": 3
            }
        },
        "rare": {
            "rare_terms": {
                "field": field,
                "exclude": "[0-9].*"
            }
        }
    }
    query = cs_basic_query(q)
    query.update({
        "track_total_hits": False,
        "_source": False,
        "aggregations": {
            "sample": {
                "sampler": {
                    "shard_size": 10 if aggr == "rare" else 100
                },
                "aggregations": {
                    "topterms": aggr_map[aggr]
                }
            }
        }
    })
    return query


def cs_paged_query(q: str, resume: Union[str, None] = None):
    query = cs_basic_query(q)
    query.update({
        "size": config["maxpage"],
        "track_total_hits": False,
        "sort": [{"surt_url": "asc"}]
    })
    if resume:
        query["search_after"] = [decode(resume)]
    return query


def format_match(hit: dict, base: str, collection: str, expanded: bool = False):
    src = hit["_source"]
    ct = src.get("first_captured") or "19700101000000"
    res = {
        "title": src.get("title") or "[UNKNOWN]",
        "publication_date": (src.get("publication_date") or "")[:10],
        "capture_time": f"{ct[:4]}-{ct[4:6]}-{ct[6:8]}T{ct[8:10]}:{ct[10:12]}:{ct[12:14]}Z",
        "language": src.get("language") or "",
        "domain": src["domain"],
        "url": src["url"],
        "original_capture_url": f"{config['wayback']}/{ct}id_/{src['url']}",
        "archive_playback_url": f"{config['wayback']}/{ct}/{src['url']}",
        "article_url": f"{base}/{collection}/article/{hit['_id']}"
    }
    if expanded:
        res["surt_url"] = src["surt_url"]
        res["snippet"] = src.get("snippet", "")
        res["text_extraction_method"] = src.get("text_extraction_method", "")
        res["version"] = src.get("version", "")
    return res


def format_day_counts(bucket: list):
    return {item["key_as_string"][:10]: item["doc_count"] for item in bucket}


def format_counts(bucket: list):
    return {item["key"]: item["doc_count"] for item in bucket}


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
def api_entrypoint(req: Request):
    """
    Link to the interactive API documentation
    """
    return "\n".join(['<ul>',
            f'<li><a href="{req.scope.get("root_path")}/{VERSION_1}/docs">Interactive API Docs ({VERSION_1})</a></li>',
            '</ul>'])


@app.get("/docs", response_class=RedirectResponse)
@app.head("/docs", response_class=RedirectResponse)
def api_entrypoint(req: Request):
    """
    Redirect to recent API documentation
    """
    return f'{req.scope.get("root_path")}/{VERSION_1}/docs'


@app.get("/redoc", response_class=RedirectResponse)
@app.head("/redoc", response_class=RedirectResponse)
def api_entrypoint(req: Request):
    """
    Redirect to recent API documentation
    """
    return f'{req.scope.get("root_path")}/{VERSION_1}/redoc'


@v1.get("/", response_class=HTMLResponse, tags=["info"])
@v1.head("/", response_class=HTMLResponse, include_in_schema=False)
def version_root(req: Request):
    """
    Links to various collections
    """
    return "\n".join(['<ul>'] + [f'<li><a href="{req.scope.get("root_path")}/{col.value}">{col.value}</a></li>' for col in Collection] + ['</ul>'])


@v1.get("/{collection}", response_class=HTMLResponse, tags=["info"])
@v1.head("/{collection}", response_class=HTMLResponse, include_in_schema=False)
def collection_root(collection: Collection, req: Request):
    """
    Links to various collection API endpoints
    """
    return "\n".join(['<ul>',
            f'<li><a href="{req.scope.get("root_path")}/{collection.value}/search">Search API</a></li>',
            f'<li><a href="{req.scope.get("root_path")}/{collection.value}/terms">Related Terms API</a></li>',
            f'<li><a href="{req.scope.get("root_path")}/{collection.value}/article">Artcile</a></li>',
            '</ul>'])


@v1.get("/{collection}/search", response_class=HTMLResponse, tags=["info"])
@v1.head("/{collection}/search", response_class=HTMLResponse, include_in_schema=False)
def search_root(collection: Collection, req: Request):
    """
    Links to various search API endpoints
    """
    return "\n".join(['<ul>',
            f'<li><a href="{req.scope.get("root_path")}/{collection.value}/search/overview">Search Overview</a></li>',
            f'<li><a href="{req.scope.get("root_path")}/{collection.value}/search/result">Search Result</a></li>',
            '</ul>'])


def _search_overview(collection: Collection, q: str, req: Request):
    res = ES.search(index=collection.name, body=cs_overview_query(q))
    if not res["hits"]["hits"]:
        raise HTTPException(status_code=404, detail="No results found!")
    return {
        "query": q,
        "total": max(res["hits"]["total"]["value"], sum(item["doc_count"] for item in res["aggregations"]["tld"]["buckets"])),
        "topdomains": format_counts(res["aggregations"]["domain"]["buckets"]),
        "toptlds": format_counts(res["aggregations"]["tld"]["buckets"]),
        "toplangs": format_counts(res["aggregations"]["lang"]["buckets"]),
        "dailycounts": format_day_counts(res["aggregations"]["daily"]["buckets"]),
        "matches": [format_match(h, f'{req.base_url}{req.scope.get("root_path").lstrip("/")}', collection.value) for h in res["hits"]["hits"]]
    }


@v1.get("/{collection}/search/overview", tags=["data"])
@v1.head("/{collection}/search/overview", include_in_schema=False)
def search_overview_via_query_params(collection: Collection, q: str, req: Request):
    """
    Report overview summary of the search result
    """
    return _search_overview(collection, q, req)


@v1.post("/{collection}/search/overview", tags=["data"])
def search_overview_via_payload(collection: Collection, req: Request, payload: Query):
    """
    Report summary of the search result
    """
    return _search_overview(collection, payload.q, req)


def _search_result(collection: Collection, q: str, req: Request, resp: Response, resume: Union[str, None] = None):
    res = ES.search(index=collection.name, body=cs_paged_query(q, resume))
    if not res["hits"]["hits"]:
        raise HTTPException(status_code=404, detail="No results found!")
    if len(res["hits"]["hits"]) == config["maxpage"]:
        resume_key = encode(res["hits"]["hits"][-1]["sort"][0])
        resp.headers["x-resume-token"] = resume_key
        resp.headers["link"] = f'<{req.base_url}{req.scope.get("root_path").lstrip("/")}/{collection.value}/search/result?q={quote_plus(q)}&resume={resume_key}>; rel="next"'
    return [format_match(h, f'{req.base_url}{req.scope.get("root_path").lstrip("/")}', collection.value) for h in res["hits"]["hits"]]


@v1.get("/{collection}/search/result", tags=["data"])
@v1.head("/{collection}/search/result", include_in_schema=False)
def search_result_via_query_params(collection: Collection, q: str, req: Request, resp: Response, resume: Union[str, None] = None):
    """
    Paged response of search result
    """
    return _search_result(collection, q, req, resp, resume)


@v1.post("/{collection}/search/result", tags=["data"])
def search_result_via_payload(collection: Collection, req: Request, resp: Response, payload: PagedQuery):
    """
    Paged response of search result
    """
    return _search_result(collection, payload.q, req, resp, payload.resume)


if config["debug"]:
    @v1.post("/{collection}/search/esdsl", tags=["debug"])
    def search_esdsl_via_payload(collection: Collection, payload: dict = Body(...)):
        """
        Search using ES Query DSL as JSON payload
        """
        return ES.search(index=collection.name, body=payload)


def _get_terms(collection: Collection, q: str, field: TermField, aggr: TermAggr):
    res = ES.search(index=collection.name, body=cs_terms_query(q, field, aggr))
    if not res["hits"]["hits"] or not res["aggregations"]["sample"]["topterms"]["buckets"]:
        raise HTTPException(status_code=404, detail="No results found!")
    return format_counts(res["aggregations"]["sample"]["topterms"]["buckets"])


@v1.get("/{collection}/terms", response_class=HTMLResponse, tags=["info"])
@v1.head("/{collection}/terms", response_class=HTMLResponse, include_in_schema=False)
def term_field_root(collection: Collection, req: Request):
    """
    Links to various term fields
    """
    return "\n".join(['<ul>'] + [f'<li><a href="{req.scope.get("root_path")}/{collection.value}/terms/{field.value}">{field.value}</a></li>' for field in TermField] + ['</ul>'])


@v1.get("/{collection}/terms/{field}", response_class=HTMLResponse, tags=["info"])
@v1.head("/{collection}/terms/{field}", response_class=HTMLResponse, include_in_schema=False)
def term_aggr_root(collection: Collection, req: Request, field: TermField):
    """
    Links to various term aggregations
    """
    return "\n".join(['<ul>'] + [f'<li><a href="{req.scope.get("root_path")}/{collection.value}/terms/{field.value}/{aggr.value}">{aggr.value}</a></li>' for aggr in TermAggr] + ['</ul>'])


@v1.get("/{collection}/terms/{field}/{aggr}", tags=["data"])
@v1.head("/{collection}/terms/{field}/{aggr}", include_in_schema=False)
def get_terms_via_query_params(collection: Collection, q: str, field: TermField, aggr: TermAggr):
    """
    Top terms with frequencies in matching articles
    """
    return _get_terms(collection, q, field.value, aggr.value)


@v1.post("/{collection}/terms/{field}/{aggr}", tags=["data"])
def get_terms_via_payload(collection: Collection, payload: Query, field: TermField, aggr: TermAggr):
    """
    Top terms with frequencies in matching articles
    """
    return _get_terms(collection, payload.q, field.value, aggr.value)


@v1.get("/{collection}/article/{id}", tags=["data"])
@v1.head("/{collection}/article/{id}", include_in_schema=False)
def get_article(collection: Collection, id: str, req: Request):
    """
    Fetch an individual article record by ID
    """
    try:
        hit = ES.get(index=collection.name, id=id)
    except TransportError as e:
        raise HTTPException(status_code=404, detail=f"An article with ID {id} not found!")
    return format_match(hit, f'{req.base_url}{req.scope.get("root_path").lstrip("/")}', collection.value, True)


app.mount(f"/{VERSION_1}", v1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", reload=True)
