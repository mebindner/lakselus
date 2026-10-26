"""Tidsmaskinen: pakker ugentlige lusetal pr. lokalitet kompakt til et 3D-kort, der afspilles i browseren."""

import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd

SKABELON = Path(__file__).with_name("tidsmaskine.html")
MANGLER = 255  # byte-værdi for "ikke talt denne uge"


def pak(raa: pd.DataFrame, fra: str = "2019-01-01") -> dict:
    """Én byte pr. (uge, lokalitet): round(hunlus * 100), loftet ved 2,54; 255 = ingen tælling.

    Det holder ~1.000 lokaliteter × ~400 uger på godt 0,5 MB, så hele afspilningen kan ske i browseren.
    """
    talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] >= fra)].dropna(subset=["hunlus", "lat", "lon"])
    lok = talt.groupby("lokalitet").agg(lon=("lon", "last"), lat=("lat", "last"), navn=("lokalitet_navn", "last"))
    uger = pd.date_range(talt["uge_start"].min(), talt["uge_start"].max(), freq="W-MON")

    matrix = np.full((len(uger), len(lok)), MANGLER, dtype=np.uint8)
    ui = uger.get_indexer(talt["uge_start"])
    li = lok.index.get_indexer(talt["lokalitet"])
    matrix[ui, li] = np.clip(np.round(talt["hunlus"].to_numpy() * 100), 0, 254).astype(np.uint8)

    national = talt.groupby("uge_start")["hunlus"].mean().reindex(uger)
    iso = uger.isocalendar()
    return {
        "lok": [[round(r.lon, 4), round(r.lat, 4), r.navn] for r in lok.itertuples()],
        # Måned efter ugens torsdag (ISO-ugens "egen" dag), så uge 1 ikke står som december.
        "uger": [[int(a), int(u), (d + pd.Timedelta(days=3)).strftime("%b")] for a, u, d in zip(iso["year"], iso["week"], uger)],
        "national": [None if pd.isna(v) else round(float(v), 3) for v in national],
        "vaerdier": base64.b64encode(matrix.tobytes()).decode("ascii"),
    }


def html(pakke: dict) -> str:
    data = json.dumps(pakke, ensure_ascii=False).replace("</", "<\\/")
    return SKABELON.read_text(encoding="utf-8").replace("__DATA__", data)
