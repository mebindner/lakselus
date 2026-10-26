"""Prognosemodeller for ugentlige lusetal pr. produktionsområde.

Alle modeller er forecastere med samme interface som baselines:  f(historik, h) -> pd.Series (indeks = omraade).
De ser kun `historik` (data til og med forecast-ugen), så backtesten kan ikke lække fremtid ind i modellen.

Kandidater
- saeson_justeret:  sidste uges niveau + den typiske ændring fra denne uge til uge+h i tidligere år (pr. område).
- ridge:            lineær model (direkte pr. horisont) på ændringen y(t+h) − y(t).
- gbm:              gradient boosting med MAE-tab, samme mål og features, fælles for alle områder.
- ensemble:         gennemsnit af saeson_justeret, ridge og gbm.

Modellerne forudsiger *ændringen* fra i dag frem for niveauet. Så er den naive prognose (ændring = 0)
modellens udgangspunkt, og den skal kun lære, hvornår og hvor meget niveauet afviger fra uge til uge.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERISKE = ["y", "d1", "d2", "d4", "d8", "rul4", "rul12", "std4", "temp_nu", "temp_d4",
             "uge_sin", "uge_cos", "log_n", "saes_d"]
NATIONALE = ["nat_y", "nat_d1"]
REFIT_UGER = 13  # gen-træn hvert kvartal i backtesten


# --- Features --------------------------------------------------------------------------

def _iso_uge(datoer: pd.Series) -> pd.Series:
    return datoer.dt.isocalendar().week.astype(int).clip(upper=52)


def saeson_aendring(historik: pd.DataFrame, h: int) -> pd.Series:
    """Gennemsnitlig ændring y(t+h) − y(t) pr. (omraade, ISO-uge for t), beregnet inden for historikken."""
    p = historik.sort_values(["omraade", "uge_start"])
    fremtid = p.groupby("omraade")["hunlus"].shift(-h)
    aendring = (fremtid - p["hunlus"]).rename("saes_d")
    return aendring.groupby([p["omraade"], _iso_uge(p["uge_start"]).rename("uge")]).mean()


def features(historik: pd.DataFrame, h: int) -> pd.DataFrame:
    """Kausale features pr. (omraade, uge): kun værdier fra samme uge og tidligere indgår.

    Undtagelse: `saes_d` er sæsonprofilen beregnet på hele historikken – den kender intet efter forecast-ugen.
    """
    p = historik[["omraade", "uge_start", "hunlus", "temp", "n_lok"]].sort_values(["omraade", "uge_start"]).copy()
    g = p.groupby("omraade")
    p["y"] = g["hunlus"].ffill()
    p["temp_nu"] = g["temp"].ffill()
    gy, gt = p.groupby("omraade")["y"], p.groupby("omraade")["temp_nu"]
    for k in (1, 2, 4, 8):
        p[f"d{k}"] = p["y"] - gy.shift(k)
    rul = lambda n, m: gy.rolling(n, min_periods=m)  # noqa: E731 – vektoriseret glidende vindue pr. område
    p["rul4"] = rul(4, 2).mean().reset_index(level=0, drop=True)
    p["rul12"] = rul(12, 4).mean().reset_index(level=0, drop=True)
    p["std4"] = rul(4, 2).std().reset_index(level=0, drop=True)
    p["temp_d4"] = p["temp_nu"] - gt.shift(4)
    uge = _iso_uge(p["uge_start"])
    p["uge_sin"], p["uge_cos"] = np.sin(2 * np.pi * uge / 52), np.cos(2 * np.pi * uge / 52)
    p["log_n"] = np.log1p(p["n_lok"])
    # Hele kystens udvikling samme uge – lus spredes, og fælles drivere (temperatur, sæson) rammer alle områder.
    nat = p.groupby("uge_start")[["y", "d1"]].transform("mean")
    p["nat_y"], p["nat_d1"] = nat["y"], nat["d1"]
    saes = saeson_aendring(historik, h).reset_index()
    p = p.assign(uge=uge.to_numpy()).merge(saes, on=["omraade", "uge"], how="left").drop(columns="uge")
    p["maal"] = p.groupby("omraade")["hunlus"].shift(-h) - p["y"]  # ændringen h uger frem (kun til træning)
    return p


# --- Forecastere ---------------------------------------------------------------------------

def saeson_justeret(historik: pd.DataFrame, h: int) -> pd.Series:
    """Sidste niveau + den typiske sæsonændring for området fra denne uge til h uger frem."""
    f = features(historik, h)
    nu = f[f["uge_start"] == f["uge_start"].max()].set_index("omraade")
    return (nu["y"] + nu["saes_d"].fillna(0)).clip(lower=0)


def _ridge(kolonner: list[str]):
    pre = ColumnTransformer([
        ("tal", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), kolonner),
        ("omr", OneHotEncoder(handle_unknown="ignore"), ["omraade"]),
    ])
    return make_pipeline(pre, Ridge(alpha=3.0))


GBM_PARAMS = dict(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0)


def _gbm(kolonner: list[str], **params):
    return HistGradientBoostingRegressor(
        loss="absolute_error", categorical_features=[len(kolonner)], random_state=0, **(GBM_PARAMS | params),
    )


class DirekteModel:
    """Direkte multi-horisont-model: én model pr. h, gen-trænes hvert REFIT_UGER uger.

    Kaldes som forecaster: model(historik, h). Træningsrækker er dem, hvor målet (h uger frem) allerede
    ligger inden for historikken – altså kendt på forecast-tidspunktet.
    """

    def __init__(self, fabrik, kolonner: list[str] | None = None, refit_uger: int = REFIT_UGER):
        self.fabrik, self.refit_uger = fabrik, refit_uger
        self.kolonner = kolonner or NUMERISKE
        self._modeller: dict[int, tuple[pd.Timestamp, object]] = {}

    def _X(self, f: pd.DataFrame) -> pd.DataFrame:
        return f[self.kolonner + ["omraade"]]

    def __call__(self, historik: pd.DataFrame, h: int) -> pd.Series:
        f = features(historik, h)
        origin = f["uge_start"].max()
        cache = self._modeller.get(h)
        if cache is None or (origin - cache[0]).days >= 7 * self.refit_uger or origin < cache[0]:
            traen = f.dropna(subset=["maal", "y", "d1"])
            model = self.fabrik(self.kolonner).fit(self._X(traen), traen["maal"])
            self._modeller[h] = cache = (origin, model)
        nu = f[f["uge_start"] == origin]
        aendring = cache[1].predict(self._X(nu))
        return pd.Series((nu["y"].to_numpy() + aendring).clip(min=0), index=nu["omraade"].to_numpy())


class Ensemble:
    """Gennemsnit af flere forecastere – reducerer variansen fra den enkelte model."""

    def __init__(self, *dele):
        self.dele = dele

    def __call__(self, historik: pd.DataFrame, h: int) -> pd.Series:
        return pd.concat([d(historik, h) for d in self.dele], axis=1).mean(axis=1)


def kandidater() -> dict:
    """Friske modelinstanser (de har tilstand pga. refit-cache)."""
    # Valgt på valideringsperioden 2023–24 (se README): nationale features gav GBM en lille, konsistent
    # forbedring, men ikke ridge. Dybere/fladere træer ændrede skill < 0,01 – standardindstillingerne beholdes.
    ridge, gbm = DirekteModel(_ridge, NUMERISKE), DirekteModel(_gbm, NUMERISKE + NATIONALE)
    return {
        "saeson_justeret": saeson_justeret,
        "ridge": ridge,
        "gbm": gbm,
        "ensemble": Ensemble(saeson_justeret, ridge, gbm),
    }
