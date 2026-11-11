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
                                  "temp": 8 + 4 * np.sin(2 * np.pi * uge / 52), "n_lok": 50,
                                  "n_beh": rng.integers(0, 10, n_uger),
                                  "mob": 2 * y.clip(0) + rng.normal(0, stoej, n_uger).clip(0),
                                  "fast": y.clip(0) + rng.normal(0, stoej, n_uger).clip(0)}))
    return pd.concat(rows, ignore_index=True)


# --- Lækage ---------------------------------------------------------------------------

def test_features_er_kausale():
    """Features for uge t er de samme, uanset om data efter t findes (undtagen sæsonprofil og mål)."""
    p = syntetisk_panel()
    t = p["uge_start"].unique()[120]
    fuld = m.features(p, 2).set_index(["omraade", "uge_start"])
    kun_fortid = m.features(p[p["uge_start"] <= t], 2).set_index(["omraade", "uge_start"])
    kol = [k for k in m.NUMERISKE + m.NATIONALE + m.BEHANDLINGER + m.STADIER if k != "saes_d"]
    pd.testing.assert_frame_equal(fuld.loc[kun_fortid.index, kol], kun_fortid[kol])


def test_saesonfeature_kender_ikke_eget_maal():
    """En træningsrækkes saes_d må ikke ændre sig, når netop dens eget mål (y(t+h)) ændres."""
    p = syntetisk_panel(n_uger=200)
    h, raekke = 2, p.index[(p["omraade"] == 1)][60]
    mod = p.copy()
    mod.loc[raekke + h, "hunlus"] += 5.0  # målet for rækken; påvirker også andre rækkers d-features
    a = m.features(p, h).loc[raekke, "saes_d"]
    b = m.features(mod, h).loc[raekke, "saes_d"]
    assert a == pytest.approx(b)


def _alle_modeller():
    return m.kandidater() | m.kvantil_modeller(m.kandidater()["gbm_stadier"])


@pytest.mark.parametrize("navn", ["saeson_justeret", "ridge", "gbm", "gbm_beh", "gbm_stadier", "gbm_biomasse", "ensemble",
                                  "kvantil_lo", "kvantil_hi"])
def test_backtest_laekker_ikke_fremtid(navn):
    """Ødelægges alle data efter uge T, skal prognoser lavet til og med T være uændrede."""
    p = syntetisk_panel(n_uger=170)
    T = p["uge_start"].unique()[150]
    oedelagt = p.copy()
    oedelagt.loc[oedelagt["uge_start"] > T, "hunlus"] = 99.0
    oedelagt.loc[oedelagt["uge_start"] > T, "temp"] = -50.0
    oedelagt.loc[oedelagt["uge_start"] > T, "n_beh"] = 999
    oedelagt.loc[oedelagt["uge_start"] > T, ["mob", "fast"]] = 77.0

    start = p["uge_start"].unique()[130]
    a = ev.backtest(p, _alle_modeller()[navn], horisonter=(1, 3), start=start)
    b = ev.backtest(oedelagt, _alle_modeller()[navn], horisonter=(1, 3), start=start)
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
    np.testing.assert_allclose(i1.loc[foer, "lo_rel"], i2.loc[foer, "lo_rel"])
    np.testing.assert_allclose(i1.loc[foer, "hi_rel"], i2.loc[foer, "hi_rel"])


def test_intervallet_vokser_med_niveauet():
    """Fejl, der er proportionale med niveauet, skal give et interval, der også er det – og dækker ved alle niveauer."""
    rng = np.random.default_rng(6)
    n = 800
    origin = pd.date_range("2010-01-04", periods=n, freq="W-MON")
    pred = rng.choice([0.05, 0.4], n)
    faktisk = pred * (1 + rng.normal(0, 0.3, n))
    r = pd.DataFrame({"omraade": 1, "origin": origin, "h": 1, "maal": origin + pd.Timedelta(weeks=1),
                      "pred": pred, "faktisk": faktisk})
    iv = ev.intervaller(r, min_obs=52)
    bredde = (iv["hi"] - iv["lo"]).groupby(iv["pred"]).median()
    assert 6 < bredde[0.4] / bredde[0.05] < 9   # (0,4 + 0,01) / (0,05 + 0,01) ≈ 6,8
    inde = (iv["faktisk"] >= iv["lo"]) & (iv["faktisk"] <= iv["hi"])
    assert (inde.groupby(iv["pred"]).mean().between(0.72, 0.88)).all()


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


# --- Intervaller med kvantilregression (CQR) ---------------------------------------------

def test_kvantilmodeller_er_ikke_kandidater_og_kan_ikke_vaelges():
    """Kvantilmodellerne giver intervallet; de må hverken stå i tabellerne eller blive valgt som prognose."""
    from lakselus import modelrapport

    # Kvantilmodellerne har her de mindste fejl; de må alligevel ikke blive valgt.
    fejl = {"naiv": 0.04, "saeson_naiv": 0.05, "gbm": 0.02, "kvantil_lo": 0.001, "kvantil_hi": 0.001}
    res = pd.concat([_res(np.full(60, f), seed=1).assign(model=k) for k, f in fejl.items()])
    assert list(modelrapport.som_dict(res)) == ["naiv", "saeson_naiv", "gbm"]
    assert modelrapport.vaelg_model(res) == "gbm"
    assert modelrapport.kvantiler(res) is not None
    assert modelrapport.kvantiler(res[res["model"] != "kvantil_hi"]) is None


def test_cqr_udvider_for_smalle_kvantiler_til_nominel_daekning():
    """Er kvantilmodellernes interval for smalt, skal den konforme korrektion bringe dækningen op på ca. 80 %."""
    rng = np.random.default_rng(7)
    n = 600
    origin = pd.date_range("2010-01-04", periods=n, freq="W-MON")
    pred = np.full(n, 0.2)
    res = pd.DataFrame({"omraade": 1, "origin": origin, "h": 1, "maal": origin + pd.Timedelta(weeks=1),
                        "pred": pred, "faktisk": pred + rng.normal(0, 0.05, n)})
    kv = res[["omraade", "origin", "h", "maal"]].assign(pred_lo=pred - 0.02, pred_hi=pred + 0.02)  # alt for smalt
    iv = ev.cqr_intervaller(res, kv, min_obs=52)
    assert 0.74 < ev.daekning(iv).loc[1] < 0.86
    assert ((iv["lo"] <= iv["pred"]) & (iv["pred"] <= iv["hi"])).all()


def test_cqr_bruger_kun_kendte_fejl():
    rng = np.random.default_rng(8)
    n = 200
    origin = pd.date_range("2010-01-04", periods=n, freq="W-MON")
    res = pd.DataFrame({"omraade": 1, "origin": origin, "h": 1, "maal": origin + pd.Timedelta(weeks=1),
                        "pred": 0.2, "faktisk": 0.2 + rng.normal(0, 0.05, n)})
    kv = res[["omraade", "origin", "h", "maal"]].assign(pred_lo=0.15, pred_hi=0.25)
    graense = origin[120]
    res2 = res.copy()
    res2.loc[res2["maal"] > graense, "faktisk"] += 5.0
    a = ev.cqr_intervaller(res, kv, min_obs=52).set_index("origin")["hi"]
    b = ev.cqr_intervaller(res2, kv, min_obs=52).set_index("origin")["hi"]
    np.testing.assert_allclose(a[a.index <= graense], b[b.index <= graense])


def test_kvantiler_der_krydser_sorteres_og_omslutter_prognosen():
    lo, hi = ev.raa_kvantiler(np.array([0.3, 0.1]), np.array([0.2, 0.15]), np.array([0.25, 0.2]))
    np.testing.assert_allclose(lo, [0.2, 0.1])
    np.testing.assert_allclose(hi, [0.3, 0.2])
