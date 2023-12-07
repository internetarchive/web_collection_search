Testing
=======

To run unit tests locally (via `pytest`) you need to have an elasticsearch index running.

You can do this via Docker:
 * docker pull elasticsearch:8.8.2 
 * docker run --rm --name es-news-search-api -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:8.8.2

Then if you hit http://127.0.0.1:9200 you should see some json text response indicating it is running. 
