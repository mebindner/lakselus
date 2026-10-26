"""Den hostede app bruger kompakte data i data/app – de skal give de samme tal som rådata."""

import pandas as pd
import pytest

from lakselus import data
from lakselus.config import DATA_RAW


@pytest.mark.skipif(not any(DATA_RAW.glob("lusetal_*.csv")) or not data.APP_LUSETAL.exists(),
                    reason="kræver både lokale rådata og publicerede app-data")
def test_app_data_giver_samme_panel_som_raadata(monkeypatch, tmp_path):
    fra_raa = data.ugentligt_panel(data.indlaes_raa())
    monkeypatch.setattr(data, "DATA_RAW", tmp_path)  # som på Streamlit Cloud: ingen rådata
    fra_app = data.ugentligt_panel(data.indlaes_raa())
    # Rådata kan være nyere end sidst publicerede app-data; sammenlign de uger, begge har.
    faelles = fra_raa["uge_start"] <= fra_app["uge_start"].max()
    pd.testing.assert_frame_equal(fra_raa[faelles].reset_index(drop=True), fra_app, check_exact=False, rtol=1e-5)
