"""Fiskebestanden pr. produktionsområde fra Fiskeridirektoratets biomassestatistik (åbne data, NLOD).

Opdrætterne indberetter hver måned, hvor mange fisk der står i havet, og hvor mange der er sat ud og slagtet.
Fiskeridirektoratet publicerer tallene den 20. i måneden efter. Lusetallene siger, hvor mange lus der er pr.
fisk – biomassen siger, hvor mange fisk der er. Slagtning fjerner fisk og lus; nye, lusefri smolt trækker
gennemsnittet ned.

Indhold
1. Kilde og filer
2. Hentning
3. Månedstabel pr. område   – laks og regnbueørret samlet, alle årsklasser
4. Til ugepanelet           – kun måneder, der var publiceret på prognosetidspunktet
5. Kommandolinje            – python -m lakselus.biomasse (køres hver uge af GitHub Actions)
"""

import pandas as pd

from lakselus.config import DATA_APP, DATA_RAW

# --- 1. Kilde og filer ----------------------------------------------------------------------

URL = "https://register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-OMR/biostat-total-omr.csv"
RAA_FIL = DATA_RAW / "biomasse.csv"
APP_FIL = DATA_APP / "biomasse.parquet"
PUBLICERINGSDAG = 20  # tallene for en måned publiceres den 20. i måneden efter

KOLONNER = {"BEHFISK_STK": "fisk", "BIOMASSE_KG": "bio_kg", "UTSETT_SMOLT_STK": "utsat",
            "UTTAK_STK": "slagtet", "DØDFISK_STK": "doede"}


# --- 2. Hentning ----------------------------------------------------------------------------

def hent() -> pd.DataFrame:
    """Henter hele filen (2017→) og gemmer den i data/raw. Lille fil, ingen nøgle."""
    raa = pd.read_csv(URL, sep=";", encoding="utf-8-sig", na_values="(null)")
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    raa.to_csv(RAA_FIL, index=False)
    return raa


# --- 3. Månedstabel pr. område --------------------------------------------------------------

def pr_omraade(raa: pd.DataFrame) -> pd.DataFrame:
    """Én række pr. (omraade, maaned) med bestand, udsætning og slagtning samt afledte mål.

    Rækker uden produktionsområde (skjult pga. få selskaber eller ukendt område) udelades. Laks og regnbueørret lægges sammen:
    begge er værter for lakselus, og lusetallene tælles på begge.
    """
    r = raa.dropna(subset=["PO_KODE"]).rename(columns=KOLONNER)
    r["omraade"] = r["PO_KODE"].astype(int)
    r["maaned"] = pd.to_datetime(dict(year=r["ÅR"], month=r["MÅNED_KODE"], day=1))
    m = r.groupby(["omraade", "maaned"])[list(KOLONNER.values())].sum().sort_index()
    g = m.groupby(level="omraade")
    m["vaegt"] = m["bio_kg"] / m["fisk"].where(m["fisk"] > 0)                      # snitvægt i kg
    m["fisk_d1"] = m["fisk"] / g["fisk"].shift(1) - 1                                 # ændring på en måned
    m["fisk_aar"] = m["fisk"] / g["fisk"].shift(12) - 1                               # mod samme måned sidste år
    rul3 = lambda k: g[k].rolling(3, min_periods=1).sum().reset_index(level=0, drop=True)  # noqa: E731
    m["utsat3"] = rul3("utsat") / m["fisk"].where(m["fisk"] > 0)                      # andel nye smolt, 3 mdr.
    m["slagtet3"] = rul3("slagtet") / m["fisk"].where(m["fisk"] > 0)                  # andel slagtet, 3 mdr.
    m = m.replace([float("inf"), -float("inf")], float("nan")).reset_index()  # et tomt område giver division med 0
    m["publiceret"] = m["maaned"] + pd.DateOffset(months=1, days=PUBLICERINGSDAG - 1)
    return m


def indlaes() -> pd.DataFrame | None:
    """Månedstabellen – fra rådata, ellers fra app-data. None, hvis ingen findes."""
    if RAA_FIL.exists():
        return pr_omraade(pd.read_csv(RAA_FIL))
    if APP_FIL.exists():
        return pd.read_parquet(APP_FIL)
    return None


# --- 4. Til ugepanelet ----------------------------------------------------------------------

UGE_KOLONNER = ["fisk", "vaegt", "fisk_d1", "fisk_aar", "utsat3", "slagtet3"]


def til_panel(panel: pd.DataFrame, maaneder: pd.DataFrame) -> pd.DataFrame:
    """Lægger den senest publicerede måned på hver (omraade, uge).

    En uges prognose laves tidligst mandagen efter ugen (uge_start + 7 dage). Kun måneder, der var publiceret
    på det tidspunkt, bruges – så backtesten ser de samme tal, som en prognose dengang kunne have set.
    (Fiskeridirektoratet retter tal bagud, så historikken er dagens udgave, ikke den publicerede dengang.)
    """
    p = panel.assign(_kendt=panel["uge_start"] + pd.Timedelta(days=7)).sort_values("_kendt")
    m = maaneder[["omraade", "publiceret"] + UGE_KOLONNER].sort_values("publiceret")
    ud = pd.merge_asof(p, m, left_on="_kendt", right_on="publiceret", by="omraade", direction="backward")
    return ud.drop(columns=["_kendt", "publiceret"]).sort_values(["omraade", "uge_start"]).reset_index(drop=True)


# --- 5. Kommandolinje -----------------------------------------------------------------------

def main() -> None:
    m = pr_omraade(hent())
    print(f"Gemt {RAA_FIL.name}: {m['omraade'].nunique()} områder, {m['maaned'].min():%Y-%m}–{m['maaned'].max():%Y-%m}")


if __name__ == "__main__":
    main()
