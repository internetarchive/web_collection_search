#!/usr/bin/env -S docker image build -t mcsystems/news-search-api . -f

# Base image
FROM    python:3.10 AS base
ENV     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app
# Install depedencides
COPY    . ./
RUN     pip install --no-cache-dir -r requirements.txt
CMD     ["./api.py"]
