import numpy as np
import pandas as pd
import pytest

from lakselus import biomasse, modeller as m


def raa(rader):
    """Rådata i Fiskeridirektoratets format: (år, måned, område, art, fisk, kg, utsat, slagtet)."""
    return pd.DataFrame(rader, columns=["ÅR", "MÅNED_KODE", "PO_KODE", "ARTSID", "BEHFISK_STK", "BIOMASSE_KG",
                                        "UTSETT_SMOLT_STK", "UTTAK_STK"]).assign(DØDFISK_STK=0)


def test_arter_laegges_sammen_og_rader_uden_omraade_udelades():
    m_ = biomasse.pr_omraade(raa([
        (2026, 8, 3, "LAKS", 1_000_000, 3_000_000, 0, 0),
        (2026, 8, 3, "REGNBUEØRRET", 200_000, 600_000, 0, 0),
        (2026, 8, np.nan, "LAKS", 50_000, 100_000, 0, 0),   # skjult område
        (2026, 9, 3, "LAKS", 900_000, 2_900_000, 100_000, 300_000),
    ]))
    assert m_["omraade"].unique().tolist() == [3]
    assert m_["fisk"].tolist() == [1_200_000, 900_000]
    assert m_["vaegt"].iloc[0] == 3.0
    assert round(m_["fisk_d1"].iloc[1], 3) == -0.25
    assert round(m_["slagtet3"].iloc[1], 3) == round(300_000 / 900_000, 3)
    assert m_["publiceret"].tolist() == [pd.Timestamp("2026-09-20"), pd.Timestamp("2026-10-20")]


def test_ugepanelet_ser_kun_maaneder_der_var_publiceret():
    maaneder = biomasse.pr_omraade(raa([
        (2026, 8, 3, "LAKS", 1_000_000, 3e6, 0, 0),   # publiceret 20. sept.
        (2026, 9, 3, "LAKS", 2_000_000, 6e6, 0, 0),   # publiceret 20. okt.
    ]))
    uger = pd.to_datetime(["2026-09-07", "2026-10-05", "2026-10-12", "2026-10-19"])
    panel = pd.DataFrame({"omraade": 3, "uge_start": uger, "hunlus": 0.2})
    p = biomasse.til_panel(panel, maaneder).set_index("uge_start")["fisk"]
    # Uge 2026-09-07 forudsiges 14. sept. – før august er publiceret.
    assert np.isnan(p["2026-09-07"])
    # Uge 2026-10-05 forudsiges 12. okt.: august er kendt, september ikke.
    assert p["2026-10-05"] == p["2026-10-12"] == 1_000_000
    # Uge 2026-10-19 forudsiges 26. okt.: september er publiceret.
    assert p["2026-10-19"] == 2_000_000


def test_lusebyrde_er_lus_pr_fisk_gange_antal_fisk():
    uger = pd.date_range("2026-01-05", periods=3, freq="W-MON")
    panel = pd.DataFrame({"omraade": 3, "uge_start": uger, "hunlus": [0.1, 0.2, 0.4], "temp": 8.0, "n_lok": 10,
                          "fisk": 2_000_000})
    f = m.features(panel, 1)
    assert np.allclose(f["lusebyrde"], np.log1p([0.2, 0.4, 0.8]))
    # Uden fiskebestanden findes kolonnerne stadig, men er tomme – modellen kører videre.
    assert m.features(panel.drop(columns="fisk"), 1)[m.BIOMASSE].isna().all().all()


def test_app_kopien_giver_samme_maanedstabel_som_raadata(monkeypatch, tmp_path):
    """Fejler hentningen i den ugentlige kørsel, bruger modellen den publicerede kopi i data/app."""
    if not biomasse.RAA_FIL.exists() or not biomasse.APP_FIL.exists():
        pytest.skip("kræver både lokale rådata og publicerede app-data")
    fra_raa = biomasse.indlaes()
    monkeypatch.setattr(biomasse, "RAA_FIL", tmp_path / "findes_ikke.csv")
    fra_app = biomasse.indlaes()
    faelles = fra_raa["maaned"] <= fra_app["maaned"].max()
    pd.testing.assert_frame_equal(fra_raa[faelles].reset_index(drop=True), fra_app, check_dtype=False)
