"""Hændelsesstudiet af behandlinger: rigtige forløb, isolation og kontrolgruppe på et konstrueret eksempel."""

import numpy as np
import pandas as pd

from lakselus import behandlingseffekt as be


def _lusetal(n_lok: int = 40, n_uger: int = 30) -> pd.DataFrame:
    """Lokaliteter med konstant lusetal 0,4 – undtagen at behandlede halveres fra behandlingsugen."""
    uger = pd.date_range("2025-01-06", periods=n_uger, freq="W-MON")
    rows = [(lok, u, 0.4) for lok in range(1, n_lok + 1) for u in uger]
    return pd.DataFrame(rows, columns=["lokalitet", "uge_start", "hunlus"]).assign(har_talt="Ja")


def _behandling(lok: int, uge: int, type_: str = "termisk behandling", omfang: str = "hele lokaliteten") -> dict:
    return {"År": 2025, "Uke": uge, "Lokalitetsnummer": lok, "Type behandling": type_, "Omfang": omfang,
            "ProduksjonsområdeId": 3}


def test_effekt_og_kontrol():
    raa = _lusetal()
    behandlede = range(1, be.MIN_HAENDELSER + 1)
    beh = pd.DataFrame([_behandling(lok, 10) for lok in behandlede])
    # Behandlingen halverer lusetallet fra og med behandlingsugen (ISO-uge 10 = 3. marts 2025).
    efter = raa["lokalitet"].isin(behandlede) & (raa["uge_start"] >= "2025-03-03")
    raa.loc[efter, "hunlus"] = 0.2

    alle = be.effekt_tabel(raa, beh)
    assert set(alle["omraade"]) == {0, 3}  # hele kysten og det ene område med nok behandlinger
    t = alle[alle["omraade"] == 0].set_index("k")
    assert (t["type"] == "Thermal").all() and (t["n"] == be.MIN_HAENDELSER).all()
    assert t.loc[-1, "median"] == 1.0
    np.testing.assert_allclose(t.loc[0:6, "median"], 0.5)
    np.testing.assert_allclose(t["kontrol"], 1.0)  # ubehandlede lokaliteter ligger fladt


def test_kun_isolerede_behandlinger_af_hele_lokaliteten_taeller():
    beh = pd.DataFrame([
        _behandling(1, 10),                                  # tæller
        _behandling(2, 10), _behandling(2, 13),               # ny behandling inden for 6 uger – udelades
        _behandling(3, 10, omfang="deler av lokaliteten"),   # kun en del af lokaliteten – udelades
        _behandling(4, 10), _behandling(4, 10, "mekanisk behandling"),  # to typer samme uge – udelades
    ])
    assert be.haendelser(beh)["lokalitet"].tolist() == [1]
