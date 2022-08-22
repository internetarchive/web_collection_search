#!/usr/bin/env -S docker image build -t colsearch . -f

# Base image
FROM    python:3 AS base

ENV     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

RUN     pip install --no-cache-dir \
            altair \
            "elasticsearch>=7.0.0,<8.0.0" \
            fastapi \
            matplotlib \
            pandas \
            pydantic \
            requests \
            streamlit \
            "uvicorn[standard]" \
            wordcloud \
            pyyaml

COPY    . ./

# Lint code
FROM    base

RUN     pip install --no-cache-dir pylint
RUN     pylint *.py \
            --max-line-length=120 \
            --good-names="c,ct,e,ep,id,q,r" \
            --disable="C0114,C0115,C0116" \
            --extension-pkg-whitelist="pydantic"

# Build image
FROM    base

CMD     ["./api.py"]
