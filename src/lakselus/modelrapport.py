"""Fuld modelevaluering: backtest af alle modeller, modelvalg på validering, rapport på test.

Kør:  python -m lakselus.modelrapport
Gemmer data/processed/backtest.parquet, som Streamlit-appen læser.
"""

import time

import pandas as pd

from lakselus import data, evaluering as ev, modeller as m
from lakselus.config import DATA_PROCESSED

BACKTEST_FIL = DATA_PROCESSED / "backtest.parquet"
BASELINES = {"naiv": ev.naiv, "saeson_naiv": ev.saeson_naiv}
NAVNE = {
    "naiv": "Naive (last week)",
    "saeson_naiv": "Seasonal naive (same week last year)",
    "saeson_justeret": "Naive + seasonal change",
    "ridge": "Ridge regression",
    "gbm": "Gradient boosting",
    "ensemble": "Ensemble",
}


def koer(panel: pd.DataFrame, log=print) -> pd.DataFrame:
    """Backtest af baselines og modelkandidater; ét langt datasæt med kolonnen `model`."""
    dele = []
    for navn, f in (BASELINES | m.kandidater()).items():
        t = time.time()
        dele.append(ev.backtest(panel, f).assign(model=navn))
        log(f"  {navn:16s} {time.time() - t:5.1f} s")
    return pd.concat(dele, ignore_index=True)


def som_dict(res: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {navn: r.drop(columns="model") for navn, r in res.groupby("model", sort=False)}


def vaelg_model(res: pd.DataFrame) -> str:
    """Modellen med højest gennemsnitlig skill over horisonter – målt på VALIDERINGSPERIODEN alene."""
    val = {k: ev.periode(r, ev.VALIDERING) for k, r in som_dict(res).items()}
    skill = ev.skill(ev.mae(val)).mean().drop(list(BASELINES))
    return skill.idxmax()


def opsummer(res: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Tabeller til rapport og app: MAE og skill pr. periode, DM-test og intervaldækning på test."""
    alle = som_dict(res)
    valgt = vaelg_model(res)
    ud = {"valgt": valgt}
    for navn, fra_til in (("validering", ev.VALIDERING), ("test", ev.TEST)):
        mae = ev.mae({k: ev.periode(r, fra_til) for k, r in alle.items()})
        ud[f"mae_{navn}"], ud[f"skill_{navn}"] = mae, ev.skill(mae)
    test = {k: ev.periode(r, ev.TEST) for k, r in alle.items()}
    ud["dm_test"] = pd.DataFrame({
        k: {h: ev.dm_test(test[k], test["naiv"], h)[1] for h in (1, 2, 3, 4)}
        for k in alle if k != "naiv"
    })
    ud["daekning_test"] = ev.daekning(ev.periode(ev.intervaller(alle[valgt]), ev.TEST))
    ud["mae_omraade_test"] = ev.mae(test, efter=["omraade", "h"])
    return ud


def main() -> None:
    panel = data.ugentligt_panel(data.indlaes_raa())
    print("Backtest (dette tager et par minutter) …")
    res = koer(panel)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    res.to_parquet(BACKTEST_FIL, index=False)

    o = opsummer(res)
    pd.set_option("display.width", 140)
    print(f"\nValgt model (bedst på validering {ev.VALIDERING[0][:4]}–{ev.VALIDERING[1][:4]}): {NAVNE[o['valgt']]}")
    print("\nMAE – validering\n", o["mae_validering"].round(4))
    print("\nMAE – test (2025→)\n", o["mae_test"].round(4))
    print("\nSkill mod naiv – test\n", o["skill_test"].round(3))
    print("\nDM-test p-værdi mod naiv – test\n", o["dm_test"].round(4))
    print("\n80 %-intervallets dækning – test\n", o["daekning_test"].round(3))
    print(f"\nGemt: {BACKTEST_FIL}")


if __name__ == "__main__":
    main()
