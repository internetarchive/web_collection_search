#!/usr/bin/env -S docker image build -t colsearch . -f

FROM    python:3

ENV     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
CMD     ["./api.py"]

RUN     pip install --no-cache-dir \
            "elasticsearch>=7.0.0,<8.0.0" \
            fastapi \
            streamlit \
            "uvicorn[standard]" \
            wordcloud

COPY . ./
