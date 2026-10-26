"""Kvalitetstests for modeller og evaluering: lækage, korrekthed, læring og statistisk kalibrering."""

from functools import partial

import numpy as np
import pandas as pd
import pytest

from lakselus import evaluering as ev, modeller as m


def syntetisk_panel(n_uger=200, n_omr=3, seed=0, momentum=0.0, saeson=0.1, stoej=0.01):
    """Panel med sæson, valgfri momentum (ændring afhænger af sidste ændring) og støj."""
    rng = np.random.default_rng(seed)
    uger = pd.date_range("2019-01-07", periods=n_uger, freq="W-MON")
    rows = []
    for o in range(1, n_omr + 1):
        uge = uger.isocalendar().week.to_numpy().clip(max=52)
        basis = 0.2 + saeson * np.sin(2 * np.pi * uge / 52 + o)
        y = np.empty(n_uger)
        y[:2] = basis[:2]
        for t in range(2, n_uger):
            d_sidst = y[t - 1] - y[t - 2]
            y[t] = y[t - 1] + (basis[t] - basis[t - 1]) + momentum * d_sidst + rng.normal(0, stoej)
        rows.append(pd.DataFrame({"omraade": o, "uge_start": uger, "hunlus": y.clip(0),
                                  "temp": 8 + 4 * np.sin(2 * np.pi * uge / 52), "n_lok": 50}))
    return pd.concat(rows, ignore_index=True)


# --- Lækage ---------------------------------------------------------------------------

def test_features_er_kausale():
    """Features for uge t er de samme, uanset om data efter t findes (undtagen sæsonprofil og mål)."""
    p = syntetisk_panel()
    t = p["uge_start"].unique()[120]
    fuld = m.features(p, 2).set_index(["omraade", "uge_start"])
    kun_fortid = m.features(p[p["uge_start"] <= t], 2).set_index(["omraade", "uge_start"])
    kol = [k for k in m.NUMERISKE + m.NATIONALE if k != "saes_d"]
    pd.testing.assert_frame_equal(fuld.loc[kun_fortid.index, kol], kun_fortid[kol])


@pytest.mark.parametrize("navn", ["saeson_justeret", "ridge", "gbm", "ensemble"])
def test_backtest_laekker_ikke_fremtid(navn):
    """Ødelægges alle data efter uge T, skal prognoser lavet til og med T være uændrede."""
    p = syntetisk_panel(n_uger=170)
    T = p["uge_start"].unique()[150]
    oedelagt = p.copy()
    oedelagt.loc[oedelagt["uge_start"] > T, "hunlus"] = 99.0
    oedelagt.loc[oedelagt["uge_start"] > T, "temp"] = -50.0

    start = p["uge_start"].unique()[130]
    a = ev.backtest(p, m.kandidater()[navn], horisonter=(1, 3), start=start)
    b = ev.backtest(oedelagt, m.kandidater()[navn], horisonter=(1, 3), start=start)
    sammen = a.merge(b, on=["omraade", "origin", "h"], suffixes=("", "_b"))
    sammen = sammen[sammen["origin"] <= T]
    assert len(sammen) > 0
    np.testing.assert_allclose(sammen["pred"], sammen["pred_b"])


# --- Korrekthed og læring ---------------------------------------------------------------

def test_saeson_justeret_rammer_ren_saeson():
    """Uden støj gentager sæsonen sig præcist, så sæsonjusteret naiv skal ramme (næsten) perfekt."""
    p = syntetisk_panel(n_uger=260, stoej=0.0)
    res = ev.backtest(p, m.saeson_justeret, horisonter=(2,), start=p["uge_start"].unique()[160])
    assert (res["pred"] - res["faktisk"]).abs().mean() < 0.01


@pytest.mark.parametrize("fabrik", [m._ridge, partial(m._gbm, max_iter=150)])
def test_modeller_laerer_momentum_og_slaar_naiv(fabrik):
    """Når ændringer fortsætter (momentum), skal en lærende model slå den naive prognose klart."""
    p = syntetisk_panel(n_uger=260, momentum=0.7, saeson=0.05, stoej=0.02, seed=3)
    start = p["uge_start"].unique()[180]
    res = {"naiv": ev.backtest(p, ev.naiv, horisonter=(1, 2), start=start),
           "model": ev.backtest(p, m.DirekteModel(fabrik), horisonter=(1, 2), start=start)}
    assert (ev.skill(ev.mae(res))["model"] > 0.1).all()


def test_ensemble_er_gennemsnit():
    p = syntetisk_panel()
    f1 = lambda hist, h: pd.Series({1: 1.0, 2: 2.0})  # noqa: E731
    f2 = lambda hist, h: pd.Series({1: 3.0, 2: 4.0})  # noqa: E731
    assert m.Ensemble(f1, f2)(p, 1).to_dict() == {1: 2.0, 2: 3.0}


def test_prognoser_er_ikke_negative():
    p = syntetisk_panel(saeson=0.3)
    for navn, f in m.kandidater().items():
        assert (f(p, 4) >= 0).all(), navn


# --- Statistik --------------------------------------------------------------------------

def _res(fejl, h=1, seed=0):
    rng = np.random.default_rng(seed)
    n = len(fejl)
    origin = pd.date_range("2023-01-02", periods=n, freq="W-MON")
    faktisk = rng.normal(0.2, 0.05, n)
    return pd.DataFrame({"omraade": 1, "origin": origin, "h": h, "maal": origin + pd.Timedelta(weeks=h),
                         "pred": faktisk + fejl, "faktisk": faktisk})


def test_dm_test_ens_prognoser_giver_ingen_forskel():
    r = _res(np.random.default_rng(1).normal(0, 0.02, 150))
    stat, p = ev.dm_test(r, r, h=1)
    assert p == 1.0


def test_dm_test_finder_klart_bedre_model():
    rng = np.random.default_rng(2)
    god, daarlig = _res(rng.normal(0, 0.01, 150)), _res(rng.normal(0, 0.05, 150))
    stat, p = ev.dm_test(god, daarlig, h=1)
    assert stat < 0 and p < 0.01


def test_dm_test_kalibreret_under_nulhypotesen():
    """To lige gode modeller: p < 0,05 i ca. 5 % af tilfældene (ikke langt flere)."""
    afvist = 0
    for s in range(200):
        rng = np.random.default_rng(100 + s)
        a, b = _res(rng.normal(0, 0.03, 120)), _res(rng.normal(0, 0.03, 120))
        afvist += ev.dm_test(a, b, h=1)[1] < 0.05
    assert afvist / 200 < 0.10


def test_intervaller_har_nominel_daekning():
    """Med stationære fejl skal et 80 %-interval dække ca. 80 % af udfaldene."""
    r = _res(np.random.default_rng(4).normal(0, 0.03, 600))
    d = ev.daekning(ev.intervaller(r, niveau=0.8, min_obs=52))
    assert 0.74 < d.loc[1] < 0.86


def test_intervaller_bruger_kun_kendte_fejl():
    """Ændres fejl for prognoser, hvis måluge ligger efter et tidspunkt, ændres tidligere intervaller ikke."""
    r = _res(np.random.default_rng(5).normal(0, 0.03, 200))
    graense = r["origin"].iloc[120]
    r2 = r.copy()
    r2.loc[r2["maal"] > graense, "pred"] += 5.0
    i1 = ev.intervaller(r, min_obs=52).set_index("origin")
    i2 = ev.intervaller(r2, min_obs=52).set_index("origin")
    foer = i1.index[i1.index <= graense]
    np.testing.assert_allclose(i1.loc[foer, "lo_resid"], i2.loc[foer, "lo_resid"])
    np.testing.assert_allclose(i1.loc[foer, "hi_resid"], i2.loc[foer, "hi_resid"])


def test_modelvalg_ser_kun_paa_validering():
    """En model, der er bedst på test men dårligst på validering, må ikke blive valgt."""
    from lakselus import modelrapport

    rng = np.random.default_rng(7)
    origin = pd.date_range("2023-01-02", "2026-06-29", freq="W-MON")
    faktisk = rng.normal(0.2, 0.05, len(origin))
    er_val = origin <= pd.Timestamp(ev.VALIDERING[1])
    fejl = {"naiv": np.full(len(origin), 0.04), "saeson_naiv": np.full(len(origin), 0.06),
            "god_paa_val": np.where(er_val, 0.01, 0.05), "god_paa_test": np.where(er_val, 0.05, 0.001)}
    res = pd.concat([
        pd.DataFrame({"model": k, "omraade": 1, "origin": origin, "h": h, "maal": origin + pd.Timedelta(weeks=h),
                      "pred": faktisk + f, "faktisk": faktisk})
        for k, f in fejl.items() for h in (1, 2, 3, 4)
    ])
    assert modelrapport.vaelg_model(res) == "god_paa_val"
