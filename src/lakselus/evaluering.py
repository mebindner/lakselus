"""Baselines og rullende backtest.

En forecaster er en funktion  f(historik, h) -> pd.Series  (indeks = omraade), der kun må se
`historik` (panelet til og med forecast-ugen) og forudsiger hunlus h uger frem.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

Forecaster = Callable[[pd.DataFrame, int], pd.Series]


def naiv(historik: pd.DataFrame, h: int) -> pd.Series:
    """Samme værdi som i forecast-ugen."""
    sidste = historik["uge_start"].max()
    return historik[historik["uge_start"] == sidste].set_index("omraade")["hunlus"]


def saeson_naiv(historik: pd.DataFrame, h: int) -> pd.Series:
    """Samme uge sidste år (52 uger før måluge)."""
    maal = historik["uge_start"].max() + pd.Timedelta(weeks=h - 52)
    return historik[historik["uge_start"] == maal].set_index("omraade")["hunlus"]


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


# --- Statistisk evaluering ------------------------------------------------------------

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


def intervaller(res: pd.DataFrame, niveau: float = 0.8, min_obs: int = 26) -> pd.DataFrame:
    """Kausale prognoseintervaller fra modellens egne tidligere fejl (empirisk/konform metode).

    For hver forecast-uge, horisont og område bruges kun residualer, hvis måluge allerede er passeret –
    altså fejl, der var kendt på forecast-tidspunktet. Pr. område, fordi fejlenes størrelse varierer meget
    mellem områderne. Rækker uden nok historik får intet interval.
    """
    a = (1 - niveau) / 2
    ud = []
    for (h, omr), r in res.groupby(["h", "omraade"]):
        r = r.sort_values("origin")
        resid = (r["faktisk"] - r["pred"]).to_numpy()
        maal, origin = r["maal"].to_numpy(), r["origin"].to_numpy()
        for o in np.unique(origin):
            kendt = resid[maal <= o]
            if len(kendt) < min_obs:
                continue
            lo, hi = np.quantile(kendt, [a, 1 - a])
            ud.append((h, omr, o, lo, hi))
    q = pd.DataFrame(ud, columns=["h", "omraade", "origin", "lo_resid", "hi_resid"])
    m = res.merge(q, on=["h", "omraade", "origin"], how="inner")
    return m.assign(lo=(m["pred"] + m["lo_resid"]).clip(lower=0), hi=m["pred"] + m["hi_resid"])


def daekning(med_interval: pd.DataFrame) -> pd.Series:
    """Andel af faktiske værdier inden for intervallet, pr. horisont."""
    inde = (med_interval["faktisk"] >= med_interval["lo"]) & (med_interval["faktisk"] <= med_interval["hi"])
    return inde.groupby(med_interval["h"]).mean()
