#!/usr/bin/env python3

import os
import random

from urllib.parse import quote_plus

import requests

import matplotlib.pyplot as plt
import altair as alt
import streamlit as st
import pandas as pd

from wordcloud import WordCloud

from utils import load_config, env_to_list


config = load_config()
config["indexes"] = env_to_list("INDEXES") or config.get("indexes", [])
config["title"] = os.getenv("TITLE", config.get("title", "Collection Search API")) + " Explorer"
config["apiurl"] = os.getenv("APIURL", config.get("apiurl", "http://localhost:8000/v1")).rstrip("/")
config["maxwc"] = int(os.getenv("MAXWC", config.get("maxwc", 30)))
COLLECTIONS = [c.split(":")[-1] for c in config["indexes"]]


st.set_page_config(page_title=config["title"], layout="wide")
st.title(config["title"])


# @st.cache(ttl=300)
def load_data(cname, qstr, ep="search/overview"):
    r = requests.get(f"{config['apiurl']}/{cname}/{ep}?q={quote_plus(qstr)}", timeout=60)
    if r.ok:
        return r.json()
    return None


qp = st.experimental_get_query_params()
for p in ("col", "q"):
    if p not in st.session_state and qp.get(p):
        st.session_state[p] = qp.get(p, [""])[0]

cols = st.columns([20, 80])
col = cols[0].selectbox("Collection", COLLECTIONS, key="col")
q = cols[1].text_input("Search Query", key="q", placeholder="covid -vaccine title:usa")

if not q or not col:
    st.stop()

st.experimental_set_query_params(**st.session_state)

d = load_data(col, q)
if not d:
    st.warning("No results returned!")
    st.stop()

ov = {
    "total": d["total"],
    "topdomains": pd.DataFrame(d["topdomains"].items(), columns=["Domain", "Articles"]),
    "toptlds": pd.DataFrame(d["toptlds"].items(), columns=["TLD", "Articles"]),
    "toplangs": pd.DataFrame(d["toplangs"].items(), columns=["Language", "Articles"]),
    "dailycounts": pd.DataFrame(d["dailycounts"].items(), columns=["Date", "Articles"]),
    "matches": d["matches"]
}

cols = st.columns(4)
cols[0].metric("Hits", f"{ov['total']:,}")
cols[1].metric("Languages", f"{'100+' if len(ov['toplangs'])>=100 else len(ov['toplangs'])}")
cols[2].metric("Domains", f"{'100+' if len(ov['topdomains'])>=100 else len(ov['topdomains'])}")
cols[3].metric("Days", f"{len(ov['dailycounts']):,}")

tbs = st.tabs(["Top Hits", "Data"])
res = ["Title | Domain | Published | Archived | Language", ":---|:---|:---:|:---:|:---:"]
for m in ov["matches"]:
    t = m.get("article_title", "UNKNOWN").replace("|", "&vert;")
    res.append(" | ".join([f"[{t}]({m.get('archive_playback_url') or '#'})",
                           f"`{m.get('canonical_domain') or '~'}` | `{m.get('publication_date') or '~'}`",
                           f"`{(m.get('capture_time') or '~')[:10]}` | `{m.get('language') or '~'}`"]))
tbs[0].write("\n".join(res))
tbs[1].write(ov["matches"])

tbs = st.tabs(["Temporal Attention", "Data"])
ov["dailycounts"]["Day"] = ov["dailycounts"]["Date"] + "T12:00:00Z"
c = alt.Chart(ov["dailycounts"], height=250).mark_line(
    point=alt.OverlayMarkDef(color="#e74c3c")
).encode(
    x="Day:T",
    y="Articles:Q",
    tooltip=["Day:T", "Articles"]
).interactive(bind_y=False).configure_axisX(grid=False)
tbs[0].altair_chart(c, use_container_width=True)
tbs[1].write(ov["dailycounts"][["Date", "Articles"]])

fmap = {
    "Domain": "topdomains",
    "TLD": "toptlds",
    "Language": "toplangs"
}
cols = st.columns(len(fmap))
for i, (k, v) in enumerate(fmap.items()):
    with cols[i]:
        tbs = st.tabs([f"Top {k}s", "Data"])
        c = alt.Chart(ov[v].head(20), height=300).mark_bar().encode(
            x="Articles:Q",
            y=alt.Y(f"{k}:N", sort="-x"),
            tooltip=[f"{k}:N", "Articles:Q"]
        )
        tbs[0].altair_chart(c, use_container_width=True)
        tbs[1].write(ov[v])

for fld in ["article_title", "text_content"]:
    cols = st.columns(3)
    for i, aggr in enumerate(["top", "significant", "rare"]):
        with cols[i]:
            tbs = st.tabs([f"{aggr} {fld} terms".title(), "Data"])
            tt = load_data(col, q, f"terms/{fld}/{aggr}")
            if tt:
                sample = tt
                if len(tt) > config["maxwc"]:
                    if aggr == "rare":
                        sample = dict(random.sample(list(tt.items()), config["maxwc"]))
                    else:
                        sample = dict(list(tt.items())[:config["maxwc"]])
                wc = WordCloud(background_color="white")
                wc.generate_from_frequencies(sample)
                fig, ax = plt.subplots()
                ax.imshow(wc)
                ax.axis("off")
                tbs[0].pyplot(fig)
                tbs[1].write(pd.DataFrame(tt.items(), columns=["Term", "Frequency"]))
            else:
                tbs[0].info("No related terms found!")
                tbs[1].info("No related terms found!")
