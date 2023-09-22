### Prerequisites

Before you begin, ensure you have the following prerequisites in place:

1. Docker: Docker must be installed on the host where you plan to set up the Swarm. You can download and install Docker from Docker's [official website](https://docs.docker.com/engine/install/ubuntu/#install-from-a-package).

2. Docker Compose: Make sure you have Docker Compose installed, as it's essential for managing multi-container applications. You can install Docker Compose by following the instructions in the official [documentation](https://docs.docker.com/compose/install/).

### Network Setup

The Web Search API should connect to the Elasticsearch cluster running from the `indexer`. 
The `indexer` runs as a swarm cluster and therefore to expose the ES endpoint to the API, we need to deploy the Web Search API in the same overlay network

To create the network (if non exists)

    `docker network create -d overlay --attachable story-indexer`


### Docker compose

If relying on a shared network for the Search API and the `indexer`, ensure the `docker-compose.yml` is attached to th overlay network created above.

To build & run the services

    `docker compose up --build`