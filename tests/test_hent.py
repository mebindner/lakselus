"""Den ugentlige hentning: rigtige år og uger – også omkring årsskiftet."""

import datetime as dt

import pandas as pd
import pytest

from lakselus import hent


@pytest.mark.parametrize("i_dag, forventet", [
    # Midt i året: hele sidste år og til og med sidste uge i år.
    (dt.date(2026, 10, 28), {(2025, 52), (2026, 43)}),
    # ISO-uge 1 (mandag 4. jan. 2027): sidste år til og med uge 53, intet fra det nye år endnu.
    (dt.date(2027, 1, 6), {(2026, 53)}),
])
def test_henter_rigtige_uger(monkeypatch, tmp_path, i_dag, forventet):
    kald = []

    class Dato(dt.date):
        @classmethod
        def today(cls):
            return i_dag

    monkeypatch.setattr(hent.dt, "date", Dato)
    monkeypatch.setattr(hent, "DATA_RAW", tmp_path)
    monkeypatch.setattr(hent.barentswatch, "produktionsomraader", lambda: pd.DataFrame({"id": [1]}))
    tom = lambda aar, _, til_uge: kald.append((aar, til_uge)) or pd.DataFrame({"x": [1]})  # noqa: E731
    monkeypatch.setattr(hent, "AARLIGE_DATASAET", {"lusetal": tom})
    monkeypatch.setattr("sys.argv", ["hent", "--fra", str(i_dag.year - 1)])
    hent.main()
    assert set(kald) == forventet
