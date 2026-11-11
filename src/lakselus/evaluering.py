"""Baselines, rullende backtest og statistisk evaluering.

En forecaster er en funktion  f(historik, h) -> pd.Series  (indeks = omraade), der kun må se
`historik` (panelet til og med forecast-ugen) og forudsiger hunlus h uger frem.

Indhold
1. Baselines            – naiv (sidste uge) og sæson-naiv (samme uge sidste år)
2. Backtest             – expanding window, uge for uge, med kun de data, der fandtes dengang
3. Fejlmål              – MAE og skill mod den naive prognose
4. Perioder og test     – validering/test-opdeling og Diebold–Mariano-test
5. Prognoseintervaller  – konformaliseret kvantilregression (CQR); reserve: modellens egne fejl, skaleret med niveauet
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

Forecaster = Callable[[pd.DataFrame, int], pd.Series]


# --- 1. Baselines ---------------------------------------------------------------------------

def naiv(historik: pd.DataFrame, h: int) -> pd.Series:
    """Samme værdi som i forecast-ugen."""
    sidste = historik["uge_start"].max()
    return historik[historik["uge_start"] == sidste].set_index("omraade")["hunlus"]


def saeson_naiv(historik: pd.DataFrame, h: int) -> pd.Series:
    """Samme uge sidste år (52 uger før måluge)."""
    maal = historik["uge_start"].max() + pd.Timedelta(weeks=h - 52)
    return historik[historik["uge_start"] == maal].set_index("omraade")["hunlus"]


# --- 2. Backtest ----------------------------------------------------------------------------

def backtest(
    panel: pd.DataFrame,
    forecaster: Forecaster,
    horisonter: tuple[int, ...] = (1, 2, 3, 4),
    start: str = "2023-01-02",
) -> pd.DataFrame:
    """Expanding window: for hver uge fra `start` forudsiges 1..H uger frem med data til og med ugen."""
    faktisk = panel.set_index(["uge_start", "omraade"])["hunlus"]
    sidste = panel["uge_start"].max()
    rows = []
    for origin in sorted(panel.loc[panel["uge_start"] >= start, "uge_start"].unique()):
        historik = panel[panel["uge_start"] <= origin]
        for h in horisonter:
            maal = origin + pd.Timedelta(weeks=h)
            if maal > sidste:
                continue
            pred = forecaster(historik, h)
            for omraade, y_hat in pred.items():
                rows.append((omraade, origin, h, maal, y_hat, faktisk.get((maal, omraade))))
    res = pd.DataFrame(rows, columns=["omraade", "origin", "h", "maal", "pred", "faktisk"])
    return res.dropna(subset=["pred", "faktisk"])


# --- 3. Fejlmål -----------------------------------------------------------------------------

def mae(resultater: dict[str, pd.DataFrame], efter: list[str] = ["h"]) -> pd.DataFrame:
    """MAE pr. model (kolonner) grupperet efter fx ['h'] eller ['omraade', 'h'].

    Kun (omraade, origin, h) som alle modeller har forudsagt indgår, så sammenligningen er fair.
    """
    noegle = ["omraade", "origin", "h"]
    faelles = None
    for df in resultater.values():
        idx = df.set_index(noegle).index
        faelles = idx if faelles is None else faelles.intersection(idx)
    ud = {}
    for navn, df in resultater.items():
        df = df.set_index(noegle).loc[faelles].reset_index()
        ud[navn] = (df["pred"] - df["faktisk"]).abs().groupby([df[k] for k in efter]).mean()
    return pd.DataFrame(ud)


def skill(mae_tabel: pd.DataFrame, reference: str = "naiv") -> pd.DataFrame:
    """1 − MAE_model / MAE_reference. Positiv = bedre end reference."""
    return 1 - mae_tabel.div(mae_tabel[reference], axis=0)


# --- 4. Perioder og test ---------------------------------------------------------------------

VALIDERING = ("2023-01-01", "2024-12-31")  # modelvalg og indstillinger
TEST = ("2025-01-01", "2100-01-01")       # rapporteres én gang, efter valget er truffet


def periode(res: pd.DataFrame, fra_til: tuple[str, str]) -> pd.DataFrame:
    """Rækker hvis forecast-uge (origin) ligger i perioden."""
    return res[(res["origin"] >= fra_til[0]) & (res["origin"] <= fra_til[1])]


def dm_test(res_model: pd.DataFrame, res_ref: pd.DataFrame, h: int) -> tuple[float, float]:
    """Diebold–Mariano-test af absolut fejl, model mod reference, for én horisont.

    Tabet aggregeres pr. forecast-uge (gennemsnit over områder), så testen kører på én tidsserie.
    Variansen estimeres med Newey–West (h−1 lags), og Harvey–Leybourne–Newbold-korrektionen anvendes.
    Returnerer (DM-statistik, tosidet p-værdi). Negativ statistik = modellen har lavere fejl.
    """
    from scipy import stats

    def tab(r):
        r = r[r["h"] == h]
        return (r["pred"] - r["faktisk"]).abs().groupby(r["origin"]).mean()

    d = (tab(res_model) - tab(res_ref)).dropna()
    n = len(d)
    if n < 10 or np.allclose(d, 0):
        return float("nan"), 1.0
    u = d - d.mean()
    var = (u @ u) / n
    for k in range(1, h):
        var += 2 * (1 - k / h) * (u[k:].to_numpy() @ u[:-k].to_numpy()) / n
    dm = d.mean() / np.sqrt(var / n)
    dm *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(dm), float(2 * stats.t.sf(abs(dm), df=n - 1))


# --- 5. Prognoseintervaller -----------------------------------------------------------------

# Reserve, når kvantilmodellerne mangler (se CQR nedenfor), og skalaen for CQR's korrektion.
# Fejlene vokser med lusetallet: et fast interval er for bredt ved lave niveauer og for smalt ved høje – netop
# når et område nærmer sig lusegrænsen. Fejlen måles derfor relativt til prognosen plus SKALA_C. Valgt på
# validering 2023–24 med interval score (Gneiting & Raftery 2007): 0,187 mod 0,215 for faste intervaller, og
# dækningen ved prognoser over 0,25 steg fra 35 % til 65 %. 0,01 er den mindste værdi, en tælling kan have
# (to decimaler), og holder intervallet åbent, når prognosen er 0.
SKALA_C = 0.01


def relativ_fejl(faktisk, pred, c: float = SKALA_C):
    return (faktisk - pred) / (pred + c)


def interval(pred, lo_rel, hi_rel, c: float = SKALA_C):
    """(lo, hi) fra prognosen og kvantilerne af den relative fejl. Lusetal kan ikke være negative."""
    return np.maximum(pred + lo_rel * (pred + c), 0), pred + hi_rel * (pred + c)


def intervaller(res: pd.DataFrame, niveau: float = 0.8, min_obs: int = 26) -> pd.DataFrame:
    """Kausale prognoseintervaller fra modellens egne tidligere fejl (empirisk/konform metode).

    For hver forecast-uge, horisont og område bruges kun residualer, hvis måluge allerede er passeret –
    altså fejl, der var kendt på forecast-tidspunktet. Pr. område, fordi fejlenes størrelse varierer meget
    mellem områderne. Fejlene er relative (se SKALA_C), så intervallet vokser med prognosen.
    Rækker uden nok historik får intet interval.
    """
    a = (1 - niveau) / 2
    ud = []
    for (h, omr), r in res.groupby(["h", "omraade"]):
        r = r.sort_values("origin")
        resid = relativ_fejl(r["faktisk"], r["pred"]).to_numpy()
        maal, origin = r["maal"].to_numpy(), r["origin"].to_numpy()
        for o in np.unique(origin):
            kendt = resid[maal <= o]
            if len(kendt) < min_obs:
                continue
            lo, hi = np.quantile(kendt, [a, 1 - a])
            ud.append((h, omr, o, lo, hi))
    q = pd.DataFrame(ud, columns=["h", "omraade", "origin", "lo_rel", "hi_rel"])
    m = res.merge(q, on=["h", "omraade", "origin"], how="inner")
    lo, hi = interval(m["pred"], m["lo_rel"], m["hi_rel"])
    return m.assign(lo=lo, hi=hi)


# Konformaliseret kvantilregression (CQR, Romano, Patterson & Candès 2019). To gradient boosting-modeller forudsiger
# 10 %- og 90 %-kvantilen direkte med alle variablene, så intervallet kan blive bredere af andre grunde end niveauet.
# Rå kvantilmodeller dækker for lidt (71 % på validering), så intervallet udvides med 80 %-kvantilen af de tidligere
# overskridelser E = max(lo − y, y − hi), relativt til prognosen som ovenfor. Valgt på validering 2023–24 mod de
# skalerede intervaller: interval score 0,170 mod 0,188 (DM p = 0,01–0,07 ved de fire horisonter), dækning 79 %
# og jævn over niveauerne (76–81 %). Testperioden bekræftede det: 82 % dækning, 80 % over 0,25 lus pr. fisk.

def raa_kvantiler(lo_pred, hi_pred, pred):
    """Kvantilmodellernes interval, sorteret og udvidet, så prognosen altid ligger inde (kvantiler kan krydse)."""
    lo = np.minimum(np.minimum(lo_pred, hi_pred), pred)
    hi = np.maximum(np.maximum(lo_pred, hi_pred), pred)
    return np.maximum(lo, 0), hi


def cqr_score(faktisk, pred, lo, hi, c: float = SKALA_C):
    """Hvor langt udfaldet lå uden for kvantilintervallet (negativ: inde), relativt til prognosen."""
    return np.maximum(lo - faktisk, faktisk - hi) / (pred + c)


def cqr_udvid(pred, lo, hi, korrektion, c: float = SKALA_C):
    return np.maximum(lo - korrektion * (pred + c), 0), hi + korrektion * (pred + c)


def cqr_intervaller(res: pd.DataFrame, kvantiler: pd.DataFrame, niveau: float = 0.8, min_obs: int = 26) -> pd.DataFrame:
    """Kausale CQR-intervaller til backtesten. `kvantiler` har kolonnerne pred_lo og pred_hi pr. prognose.

    Korrektionen for en forecast-uge bruger kun overskridelser, hvis måluge allerede er passeret, pr. område og horisont.
    """
    noegle = ["omraade", "origin", "h", "maal"]
    m = res.merge(kvantiler[noegle + ["pred_lo", "pred_hi"]], on=noegle, how="inner")
    m["lo_q"], m["hi_q"] = raa_kvantiler(m["pred_lo"], m["pred_hi"], m["pred"])
    ud = []
    for (h, omr), r in m.groupby(["h", "omraade"]):
        r = r.sort_values("origin")
        e = cqr_score(r["faktisk"], r["pred"], r["lo_q"], r["hi_q"]).to_numpy()
        maal = r["maal"].to_numpy()
        for o in np.unique(r["origin"]):
            kendt = e[maal <= o]
            if len(kendt) >= min_obs:
                ud.append((h, omr, o, np.quantile(kendt, niveau)))
    q = pd.DataFrame(ud, columns=["h", "omraade", "origin", "korrektion"])
    m = m.merge(q, on=["h", "omraade", "origin"], how="inner")
    lo, hi = cqr_udvid(m["pred"], m["lo_q"], m["hi_q"], m["korrektion"])
    return m.assign(lo=lo, hi=hi)


def daekning(med_interval: pd.DataFrame) -> pd.Series:
    """Andel af faktiske værdier inden for intervallet, pr. horisont."""
    inde = (med_interval["faktisk"] >= med_interval["lo"]) & (med_interval["faktisk"] <= med_interval["hi"])
    return inde.groupby(med_interval["h"]).mean()
