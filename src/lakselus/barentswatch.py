"""Tynd klient til BarentsWatch Fishhealth API (OAuth2 client credentials).

Dokumentation: https://www.barentswatch.no/bwapi/openapi/ (vælg "fishhealth").
Vilkår: NLOD; kreditér BarentsWatch og Mattilsynet. Hent sekventielt, ikke parallelt.

Indhold
1. Godkendelse   – adgangstoken, der genbruges, til det udløber
2. HTTP          – fælles GET med token og timeout
3. Datasæt       – produktionsområder, lusetal og behandlinger
"""

import io
import time

import pandas as pd
import requests

from lakselus.config import hent_noegle

TOKEN_URL = "https://id.barentswatch.no/connect/token"
API_URL = "https://www.barentswatch.no/bwapi"


# --- 1. Godkendelse ----------------------------------------------------------------------

_token: dict = {}


def _access_token() -> str:
    """Gyldigt adgangstoken; et nyt hentes først, når det gamle er ved at udløbe."""
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


# --- 2. HTTP -----------------------------------------------------------------------------

def _get(sti: str, **params) -> requests.Response:
    svar = requests.get(
        f"{API_URL}{sti}",
        params=params,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=120,
    )
    svar.raise_for_status()
    return svar


def _bulk_eksport(rapport: str, fra_aar: int, til_aar: int, til_uge: int) -> pd.DataFrame:
    """Bulk-eksport fra Fishhealth som CSV (reporttype: lice, treatments, disease, cleanerfishreport)."""
    svar = _get(
        "/v1/geodata/download/fishhealth",
        reporttype=rapport,
        filetype="csv",
        fromyear=fra_aar,
        fromweek=1,
        toyear=til_aar,
        toweek=til_uge,
    )
    # Separatoren er ikke dokumenteret; lad pandas gætte.
    return pd.read_csv(io.StringIO(svar.content.decode("utf-8-sig")), sep=None, engine="python")


# --- 3. Datasæt --------------------------------------------------------------------------

def produktionsomraader() -> pd.DataFrame:
    """De 13 produktionsområder (id, navn, farve/trafiklys, gyldighed)."""
    return pd.json_normalize(_get("/v1/geodata/productionarea").json())


def lusetal(fra_aar: int, til_aar: int, til_uge: int = 52) -> pd.DataFrame:
    """Ugentlige lusetællinger pr. lokalitet.

    Kolonner bl.a.: År, Uke, Lokalitetsnummer, Voksne hunnlus, Sjøtemperatur, ProduksjonsområdeId.
    """
    return _bulk_eksport("lice", fra_aar, til_aar, til_uge)


def behandlinger(fra_aar: int, til_aar: int, til_uge: int = 52) -> pd.DataFrame:
    """Lusebehandlinger pr. lokalitet og uge – én række pr. behandling.

    Kolonner bl.a.: År, Uke, Lokalitetsnummer, Tiltak (medikamentell / ikke-medikamentell),
    Type behandling (mekanisk, termisk, ferskvann, bad, fôr …), Omfang, ProduksjonsområdeId.
    """
    return _bulk_eksport("treatments", fra_aar, til_aar, til_uge)
