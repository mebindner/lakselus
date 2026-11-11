import pandas as pd
import pytest

from lakselus import regnskab


def prognose(udgang: str, pred: float, model: str = "gbm", naiv: dict | None = None) -> pd.DataFrame:
    """`naiv`: udgangsugens lusetal pr. område, som det så ud, da prognosen blev lavet."""
    start, naiv = pd.Timestamp(udgang), naiv or {}
    return pd.DataFrame([{"omraade": o, "h": h, "uge_start": start + pd.Timedelta(weeks=h), "pred": pred,
                          "lo": pred - 0.05, "hi": pred + 0.05, "model": model, "naiv": naiv.get(o)}
                         for o in (1, 2) for h in (1, 2)])


def test_ny_uge_tilfoejes_og_samme_uge_erstattes():
    a = regnskab.tilfoej(pd.DataFrame(columns=regnskab.KOLONNER), prognose("2026-10-19", 0.2))
    a = regnskab.tilfoej(a, prognose("2026-10-26", 0.3))
    assert sorted(a["lavet"].unique()) == [pd.Timestamp("2026-10-19"), pd.Timestamp("2026-10-26")]
    # Køres modellen igen i samme uge, erstattes ugens prognose – den gamle uge ligger fast
    a = regnskab.tilfoej(a, prognose("2026-10-26", 0.4, "gbm_stadier"))
    assert len(a) == 8
    assert a.loc[a["lavet"] == pd.Timestamp("2026-10-26"), "pred"].eq(0.4).all()
    assert a.loc[a["lavet"] == pd.Timestamp("2026-10-19"), "pred"].eq(0.2).all()


def test_vurdering_tager_kun_uger_der_er_kommet_og_sammenligner_med_naiv():
    a = regnskab.tilfoej(pd.DataFrame(columns=regnskab.KOLONNER), prognose("2026-10-19", 0.2, naiv={1: 0.18, 2: 0.30}))
    panel = pd.DataFrame({"uge_start": pd.to_datetime(["2026-10-19", "2026-10-19", "2026-10-26", "2026-10-26"]),
                          "omraade": [1, 2, 1, 2], "hunlus": [0.18, 0.30, 0.22, 0.40]})
    v = regnskab.vurder(a, panel)
    assert len(v) == 2 and (v["h"] == 1).all()  # 2-ugers-prognosen er ikke kommet endnu
    assert v["inde"].tolist() == [True, False]  # 0,22 ligger i 0,15–0,25; 0,40 gør ikke
    o = regnskab.opsummer(v)
    assert (o["n"], o["inde"]) == (2, 1)
    assert round(o["mae"], 3) == round((0.02 + 0.20) / 2, 3)
    assert round(o["mae_naiv"], 3) == round((0.04 + 0.10) / 2, 3)
    assert regnskab.opsummer(v.iloc[0:0]) == {"n": 0}


def test_naiv_er_udgangsugen_som_publiceret_ikke_som_rettet_bagefter():
    """Sene indberetninger retter udgangsugen. Den naive prognose må ikke få gavn af rettelsen."""
    a = regnskab.tilfoej(pd.DataFrame(columns=regnskab.KOLONNER), prognose("2026-10-19", 0.2, naiv={1: 0.10}))
    panel = pd.DataFrame({"uge_start": pd.to_datetime(["2026-10-19", "2026-10-19", "2026-10-26", "2026-10-26"]),
                          "omraade": [1, 2, 1, 2], "hunlus": [0.22, 0.30, 0.22, 0.40]})  # område 1 rettet 0,10 → 0,22
    v = regnskab.vurder(a, panel)
    assert v.set_index("omraade").loc[1, "naiv_fejl"] == pytest.approx(0.12)
    # Område 2 havde ingen tælling, da prognosen blev lavet: ingen naiv prognose, og rækken tæller ikke i sammenligningen.
    assert pd.isna(v.set_index("omraade").loc[2, "naiv"])
    o = regnskab.opsummer(v)
    assert o["n"] == 2 and o["mae_par"] == pytest.approx(0.02) and o["mae_naiv"] == pytest.approx(0.12)


def test_aeldre_prognoser_uden_naiv_kolonne_kan_stadig_arkiveres():
    gammel = prognose("2026-10-19", 0.2).drop(columns="naiv")
    a = regnskab.tilfoej(pd.DataFrame(columns=regnskab.KOLONNER), gammel)
    assert list(a.columns) == regnskab.KOLONNER and a["naiv"].isna().all()
