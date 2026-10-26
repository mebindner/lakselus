"""Streamlit-side. Start med:  streamlit run app.py"""

import pandas as pd
import streamlit as st

from lakselus import KILDE_TEKST
from lakselus.config import DATA_RAW, har_noegle

st.set_page_config(page_title="Lakselus-forecast", layout="wide")
st.title("Lakselus i norske havbrug")
st.caption("Forecast af voksne hunlus pr. produktionsområde, 1–4 uger frem – evalueret mod en naiv baseline.")

filer = sorted(DATA_RAW.glob("lusetal_*.csv"))

if not har_noegle():
    st.warning("Ingen API-nøgle fundet. Opret `.env` ud fra `.env.example` (se README).")
elif not filer:
    st.info("Nøgle fundet, men ingen data endnu. Kør `python -m lakselus.hent`.")
else:
    df = pd.concat((pd.read_csv(f) for f in filer), ignore_index=True)
    st.metric("Rækker (lokalitet × uge)", f"{len(df):,}")
    st.dataframe(df.head(50))

st.divider()
st.caption(f"{KILDE_TEKST} Licens: NLOD. [barentswatch.no](https://www.barentswatch.no)")
