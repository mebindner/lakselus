"""Hvor meget sænker en lusebehandling lusetallet? Hændelsesstudie med en matchet kontrolgruppe.

Spørgsmålet: Hvordan udvikler lusetallet på en lokalitet sig i ugerne omkring en behandling – og hvor meget
af faldet skyldes behandlingen og ikke bare, at lusetallet alligevel ville være faldet?

Metode
- Hændelse: en uge, hvor hele lokaliteten fik præcis én type behandling, og lokaliteten ikke blev behandlet
  i ugerne før og efter (vinduet −3 til +6 uger). Så blandes effekterne af flere behandlinger ikke sammen.
- Forløb: lusetallet i hver uge i forhold til ugen før behandlingen (= 100 %). Median og kvartiler pr. type.
- Kontrol: lokalitet-uger uden nogen behandling i samme vindue. Anlæg behandler, når lusetallet er højt, og
  et højt lusetal falder ofte lidt af sig selv (regression mod middelværdien). Kontrollen matches derfor på
  lusetallet ugen før og på måned: for hver behandlingstype vægtes kontrollen, så den har samme fordeling af
  udgangsniveau og årstid som de behandlede.

Indhold
1. Konstanter         – vindue, minimumsniveau og typenavne
2. Lusetal pr. uge    – én værdi pr. (lokalitet, uge)
3. Hændelser          – isolerede behandlinger af hele lokaliteten
4. Forløb             – lusetal i forhold til ugen før, for behandlede og kontrol
5. Samlet tabel       – median, kvartiler og antal pr. type og uge (det, appen viser)
"""

import pandas as pd

from lakselus import data
from lakselus.config import DATA_APP

# Den færdige tabel publiceres til den hostede app, som ikke har behandlinger pr. lokalitet.
APP_FIL = DATA_APP / "behandlingseffekt.parquet"


# --- 1. Konstanter -------------------------------------------------------------------------

UGER = range(-3, 7)       # uger i forhold til behandlingsugen, der vises
MIN_NIVEAU = 0.05         # under dette niveau ugen før giver procentvise ændringer ingen mening
MIN_HAENDELSER = 30       # typer med færre isolerede behandlinger udelades
# Niveaubånd til matching af kontrolgruppen (voksne hunlus pr. fisk ugen før).
NIVEAU_BAAND = [MIN_NIVEAU, 0.1, 0.2, 0.3, 0.5, 1.0, float("inf")]
TYPER = {
    "termisk behandling": "Thermal",
    "mekanisk behandling": "Mechanical",
    "ferskvannsbehandling": "Freshwater",
    "badebehandling": "Bath (medicinal)",
    "fôrbehandling": "In-feed (medicinal)",
    "annen behandling": "Other",
}


# --- 2. Lusetal pr. uge --------------------------------------------------------------------

def lusetal_pr_lokalitet(raa: pd.DataFrame) -> pd.Series:
    """Voksne hunlus pr. fisk, indekseret på (lokalitet, uge_start), kun uger hvor lokaliteten har talt."""
    talt = raa[raa["har_talt"] == "Ja"].dropna(subset=["hunlus"])
    return talt.groupby(["lokalitet", "uge_start"])["hunlus"].mean()


def _slaa_op(lus: pd.Series, lok: pd.Series, uge: pd.Series) -> pd.Series:
    """Lusetal for hvert (lokalitet, uge)-par; NaN hvor der ikke er talt."""
    return pd.Series(lus.reindex(pd.MultiIndex.from_arrays([lok, uge])).to_numpy(), index=lok.index)


# --- 3. Hændelser --------------------------------------------------------------------------

def _behandlede_uger(beh: pd.DataFrame) -> pd.MultiIndex:
    """Alle (lokalitet, uge), hvor der blev behandlet – uanset type og omfang."""
    return pd.MultiIndex.from_frame(beh[["Lokalitetsnummer", "uge_start"]].drop_duplicates())


def _ubehandlet_i_vindue(lok: pd.Series, uge: pd.Series, behandlet: pd.MultiIndex, undtagen_0: bool) -> pd.Series:
    """Sand, hvis lokaliteten ikke blev behandlet i nogen uge i vinduet (evt. bortset fra uge 0)."""
    fri = pd.Series(True, index=lok.index)
    for k in UGER:
        if undtagen_0 and k == 0:
            continue
        noegler = pd.MultiIndex.from_arrays([lok, uge + pd.Timedelta(weeks=k)])
        fri &= ~noegler.isin(behandlet)
    return fri


def haendelser(beh: pd.DataFrame) -> pd.DataFrame:
    """Isolerede behandlinger af hele lokaliteten med én behandlingstype i ugen."""
    beh = beh.assign(uge_start=data._uge_start(beh["År"], beh["Uke"]))
    pr_uge = beh.groupby(["Lokalitetsnummer", "uge_start"]).agg(
        typer=("Type behandling", "nunique"), type=("Type behandling", "first"),
        hele=("Omfang", lambda s: (s == "hele lokaliteten").any()), omraade=("ProduksjonsområdeId", "first"),
    ).reset_index()
    h = pr_uge[(pr_uge["typer"] == 1) & pr_uge["hele"] & pr_uge["type"].isin(TYPER)]
    isoleret = _ubehandlet_i_vindue(h["Lokalitetsnummer"], h["uge_start"], _behandlede_uger(beh), undtagen_0=True)
    return h[isoleret].rename(columns={"Lokalitetsnummer": "lokalitet"})[["lokalitet", "uge_start", "type", "omraade"]]


# --- 4. Forløb -----------------------------------------------------------------------------

def _forloeb(lus: pd.Series, start: pd.DataFrame) -> pd.DataFrame:
    """Langt datasæt: lusetal i uge k i forhold til ugen før (k = −1 er 100 %), med udgangsniveau og måned."""
    udgang = _slaa_op(lus, start["lokalitet"], start["uge_start"] - pd.Timedelta(weeks=1))
    start = start.assign(udgang=udgang)[udgang >= MIN_NIVEAU]
    dele = []
    for k in UGER:
        v = _slaa_op(lus, start["lokalitet"], start["uge_start"] + pd.Timedelta(weeks=k))
        dele.append(start.assign(k=k, indeks=v / start["udgang"]))
    ud = pd.concat(dele, ignore_index=True).dropna(subset=["indeks"])
    return ud.assign(baand=pd.cut(ud["udgang"], NIVEAU_BAAND, right=False).cat.codes,
                     maaned=ud["uge_start"].dt.month)


def behandlede_forloeb(lus: pd.Series, beh: pd.DataFrame) -> pd.DataFrame:
    return _forloeb(lus, haendelser(beh))


def kontrol_forloeb(lus: pd.Series, beh: pd.DataFrame) -> pd.DataFrame:
    """Forløb for lokalitet-uger uden nogen behandling i vinduet – de "ubehandlede tvillinger"."""
    beh = beh.assign(uge_start=data._uge_start(beh["År"], beh["Uke"]))
    alle = lus.index.to_frame(index=False)
    fri = _ubehandlet_i_vindue(alle["lokalitet"], alle["uge_start"], _behandlede_uger(beh), undtagen_0=False)
    return _forloeb(lus, alle[fri])


# --- 5. Samlet tabel -----------------------------------------------------------------------

def effekt_tabel(raa: pd.DataFrame, beh: pd.DataFrame) -> pd.DataFrame:
    """Pr. behandlingstype og uge: median og kvartiler for behandlede, matchet kontrol og antal hændelser.

    Kolonner: type, k, median, q25, q75, kontrol, n. Indeks i procent af ugen før behandlingen.
    """
    lus = lusetal_pr_lokalitet(raa)
    behandlet, kontrol = behandlede_forloeb(lus, beh), kontrol_forloeb(lus, beh)

    # Kontrollens median pr. (niveaubånd, måned, uge) – vægtet med de behandledes fordeling pr. type.
    kontrol_median = kontrol.groupby(["baand", "maaned", "k"])["indeks"].median().rename("kontrol")
    vaegte = behandlet[behandlet["k"] == -1].groupby(["type", "baand", "maaned"]).size().rename("w").reset_index()
    vaegtet = vaegte.merge(kontrol_median.reset_index(), on=["baand", "maaned"])
    kontrol_linje = (vaegtet.assign(vk=vaegtet["w"] * vaegtet["kontrol"]).groupby(["type", "k"])[["vk", "w"]].sum()
                     .pipe(lambda d: d["vk"] / d["w"]).rename("kontrol"))

    g = behandlet.groupby(["type", "k"])["indeks"]
    tabel = pd.concat([g.median().rename("median"), g.quantile(0.25).rename("q25"), g.quantile(0.75).rename("q75"),
                       kontrol_linje], axis=1).reset_index()
    n = behandlet[behandlet["k"] == -1].groupby("type").size()
    tabel["n"] = tabel["type"].map(n).astype(int)
    tabel = tabel[tabel["n"] >= MIN_HAENDELSER]
    return tabel.assign(type=tabel["type"].map(TYPER)).sort_values(["type", "k"]).reset_index(drop=True)
