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
