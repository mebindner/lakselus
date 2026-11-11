"""Fuld modelevaluering: backtest af alle modeller, modelvalg på validering, rapport på test.

Kør:  python -m lakselus.modelrapport
Gemmer data/app/backtest.parquet og data/app/prognose.parquet, som Streamlit-appen læser.

Indhold
1. Filer og modelnavne
2. Backtest                    – alle baselines og kandidater på samme panel
3. Modelvalg og opsummering    – valg på validering (2023–24), rapport på test (2025→)
4. Live-prognose               – 1–4 uger frem med 80 %-interval (CQR) fra backtesten
5. Kommandolinje
"""

import time

import pandas as pd

from lakselus import biomasse, data, evaluering as ev, modeller as m, regnskab
from lakselus.config import DATA_APP

# --- 1. Filer og modelnavne -----------------------------------------------------------------

# Committes sammen med app-data, så den hostede app ikke skal køre backtesten ved opstart.
BACKTEST_FIL = DATA_APP / "backtest.parquet"
# Den valgte models prognose 1–4 uger frem – beregnes her, så appens første besøgende ikke venter på træning.
PROGNOSE_FIL = DATA_APP / "prognose.parquet"
BASELINES = {"naiv": ev.naiv, "saeson_naiv": ev.saeson_naiv}
NAVNE = {
    "naiv": "Naive (last week)",
    "saeson_naiv": "Seasonal naive (same week last year)",
    "saeson_justeret": "Naive + seasonal change",
    "ridge": "Ridge regression",
    "gbm": "Gradient boosting",
    "gbm_beh": "Gradient boosting + treatments",
    "gbm_stadier": "Gradient boosting + lice stages",
    "gbm_biomasse": "Gradient boosting + lice stages + fish stock",
    "ensemble": "Ensemble",
}


# --- 2. Backtest ----------------------------------------------------------------------------

def koer(panel: pd.DataFrame, log=print) -> pd.DataFrame:
    """Backtest af baselines og modelkandidater; ét langt datasæt med kolonnen `model`.

    Til sidst backtestes kvantilmodellerne til den valgte models interval (m.KVANTILER). De er ikke kandidater og
    holdes ude af modelvalget og tabellerne (se som_dict).
    """
    dele = []
    for navn, f in (BASELINES | m.kandidater()).items():
        t = time.time()
        dele.append(ev.backtest(panel, f).assign(model=navn))
        log(f"  {navn:16s} {time.time() - t:5.1f} s")
    res = pd.concat(dele, ignore_index=True)
    for navn, f in m.kvantil_modeller(m.kandidater().get(vaelg_model(res))).items():
        t = time.time()
        res = pd.concat([res, ev.backtest(panel, f).assign(model=navn)], ignore_index=True)
        log(f"  {navn:16s} {time.time() - t:5.1f} s")
    return res


# --- 3. Modelvalg og opsummering ------------------------------------------------------------

def som_dict(res: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Prognosemodellerne (baselines og kandidater) – uden intervalmodellerne."""
    return {navn: r.drop(columns="model") for navn, r in res.groupby("model", sort=False) if navn not in m.KVANTILER}


def kvantiler(res: pd.DataFrame) -> pd.DataFrame | None:
    """Kvantilmodellernes backtest som én række pr. prognose (pred_lo, pred_hi). None, hvis de ikke er kørt."""
    if not set(m.KVANTILER) <= set(res["model"]):
        return None
    noegle = ["omraade", "origin", "h", "maal"]
    lo, hi = (res[res["model"] == k].set_index(noegle)["pred"] for k in m.KVANTILER)
    return pd.DataFrame({"pred_lo": lo, "pred_hi": hi}).dropna().reset_index()


def backtest_intervaller(res: pd.DataFrame, model: str) -> pd.DataFrame:
    """80 %-intervaller for modellens backtest: CQR, når kvantilmodellerne findes, ellers skalerede fejl."""
    r = res[res["model"] == model].drop(columns="model")
    kv = kvantiler(res)
    return ev.cqr_intervaller(r, kv) if kv is not None else ev.intervaller(r)


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
    ud["daekning_test"] = ev.daekning(ev.periode(backtest_intervaller(res, valgt), ev.TEST))
    ud["mae_omraade_test"] = ev.mae(test, efter=["omraade", "h"])
    return ud


# --- 4. Live-prognose ------------------------------------------------------------------------

def live_prognose(panel: pd.DataFrame, model: str, res: pd.DataFrame, niveau: float = 0.8) -> pd.DataFrame:
    """Prognose 1–4 uger frem fra seneste uge med den valgte model og et 80 %-interval pr. område.

    Modellen trænes på alle data. Intervallet er CQR: kvantilmodellerne trænes også på alle data, og intervallet
    udvides med 80 %-kvantilen af deres overskridelser i hele backtesten for området og horisonten. Uden kvantilmodeller
    bruges de empiriske kvantiler af modellens egne relative backtest-fejl (se evaluering.SKALA_C).
    `naiv` er områdets lusetal i udgangsugen, som det så ud nu – regnskabet sammenligner med det, ikke med det tal,
    ugen senere bliver rettet til.
    """
    f = (m.kandidater() | BASELINES)[model]
    kv_modeller = m.kvantil_modeller(m.kandidater().get(model))
    kv = kvantiler(res)
    if kv_modeller and kv is not None:
        b = res[res["model"] == model].merge(kv, on=["omraade", "origin", "h", "maal"])
        lo_q, hi_q = ev.raa_kvantiler(b["pred_lo"], b["pred_hi"], b["pred"])
        e = ev.cqr_score(b["faktisk"], b["pred"], lo_q, hi_q)
        korrektion = e.groupby([b["omraade"], b["h"]]).quantile(niveau)
    else:
        resid = res[res["model"] == model].assign(r=lambda d: ev.relativ_fejl(d["faktisk"], d["pred"]))
        q = resid.groupby(["omraade", "h"])["r"].quantile([(1 - niveau) / 2, (1 + niveau) / 2]).unstack()
        q.columns = ["lo_rel", "hi_rel"]
    nan = float("nan")
    seneste = panel["uge_start"].max()
    naiv = ev.naiv(panel, 1)
    rows = []
    for h in (1, 2, 3, 4):
        pred = f(panel, h)
        if kv_modeller and kv is not None:
            lo_p, hi_p = (kv_modeller[k](panel, h).reindex(pred.index) for k in m.KVANTILER)
            lo_q, hi_q = ev.raa_kvantiler(lo_p, hi_p, pred)
            k = pd.Series([korrektion.get((o, h), nan) for o in pred.index], index=pred.index)
            lo, hi = ev.cqr_udvid(pred, lo_q, hi_q, k)
        else:
            rel = pd.DataFrame([q.loc[(o, h)] if (o, h) in q.index else (nan, nan) for o in pred.index],
                               index=pred.index, columns=["lo_rel", "hi_rel"])
            lo, hi = ev.interval(pred, rel["lo_rel"], rel["hi_rel"])
        for omr, v in pred.items():
            rows.append({"omraade": omr, "h": h, "uge_start": seneste + pd.Timedelta(weeks=h), "pred": v,
                         "lo": float(lo[omr]), "hi": float(hi[omr]), "naiv": naiv.get(omr, nan)})
    return pd.DataFrame(rows).assign(model=model)


# --- 5. Kommandolinje -----------------------------------------------------------------------

def main() -> None:
    panel = data.ugentligt_panel(data.indlaes_raa(), data.indlaes_behandlinger())
    bestand = biomasse.indlaes()
    if bestand is not None:  # uden fiskebestanden får gbm_biomasse NaN og bliver i praksis til gbm_stadier
        panel = biomasse.til_panel(panel, bestand)
    print("Backtest (dette tager et par minutter) …")
    res = koer(panel)
    DATA_APP.mkdir(parents=True, exist_ok=True)
    res.to_parquet(BACKTEST_FIL, index=False)

    o = opsummer(res)
    prognose = live_prognose(panel, o["valgt"], res)
    prognose.to_parquet(PROGNOSE_FIL, index=False)
    # Regnskabet: ugens prognose gemmes, så den senere kan holdes op mod det, der faktisk skete.
    arkiv = regnskab.gem(prognose)
    pd.set_option("display.width", 140)
    print(f"\nValgt model (bedst på validering {ev.VALIDERING[0][:4]}–{ev.VALIDERING[1][:4]}): {NAVNE[o['valgt']]}")
    print("\nMAE – validering\n", o["mae_validering"].round(4))
    print("\nMAE – test (2025→)\n", o["mae_test"].round(4))
    print("\nSkill mod naiv – test\n", o["skill_test"].round(3))
    print("\nDM-test p-værdi mod naiv – test\n", o["dm_test"].round(4))
    print("\n80 %-intervallets dækning – test\n", o["daekning_test"].round(3))
    print(f"\nGemt: {BACKTEST_FIL}, {PROGNOSE_FIL} og {regnskab.ARKIV_FIL} ({arkiv['lavet'].nunique()} uger)")


if __name__ == "__main__":
    main()
