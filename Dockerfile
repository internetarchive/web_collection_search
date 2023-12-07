#!/usr/bin/env -S docker image build -t mcsystems/news-search-api . -f

# Base image
FROM    python:3.10 AS base
ENV     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app
CMD     ["./api.py"]
# Install depedencides
FROM    base
RUN     pip install --no-cache-dir -r requirements.txt
COPY    . ./
# Build image
FROM    base
COPY    . ./
