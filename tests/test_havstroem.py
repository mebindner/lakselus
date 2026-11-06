import base64
import json
import zlib

import numpy as np
import pandas as pd
import pytest

from lakselus import havstroem as h


def dap_svar(navn: str, type_: str, a: np.ndarray) -> bytes:
    """Et DAP2-svar som fra THREDDS: beskrivelse, 'Data:' og arrayet som XDR (længde to gange, så værdier)."""
    dim = "".join(f"[d{i} = {n}]" for i, n in enumerate(a.shape))
    hoved = f"Dataset {{\n    {type_} {navn}{dim};\n}} test;\n".encode()
    n = np.array([a.size, a.size], ">u4").tobytes()
    return hoved + b"\nData:\n" + n + a.astype(h._XDR[type_]).tobytes()


def test_laes_dods_giver_array_med_form_og_fortegn():
    a = np.array([[[-32767, 5, -3], [7, 0, 1200]]])
    ud = h.laes_dods(dap_svar("u_eastward", "Int16", a))
    assert ud.shape == (1, 2, 3)
    assert ud.tolist() == a.tolist()  # Int16 sendes som 32 bit med fortegn – fyldværdien skal overleve


def test_tidsindeks_finder_dagens_timer_og_fejler_uden_for_modellen():
    start = pd.Timestamp("2026-10-26")
    tider = np.array([(start + pd.Timedelta(hours=t)).value // 10**9 for t in range(48)], dtype=float)
    assert h.tidsindeks(tider, start) == list(h.TIMER)
    with pytest.raises(ValueError):
        h.tidsindeks(tider, start + pd.Timedelta(days=3))


def syntetisk_model():
    """Et lille modelgitter ud for Vestlandet: hav overalt, strøm mod nord på 0,2 m/s."""
    lat, lon = np.meshgrid(np.arange(59.0, 62.0, 0.03), np.arange(3.0, 6.0, 0.05), indexing="ij")
    u = np.zeros((7, *lat.shape))
    v = np.full((7, *lat.shape), 0.2)
    return {"lat": lat, "lon": lon, "u": u, "v": v}


def test_til_mercator_beholder_strommen_og_goer_resten_til_land():
    g = h.til_mercator(syntetisk_model())
    hav = np.isfinite(g["u"][0])
    assert hav.any() and not hav.all()  # resten af kysten ligger uden for det syntetiske område
    assert np.allclose(g["v"][:, hav], 0.2) and np.allclose(g["u"][:, hav], 0.0)
    r = np.argmin(abs(g["lats"] - 60.5))
    c = int(round((4.5 - g["lons"][0]) / h.GRAD))
    assert hav[r, c]                           # midt i det syntetiske hav
    assert not hav[r, int(round((10.0 - g["lons"][0]) / h.GRAD))]  # inde i landet


def test_pak_og_html_koder_land_og_fart():
    g = h.til_mercator(syntetisk_model())
    p = h.pak(g, pd.Timestamp("2026-10-26"))
    assert p["u"].dtype == np.int8
    assert (p["u"][~np.isfinite(g["u"])] == -128).all()
    assert (p["v"][np.isfinite(g["v"])] == 20).all()  # 0,2 m/s i trin af 0,01
    side = h.html(p, [[5.0, 60.0, "Test </script>", 0.3]])
    data = json.loads(side.split("const D = ")[1].split(";\n")[0].replace("<\\/", "</"))
    felt = np.frombuffer(zlib.decompress(base64.b64decode(data["stroem"])), np.int8)
    assert felt.size == 2 * p["u"].size and data["dage"][0] == ["Mon", "Mon 26 Oct"]
    assert "</script>\", 0.3" not in side      # navne kan ikke lukke script-blokken


def test_kvalitetstjek_afviser_tomt_eller_urimeligt_felt():
    g = h.til_mercator(syntetisk_model())
    assert any("havceller" in p for p in h.kvalitetstjek(g))  # det lille testområde er for lille til hele kysten
    stor = {**g, "u": np.zeros((7, 400, 400)), "v": np.full((7, 400, 400), 3.0)}
    assert any("middelfart" in p for p in h.kvalitetstjek(stor))


def test_publicerede_stroemme_passer_til_kortet():
    p = h.indlaes()
    if p is None:
        pytest.skip("ingen publicerede strømme")
    assert p["u"].shape == p["v"].shape and p["u"].shape[0] == 7
    assert not h.kvalitetstjek({"u": np.where(p["u"] == -128, np.nan, p["u"] * p["skala"]),
                                "v": np.where(p["v"] == -128, np.nan, p["v"] * p["skala"])})


def test_fart_ved_anlaeg_regner_km_pr_doegn_og_udelader_fjordanlaeg():
    p = h.pak(h.til_mercator(syntetisk_model()), pd.Timestamp("2026-10-26"))
    anlaeg = pd.DataFrame({"lat": [60.5, 61.0], "lon": [4.5, 10.0]})  # i havet · langt inde i landet
    ud = h.fart_ved_anlaeg(p, anlaeg)
    assert ud["km_dag"].iloc[0] == pytest.approx(0.2 * 86.4)  # 0,2 m/s ≈ 17 km pr. døgn
    assert pd.isna(ud["km_dag"].iloc[1])


def _fokus_data():
    uge, forrige = pd.Timestamp("2026-10-26"), pd.Timestamp("2026-10-19")
    raa = pd.DataFrame({
        "lokalitet": [1, 2, 3, 3], "lokalitet_navn": ["Skorpo", "Fjordbunn", "Stille", "Stille"],
        "uge_start": [uge, uge, forrige, uge], "har_talt": ["Ja", "Ja", "Ja", "Nei"],
        "hunlus": [0.31, 0.12, 0.2, None], "omraade": [3.0, 3.0, 4.0, 4.0],
        "lat": [59.8, 60.1, 61.0, 61.0], "lon": [5.2, 5.6, 5.0, 5.0],
    })
    fart = pd.DataFrame({"lokalitet": [1, 2], "km_dag": [6.4, np.nan]})
    return raa, fart, uge, {3: "Karmøy til Sotra", 4: "Nordhordland til Stadt"}


def test_fokus_paa_anlaeg_viser_lusetal_og_fart():
    raa, fart, uge, navne = _fokus_data()
    f = h.fokus(raa, fart, uge, navne, po=3, lokalitet=1)  # anlægget vinder over området
    assert f == {"type": "site", "lon": 5.2, "lat": 59.8, "navn": "Skorpo",
                 "linje": "0.31 adult female lice per fish in week 44 · water moved about 6 km a day"}
    assert "narrower than the map's grid" in h.fokus(raa, fart, uge, navne, lokalitet=2)["linje"]
    # Talte ikke i ugen: seneste kendte position og en ærlig linje
    stille = h.fokus(raa, fart, uge, navne, lokalitet=3)
    assert (stille["lat"], stille["linje"]) == (61.0, "No lice count in week 44")


def test_fokus_paa_omraade_giver_ramme_og_ukendte_valg_giver_hele_kysten():
    raa, fart, uge, navne = _fokus_data()
    assert h.fokus(raa, fart, uge, navne, po=3) == {"type": "po", "navn": "PO 3 · Karmøy til Sotra",
                                                    "ramme": [5.2, 59.8, 5.6, 60.1]}
    # Ingen talte i ugen: rammen om områdets kendte anlæg, og navnet siger det
    assert h.fokus(raa, fart, uge, navne, po=4) == {"type": "po", "navn": "PO 4 · Nordhordland til Stadt · no counts in week 44",
                                                    "ramme": [5.0, 61.0, 5.0, 61.0]}
    assert h.fokus(raa, fart, uge, navne, lokalitet=999) is None
    assert h.fokus(raa, fart, uge, navne) is None
