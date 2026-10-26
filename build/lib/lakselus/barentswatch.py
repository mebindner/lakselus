"""Tynd klient til BarentsWatch Fishhealth API (OAuth2 client credentials).

Dokumentation: https://www.barentswatch.no/bwapi/openapi/ (vælg "fishhealth").
Vilkår: NLOD; kreditér BarentsWatch og Mattilsynet. Hent sekventielt, ikke parallelt.
"""

import io
import time

import pandas as pd
import requests

from lakselus.config import hent_noegle

TOKEN_URL = "https://id.barentswatch.no/connect/token"
API_URL = "https://www.barentswatch.no/bwapi"

_token: dict = {}


def _access_token() -> str:
    if _token.get("udloeber", 0) > time.time() + 60:
        return _token["vaerdi"]
    client_id, client_secret = hent_noegle()
    svar = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api",
        },
        timeout=30,
    )
    svar.raise_for_status()
    body = svar.json()
    _token.update(vaerdi=body["access_token"], udloeber=time.time() + body["expires_in"])
    return _token["vaerdi"]


def _get(sti: str, **params) -> requests.Response:
    svar = requests.get(
        f"{API_URL}{sti}",
        params=params,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=120,
    )
    svar.raise_for_status()
    return svar


def produktionsomraader() -> pd.DataFrame:
    """De 13 produktionsområder (id, navn, farve/trafiklys, gyldighed)."""
    return pd.json_normalize(_get("/v1/geodata/productionarea").json())


def lusetal(fra_aar: int, til_aar: int, til_uge: int = 52) -> pd.DataFrame:
    """Ugentlige lusetællinger pr. lokalitet (bulk-eksport, reporttype=lice).

    Kolonner bl.a.: year, week, localityNo, avgAdultFemaleLice, seaTemperature,
    productionAreaId, fallow, hasReportedLice.
    """
    svar = _get(
        "/v1/geodata/download/fishhealth",
        reporttype="lice",
        filetype="csv",
        fromyear=fra_aar,
        fromweek=1,
        toyear=til_aar,
        toweek=til_uge,
    )
    # Separatoren er ikke dokumenteret; lad pandas gætte.
    return pd.read_csv(io.StringIO(svar.content.decode("utf-8-sig")), sep=None, engine="python")
