"""Opslaget på Overview: søgeliste, URL-valg, afstand, naboer og anlæggets historik."""

import math

import pandas as pd
import pytest

from lakselus import appdata

SENESTE = pd.Timestamp("2026-10-19")


def raekker(*r) -> pd.DataFrame:
    """Tællinger: (lokalitet, navn, omraade, lat, lon, uger før seneste, hunlus, over grænsen, lusegrænse)."""
    return pd.DataFrame([{
        "lokalitet": lok, "lokalitet_navn": navn, "omraade": float(omr), "lat": lat, "lon": lon,
        "uge_start": SENESTE - pd.Timedelta(weeks=uger), "hunlus": lus, "har_talt": "Ja",
        "over_graense": over, "Lusegrense uke": graense,
    } for lok, navn, omr, lat, lon, uger, lus, over, graense in r])


# Tre anlæg ved 60° N: B ligger ~5,6 km øst for A, C ~111 km nord for A. D talte for over et år siden.
RAA = raekker(
    (1, "Aa", 3, 60.0, 5.0, 0, 0.6, "Ja", "0,5"),
    (1, "Aa", 3, 60.0, 5.0, 1, 0.2, "Nei", "0,5"),
    (1, "Aa", 3, 60.0, 5.0, 2, 0.4, "Nei", "0.5"),
    (2, "bravo", 3, 60.0, 5.1, 0, 0.1, "Nei", "0,5"),
    (2, "bravo", 3, 60.0, 5.1, 3, 0.3, "Nei", "0,5"),
    (3, "Charlie", 4, 61.0, 5.0, 1, 0.5, "Nei", "Ukjent"),
    (4, "Delta", 3, 60.0, 5.05, 60, 0.9, "Ja", "0,5"),
)


def test_anlaeg_oversigt_kun_aktive_med_seneste_taelling():
    a = appdata.anlaeg_oversigt(RAA, SENESTE)
    assert list(a.index) == [1, 2, 3]  # Delta har ikke talt det seneste år
    assert a.loc[3, "sidst_talt"] == SENESTE - pd.Timedelta(weeks=1)
    assert a["omraade"].dtype.kind == "i"


def test_soegevalg_omraader_foerst_og_anlaeg_efter_navn_uden_store_bogstaver():
    valg = appdata.soegevalg(appdata.anlaeg_oversigt(RAA, SENESTE), {4: "Nord", 3: "Syd"})
    assert list(valg) == ["po:3", "po:4", "site:1", "site:2", "site:3"]
    assert valg["po:3"] == "PO 3 · Syd"
    assert valg["site:2"] == "bravo · PO 3 · 2"


@pytest.mark.parametrize("params, forventet", [
    ({"po": "3"}, "po:3"),
    ({"site": "2"}, "site:2"),
    ({"site": "2", "po": "4"}, "site:2"),  # et anlæg er mere præcist end et område
    ({"site": "99"}, None),                # ukendt anlæg
    ({"site": "99", "po": "4"}, "po:4"),
    ({"po": "tre"}, None),
    ({"po": "03"}, "po:3"),
    ({}, None),
])
def test_fra_url_validerer(params, forventet):
    valg = {"po:3": "", "po:4": "", "site:2": ""}
    assert appdata.fra_url(params, valg) == forventet


@pytest.mark.parametrize("noegle", ["po:3", "site:12345", None])
def test_url_rundtur(noegle):
    valg = {"po:3": "", "site:12345": ""}
    assert appdata.fra_url(appdata.til_url(noegle), valg) == noegle


def test_afstand_km():
    assert appdata.afstand_km(60, 5, 60, 5) == pytest.approx(0)
    assert appdata.afstand_km(60, 5, 61, 5) == pytest.approx(111.2, abs=0.1)  # én breddegrad
    # En længdegrad ved 60° N er halvt så lang som ved ækvator
    assert appdata.afstand_km(60, 5, 60, 6) == pytest.approx(111.2 * math.cos(math.radians(60)), abs=0.2)


def test_graense_tal():
    assert appdata.graense_tal(pd.Series(["0,5", "0.2", "Ukjent", None])).tolist()[:2] == [0.5, 0.2]
    assert appdata.graense_tal(pd.Series(["Ukjent"])).isna().all()


def test_naboer_inden_for_radius_og_udvikling():
    a = appdata.anlaeg_oversigt(RAA, SENESTE)
    nab = appdata.naboer(a, RAA, 1, SENESTE, km=20, min_antal=0)
    assert list(nab["lokalitet"]) == [2]  # C ligger 111 km væk; anlægget selv er ikke sin egen nabo
    r = nab.iloc[0]
    assert r["km"] == pytest.approx(5.56, abs=0.05)
    assert r["hunlus"] == 0.1 and r["over_graense"] == "Nei"
    assert r["hunlus_4u_foer"] == 0.3  # snit af de 4 uger før seneste


def test_naboer_fyldes_op_med_de_naermeste():
    a = appdata.anlaeg_oversigt(RAA, SENESTE)
    nab = appdata.naboer(a, RAA, 1, SENESTE, km=20, min_antal=2)
    assert list(nab["lokalitet"]) == [2, 3]
    assert pd.isna(nab.iloc[1]["hunlus"])  # C talte ikke i seneste uge


def test_lokalitet_historik_komplet_gitter_med_naboer_og_graense():
    h = appdata.lokalitet_historik(RAA, 1, [2], SENESTE, uger=4)
    assert list(h["uge_start"]) == list(pd.date_range(SENESTE - pd.Timedelta(weeks=3), SENESTE, freq="W-MON"))
    assert h["hunlus"].tolist()[1:] == [0.4, 0.2, 0.6]
    assert pd.isna(h["hunlus"].iloc[0])
    assert h["nabo_snit"].iloc[0] == 0.3 and h["nabo_snit"].iloc[-1] == 0.1
    # Grænsen kommer fra områdets indberetninger – også i ugen, hvor anlægget selv ikke talte
    assert h["graense"].iloc[0] == 0.5


def test_udsving_nu_foer_og_forskel():
    u = appdata.udsving(RAA, SENESTE).set_index("lokalitet")
    assert list(u.index) == [1, 2]  # kun anlæg, der talte i seneste uge
    assert u.loc[1, "nu"] == 0.6 and u.loc[1, "foer"] == pytest.approx(0.3)  # snit af 0,2 og 0,4
    assert u.loc[1, "forskel"] == pytest.approx(0.3)
    assert u.loc[2, "forskel"] == pytest.approx(-0.2)
    assert u.loc[2, "omraade"] == 3


# --- Gennemsigtighed om indberetningen -------------------------------------------------------

def test_indberetning_taeller_mod_en_normal_uge_og_viser_omraader_uden_tal():
    """Ugen tælles mod medianen for de 8 uger før; et område uden en eneste tælling står med n = 0."""
    from lakselus import appdata
    uger = pd.date_range("2026-08-31", periods=9, freq="7D")
    raa = pd.DataFrame([{"uge_start": u, "omraade": o, "lokalitet": f"{o}-{i}", "har_talt": "Ja"}
                        for u in uger for o, n in [(1, 4), (2, 10)] for i in range(n)
                        if not (u == uger[-1] and (o == 1 or i >= 8))])
    panel = pd.DataFrame({"uge_start": list(uger) * 2, "omraade": [1] * 9 + [2] * 9})
    indb = appdata.indberetning(raa, panel)
    assert indb.loc[0].tolist() == [8, 14]
    assert indb.loc[1].tolist() == [0, 4] and indb.loc[2].tolist() == [8, 10]
    assert appdata.indberetning_tekst(8, 14, 44)[0] == "8 farms reported · 57% of a normal week"
