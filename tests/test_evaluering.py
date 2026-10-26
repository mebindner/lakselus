import pandas as pd

from lakselus.evaluering import backtest, mae, naiv, saeson_naiv


def _panel():
    uger = pd.date_range("2022-01-03", periods=60, freq="W-MON")
    return pd.DataFrame(
        {"omraade": 1, "uge_start": uger, "hunlus": [float(i) for i in range(60)]}
    )


def test_naiv_bruger_seneste_uge():
    p = _panel()
    assert naiv(p.iloc[:10], h=3).loc[1] == 9.0


def test_saeson_naiv_bruger_samme_uge_sidste_aar():
    p = _panel()
    # origin = uge 55 (indeks 55), h = 2 → måluge 57 → 52 uger før = indeks 5
    assert saeson_naiv(p.iloc[:56], h=2).loc[1] == 5.0


def test_backtest_kender_ikke_fremtiden_og_naiv_fejl_er_h():
    p = _panel()
    res = backtest(p, naiv, horisonter=(1, 4), start="2022-06-06")
    assert (res["maal"] > res["origin"]).all()
    tabel = mae({"naiv": res})
    assert tabel.loc[1, "naiv"] == 1.0
    assert tabel.loc[4, "naiv"] == 4.0
