"""Prognoseregnskab: hver uges offentliggjorte prognose gemmes og holdes op mod det, der faktisk skete.

Backtesten viser, hvordan modellen ville have klaret sig på historiske data. Regnskabet viser, hvordan de
prognoser, siden rent faktisk har vist, gik – uden mulighed for at justere bagefter. Arkivet ligger i data/app
og committes hver uge, så alle kan efterprøve det.

Den naive prognose (»intet ændrer sig«) er udgangsugens lusetal, som det så ud, da prognosen blev lavet – det
gemmes i arkivet. Ugens tal rettes ofte lidt bagefter, når sene indberetninger kommer ind; at sammenligne med det
rettede tal ville give den naive prognose viden, som ingen havde på tidspunktet.

Regel: én prognose pr. udgangsuge. Køres modellen igen i samme uge (før næste uges tal findes), erstatter den nye
prognose den gamle. Så snart en ny uge er kommet, ligger prognosen fast.

Indhold
1. Arkiv     – læs, tilføj ugens prognose, gem
2. Vurdering – prognoserne sammen med det faktiske lusetal og den naive prognose (»intet ændrer sig«)
3. Opsummering – hvor mange ramte intervallet, og fejl mod den naive prognose
4. Kommandolinje – opbyg arkivet fra prognosefilens historik i git (bruges én gang)
5. Den naive prognose for ældre uger – udgangsugens lusetal fra den samme commit som prognosen
"""

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from lakselus.config import DATA_APP

ARKIV_FIL = DATA_APP / "prognose_arkiv.parquet"
KOLONNER = ["lavet", "omraade", "h", "uge_start", "pred", "lo", "hi", "model", "naiv"]


# --- 1. Arkiv ---------------------------------------------------------------------------------

def laes() -> pd.DataFrame:
    return pd.read_parquet(ARKIV_FIL) if ARKIV_FIL.exists() else pd.DataFrame(columns=KOLONNER)


def tilfoej(arkiv: pd.DataFrame, prognose: pd.DataFrame) -> pd.DataFrame:
    """Ugens prognose ind i arkivet. `lavet` er udgangsugen (ugen før 1-ugers-prognosen).

    En prognose fra samme udgangsuge erstattes; ældre udgangsuger røres ikke.
    """
    ny = prognose.assign(lavet=prognose["uge_start"].min() - pd.Timedelta(weeks=1)).reindex(columns=KOLONNER)
    gamle = arkiv[arkiv["lavet"] != ny["lavet"].iloc[0]] if len(arkiv) else arkiv
    ud = pd.concat([gamle, ny], ignore_index=True) if len(gamle) else ny.reset_index(drop=True)
    return ud.astype({"omraade": int, "h": int}).sort_values(["lavet", "h", "omraade"]).reset_index(drop=True)


def gem(prognose: pd.DataFrame) -> pd.DataFrame:
    arkiv = tilfoej(laes(), prognose)
    arkiv.to_parquet(ARKIV_FIL, index=False)
    return arkiv


# --- 2. Vurdering -------------------------------------------------------------------------------

def vurder(arkiv: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """De prognoser, hvis uge er kommet: faktisk lusetal, om det lå i 80 %-intervallet, og den naive prognose.

    Den naive prognose er udgangsugens tal, som det blev publiceret (kolonnen `naiv`). Havde området ingen tælling
    i udgangsugen, fandtes der ingen naiv prognose, og rækken indgår ikke i sammenligningen med den.
    """
    niveau = panel.set_index(["uge_start", "omraade"])["hunlus"]
    a = arkiv.reindex(columns=KOLONNER)
    a["faktisk"] = [niveau.get((u, o)) for u, o in zip(a["uge_start"], a["omraade"])]
    a["naiv"] = a["naiv"].astype(float)
    a = a.dropna(subset=["faktisk"]).astype({"faktisk": float})
    a["inde"] = (a["faktisk"] >= a["lo"]) & (a["faktisk"] <= a["hi"])
    a["fejl"] = (a["pred"] - a["faktisk"]).abs()
    a["naiv_fejl"] = (a["naiv"].astype(float) - a["faktisk"]).abs()
    return a.reset_index(drop=True)


# --- 3. Opsummering -----------------------------------------------------------------------------

def opsummer(vurderet: pd.DataFrame) -> dict:
    """Antal vurderede prognoser, andel i intervallet og gennemsnitlig fejl for modellen og den naive prognose.

    `mae` er over alle prognoser. Sammenligningen med den naive prognose (`mae_par` mod `mae_naiv`) bruger kun de
    rækker, hvor begge fandtes.
    """
    if vurderet.empty:
        return {"n": 0}
    med_naiv = vurderet.dropna(subset=["naiv_fejl"])
    return {
        "n": len(vurderet), "inde": int(vurderet["inde"].sum()), "andel_inde": float(vurderet["inde"].mean()),
        "mae": float(vurderet["fejl"].mean()), "mae_naiv": float(med_naiv["naiv_fejl"].mean()) if len(med_naiv) else None,
        "mae_par": float(med_naiv["fejl"].mean()) if len(med_naiv) else None,
        "uger": int(vurderet["lavet"].nunique()), "foerste": pd.Timestamp(vurderet["lavet"].min()),
    }


# --- 4. Kommandolinje: opbyg arkivet fra git-historikken ----------------------------------------

def fra_git(fil: str = "data/app/prognose.parquet") -> pd.DataFrame:
    """Hver version af prognosefilen, der er committet, lagt i arkivet i rækkefølge (seneste pr. uge vinder)."""
    koer = lambda *a: subprocess.run(["git", *a], capture_output=True, check=True).stdout
    commits = koer("log", "--reverse", "--format=%H", "--", fil).decode().split()
    arkiv = pd.DataFrame(columns=KOLONNER)
    with tempfile.TemporaryDirectory() as mappe:
        for c in commits:
            sti = Path(mappe) / f"{c}.parquet"
            sti.write_bytes(koer("show", f"{c}:{fil}"))
            arkiv = tilfoej(arkiv, pd.read_parquet(sti))
    return arkiv


# --- 5. Den naive prognose for ældre uger ------------------------------------------------------

def naiv_fra_git(arkiv: pd.DataFrame, prognose_fil: str = "data/app/prognose.parquet",
                 lusetal_fil: str = "data/app/lusetal.parquet") -> pd.DataFrame:
    """Udfylder `naiv` for udgangsuger, der blev arkiveret, før kolonnen fandtes.

    For hver commit, der skrev prognosefilen, læses lusetallene fra samme commit – de tal, prognosen blev lavet på.
    Den seneste commit pr. udgangsuge vinder, som i arkivet.
    """
    from lakselus import data  # her for at undgå en cirkulær import

    koer = lambda *a: subprocess.run(["git", *a], capture_output=True, check=True).stdout  # noqa: E731
    naiv = {}
    with tempfile.TemporaryDirectory() as mappe:
        for c in koer("log", "--reverse", "--format=%H", "--", prognose_fil).decode().split():
            sti, lus = Path(mappe) / "p.parquet", Path(mappe) / "l.parquet"
            sti.write_bytes(koer("show", f"{c}:{prognose_fil}"))
            lavet = pd.read_parquet(sti)["uge_start"].min() - pd.Timedelta(weeks=1)
            lus.write_bytes(koer("show", f"{c}:{lusetal_fil}"))
            raa = pd.read_parquet(lus)
            raa = raa.astype({k: str for k in raa.select_dtypes("category").columns})
            p = data.ugentligt_panel(raa)
            naiv[lavet] = p[p["uge_start"] == lavet].set_index("omraade")["hunlus"]
    a = arkiv.reindex(columns=KOLONNER)
    fra_git_ = [naiv[l].get(o, float("nan")) if l in naiv else float("nan") for l, o in zip(a["lavet"], a["omraade"])]
    a["naiv"] = a["naiv"].astype(float).fillna(pd.Series(fra_git_, index=a.index))
    return a


if __name__ == "__main__":
    a = fra_git()
    a.to_parquet(ARKIV_FIL, index=False)
    print(f"Skrev {ARKIV_FIL.name}: {a['lavet'].nunique()} udgangsuger, {len(a)} prognoser")
