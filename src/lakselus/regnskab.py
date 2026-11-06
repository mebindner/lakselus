"""Prognoseregnskab: hver uges offentliggjorte prognose gemmes og holdes op mod det, der faktisk skete.

Backtesten viser, hvordan modellen ville have klaret sig på historiske data. Regnskabet viser, hvordan de
prognoser, siden rent faktisk har vist, gik – uden mulighed for at justere bagefter. Arkivet ligger i data/app
og committes hver uge, så alle kan efterprøve det.

Regel: én prognose pr. udgangsuge. Køres modellen igen i samme uge (før næste uges tal findes), erstatter den nye
prognose den gamle. Så snart en ny uge er kommet, ligger prognosen fast.

Indhold
1. Arkiv     – læs, tilføj ugens prognose, gem
2. Vurdering – prognoserne sammen med det faktiske lusetal og den naive prognose (»intet ændrer sig«)
3. Opsummering – hvor mange ramte intervallet, og fejl mod den naive prognose
4. Kommandolinje – opbyg arkivet fra prognosefilens historik i git (bruges én gang)
"""

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from lakselus.config import DATA_APP

ARKIV_FIL = DATA_APP / "prognose_arkiv.parquet"
KOLONNER = ["lavet", "omraade", "h", "uge_start", "pred", "lo", "hi", "model"]


# --- 1. Arkiv ---------------------------------------------------------------------------------

def laes() -> pd.DataFrame:
    return pd.read_parquet(ARKIV_FIL) if ARKIV_FIL.exists() else pd.DataFrame(columns=KOLONNER)


def tilfoej(arkiv: pd.DataFrame, prognose: pd.DataFrame) -> pd.DataFrame:
    """Ugens prognose ind i arkivet. `lavet` er udgangsugen (ugen før 1-ugers-prognosen).

    En prognose fra samme udgangsuge erstattes; ældre udgangsuger røres ikke.
    """
    ny = prognose.assign(lavet=prognose["uge_start"].min() - pd.Timedelta(weeks=1))[KOLONNER]
    gamle = arkiv[arkiv["lavet"] != ny["lavet"].iloc[0]] if len(arkiv) else arkiv
    ud = pd.concat([gamle, ny], ignore_index=True) if len(gamle) else ny.reset_index(drop=True)
    return ud.astype({"omraade": int, "h": int}).sort_values(["lavet", "h", "omraade"]).reset_index(drop=True)


def gem(prognose: pd.DataFrame) -> pd.DataFrame:
    arkiv = tilfoej(laes(), prognose)
    arkiv.to_parquet(ARKIV_FIL, index=False)
    return arkiv


# --- 2. Vurdering -------------------------------------------------------------------------------

def vurder(arkiv: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """De prognoser, hvis uge er kommet: faktisk lusetal, om det lå i 80 %-intervallet, og den naive prognose."""
    niveau = panel.set_index(["uge_start", "omraade"])["hunlus"]
    a = arkiv.copy()
    a["faktisk"] = [niveau.get((u, o)) for u, o in zip(a["uge_start"], a["omraade"])]
    a["naiv"] = [niveau.get((l, o)) for l, o in zip(a["lavet"], a["omraade"])]
    a = a.dropna(subset=["faktisk"]).astype({"faktisk": float})
    a["inde"] = (a["faktisk"] >= a["lo"]) & (a["faktisk"] <= a["hi"])
    a["fejl"] = (a["pred"] - a["faktisk"]).abs()
    a["naiv_fejl"] = (a["naiv"].astype(float) - a["faktisk"]).abs()
    return a.reset_index(drop=True)


# --- 3. Opsummering -----------------------------------------------------------------------------

def opsummer(vurderet: pd.DataFrame) -> dict:
    """Antal vurderede prognoser, andel i intervallet og gennemsnitlig fejl for modellen og den naive prognose."""
    if vurderet.empty:
        return {"n": 0}
    med_naiv = vurderet.dropna(subset=["naiv_fejl"])
    return {
        "n": len(vurderet), "inde": int(vurderet["inde"].sum()), "andel_inde": float(vurderet["inde"].mean()),
        "mae": float(vurderet["fejl"].mean()), "mae_naiv": float(med_naiv["naiv_fejl"].mean()) if len(med_naiv) else None,
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


if __name__ == "__main__":
    a = fra_git()
    a.to_parquet(ARKIV_FIL, index=False)
    print(f"Skrev {ARKIV_FIL.name}: {a['lavet'].nunique()} udgangsuger, {len(a)} prognoser")
