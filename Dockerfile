#!/usr/bin/env -S docker image build -t colsearch . -f

# Base image
FROM    python:3.10 AS base
ENV     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app
CMD     ["./api.py"]
RUN     pip install --no-cache-dir \
            altair \
            "elasticsearch=8.8.0" \
            fastapi \
            matplotlib \
            pandas \
            pydantic \
            requests \
            streamlit \
            "uvicorn[standard]" \
            wordcloud \
            pyyaml

# Lint code
FROM    base
RUN     pip install --no-cache-dir pylint
COPY    . ./
RUN     pylint *.py \
            --max-line-length=120 \
            --good-names="c,ct,e,ep,id,q,r" \
            --disable="C0103,C0114,C0115,C0116" \
            --extension-pkg-whitelist="pydantic"

# Build image
FROM    base
COPY    . ./
