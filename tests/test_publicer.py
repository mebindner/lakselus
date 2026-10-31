"""Den hostede app bruger kompakte data i data/app – de skal give de samme tal som rådata."""

import pandas as pd
import pytest

from lakselus import data
from lakselus.config import DATA_RAW


@pytest.mark.skipif(not any(DATA_RAW.glob("lusetal_*.csv")) or not data.APP_LUSETAL.exists(),
                    reason="kræver både lokale rådata og publicerede app-data")
def test_app_data_giver_samme_panel_som_raadata(monkeypatch, tmp_path):
    fra_raa = data.ugentligt_panel(data.indlaes_raa(), data.indlaes_behandlinger())
    monkeypatch.setattr(data, "DATA_RAW", tmp_path)  # som på Streamlit Cloud: ingen rådata
    fra_app = data.ugentligt_panel(data.indlaes_raa(), data.indlaes_behandlinger())
    # Rådata kan være nyere end sidst publicerede app-data; sammenlign de uger, begge har.
    faelles = fra_raa["uge_start"] <= fra_app["uge_start"].max()
    pd.testing.assert_frame_equal(fra_raa[faelles].reset_index(drop=True), fra_app, check_exact=False, rtol=1e-5)


def test_behandlinger_taeller_hver_lokalitet_en_gang_pr_uge():
    """To behandlinger samme uge på samme lokalitet er én behandlet lokalitet; medicin tælles for sig."""
    raa = pd.DataFrame({
        "År": [2026] * 4, "Uke": [40, 40, 40, 41], "Lokalitetsnummer": [1, 1, 2, 1],
        "Tiltak": ["ikke-medikamentell", "medikamentell", "ikke-medikamentell", "ikke-medikamentell"],
        "ProduksjonsområdeId": [3, 3, 3, 3],
    })
    b = data.behandlinger_pr_omraade(raa).set_index("uge_start")
    assert b.loc["2026-09-28", ["n_beh", "n_med"]].tolist() == [2, 1]
    assert b.loc["2026-10-05", ["n_beh", "n_med"]].tolist() == [1, 0]


# --- Kvalitetskontrol før publicering --------------------------------------------------------

def _uge(uge_start: str, n_lok: int = 400, n_omr: int = 13, hunlus: float = 0.2) -> pd.DataFrame:
    return pd.DataFrame({"uge_start": pd.Timestamp(uge_start), "lokalitet": range(n_lok),
                         "omraade": [i % n_omr + 1 for i in range(n_lok)], "hunlus": hunlus})


def test_kvalitetstjek_godkender_normal_uge():
    from lakselus.publicer import kvalitetstjek
    gammel = _uge("2026-10-12")
    ny = pd.concat([_uge("2026-10-12"), _uge("2026-10-19")])
    assert kvalitetstjek(ny, gammel, True, True) == []


@pytest.mark.parametrize("ny, beskrivelse", [
    (pd.concat([_uge("2026-10-12"), _uge("2026-10-19", n_lok=120)]), "lokaliteter"),
    (pd.concat([_uge("2026-10-12"), _uge("2026-10-19", n_omr=6)]), "produktionsområder"),
    (pd.concat([_uge("2026-10-12"), _uge("2026-10-19", hunlus=-1.0)]), "lusetal uden for"),
    (_uge("2026-10-05"), "ældre end den publicerede"),
])
def test_kvalitetstjek_stopper_forkerte_data(ny, beskrivelse):
    from lakselus.publicer import kvalitetstjek
    gammel = _uge("2026-10-12")
    assert any(beskrivelse in p for p in kvalitetstjek(ny, gammel, True, True))


def test_kvalitetstjek_stopper_hvis_behandlinger_forsvinder():
    from lakselus.publicer import kvalitetstjek
    ny = _uge("2026-10-19")
    assert any("behandlingsdata" in p for p in kvalitetstjek(ny, None, False, True))


# --- Sammenhæng i de publicerede modeldata ---------------------------------------------------

@pytest.mark.skipif(not (data.DATA_APP / "backtest.parquet").exists(), reason="kræver publiceret backtest")
def test_publiceret_prognose_bruger_den_valgte_model():
    """Prognosen, appen viser, skal være lavet med den model, valideringen peger på – og starte ugen efter data."""
    from lakselus import modelrapport

    res = pd.read_parquet(modelrapport.BACKTEST_FIL)
    prognose = pd.read_parquet(modelrapport.PROGNOSE_FIL)
    assert set(prognose["model"]) == {modelrapport.vaelg_model(res)}
    assert sorted(prognose["h"].unique()) == [1, 2, 3, 4]
    assert prognose["omraade"].nunique() == 13
    assert (prognose["lo"] <= prognose["pred"]).all() and (prognose["pred"] <= prognose["hi"]).all()
    # Backtesten slutter 1 uge før seneste data (målet for h=1 skal være kendt); prognosen starter ugen efter data.
    assert prognose["uge_start"].min() == res["origin"].max() + pd.Timedelta(weeks=2)
