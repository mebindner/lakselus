"""Baselines og rullende backtest.

En forecaster er en funktion  f(historik, h) -> pd.Series  (indeks = omraade), der kun må se
`historik` (panelet til og med forecast-ugen) og forudsiger hunlus h uger frem.
"""

from collections.abc import Callable

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
