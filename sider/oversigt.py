"""Overview: ugebrief i konsulentstil – executive summary, figurer med handlingstitler og metode (engelsk UI).

Indhold
0. Hjælpefunktioner
1. Data og nøglefund       – seneste uge, lusegrænse, trafiklys og indberetningsstatus
2. Søgning og valg         – søgefelt, kort og søjler deler ét valg (område eller anlæg); valget står i URL'en
3. Sidehoved og resumé     – overskrift og tre nøgletal: hele kysten, et område eller et anlæg
4. Figur: kort + søjler    – klik på et område viser hvert anlæg i området; klik på et anlæg åbner anlægget
5. Figurer for et anlæg    – lusehistorik mod lusegrænsen og naboer inden for 20 km (kun med et valgt anlæg)
6. Figur: statustabel      – det valgte område fremhæves
7. Figur: små multipler    – i år mod tidligere år pr. område; det valgte område først
8. Figur: sæsonmønster
9. Metode og forbehold

Figurerne nummereres i rækkefølge (nr), så anlæggets to figurer kan stå mellem kortet og statustabellen.
"""

import math

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from lakselus import appdata
from lakselus.udseende import (
    FARVER, LAVT_NIVEAU, LUS_FARVER, LYS_FARVER, SEKVENS, andelsbjaelke, figur, forklar, ikon, info, kilde, kurve,
    lus_niveau, prikker, resume, sidehoved, strimmel, trend,
)


# --- 0. Hjælpefunktioner ---------------------------------------------------------------

def rgba(hex_farve: str, alpha: int) -> list[int]:
    h = hex_farve.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def tal(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}"


def pct(v: float, fortegn: bool = False) -> str:
    return (f"{v:+.0%}" if fortegn else f"{v:.0%}").replace("-", "−")


def aendring_tekst(nu: float, foer: float) -> str:
    """Ændringen mod de 4 uger før til tabeller; på lavt niveau i lus pr. fisk i stedet for procent."""
    if pd.isna(nu) or pd.isna(foer) or not foer:
        return "–"
    if max(nu, foer) < LAVT_NIVEAU:
        return f"{nu - foer:+.2f}".replace("-", "−")
    return pct(nu / foer - 1, True)


def radlink(tekst: str, noegle: str) -> str:
    """Et navn i en tabel som link til området eller anlægget (?po= / ?site=); siden åbner med valget fra URL'en."""
    navn, nr = noegle.split(":")
    return f'<a class="radlink" href="?{navn}={nr}" target="_self">{tekst}</a>'


def praecis(v: float) -> str:
    """Et tal med op til 4 decimaler (mindst 2) til regnestykker, så de går op med det viste resultat."""
    t = f"{v:.4f}".rstrip("0")
    return t + "0" * max(0, 2 - len(t.split(".")[1]))


def aendring_celle(nu: float, foer: float) -> str:
    """Ændringen mod de 4 uger før med en boble, der viser regnestykket bag tallet."""
    vis = aendring_tekst(nu, foer)
    if pd.isna(nu):
        return vis
    if pd.isna(foer):
        forklaring = f"No count in {uger_foer} to compare with."
    elif not foer:
        forklaring = f"<b>{praecis(nu)}</b> now, but <b>0.00</b> in {uger_foer} – a percentage of zero cannot be computed."
    elif max(nu, foer) < LAVT_NIVEAU:
        forklaring = (f"Both values are below {LAVT_NIVEAU} lice per fish, so the change is shown in lice per fish, not percent."
                      f"<span class='regnestykke'>{praecis(nu)} − {praecis(foer)} = {vis}</span>")
    else:
        forklaring = (f"<b>{praecis(nu)}</b> in week {iso.week} vs. <b>{praecis(foer)}</b> on average in {uger_foer}."
                      f"<span class='regnestykke'>{praecis(nu)} ÷ {praecis(foer)} − 1 = {vis}</span>")
    return forklar(vis, forklaring)


def ugeserie(r: pd.DataFrame, uger: int = 26) -> tuple[list[float], list[float]]:
    """Ugentligt snit af hunlus de seneste `uger` uger – og de samme uger et år før – til minikurverne."""
    r = r[(r["har_talt"] == "Ja") & (r["uge_start"] > seneste - pd.Timedelta(weeks=52 + uger))]
    t = r.groupby("uge_start")["hunlus"].mean()
    nu_uger = pd.date_range(seneste - pd.Timedelta(weeks=uger - 1), seneste, freq="W-MON")
    return t.reindex(nu_uger).tolist(), t.reindex(nu_uger - pd.Timedelta(weeks=52)).tolist()


def lys_prikker(fremhaev: int | None = None) -> str:
    """De 13 områders trafiklys som prikker fra syd til nord; det valgte område omkranses."""
    return prikker([(LYS_FARVER[po.loc[o, "trafiklys"]][0], f"PO {o} {po.loc[o, 'navn']}: "
                     f"{appdata.TRAFIKLYS[po.loc[o, 'trafiklys']]}", o == fremhaev) for o in sorted(po.index)],
                   "PO 1–13, south to north")


def mod_sidste_aar(nu: float, foer: float) -> str:
    """Fx "12% higher than a year ago" – til overskrifter for et område."""
    if pd.isna(foer) or not foer:
        return "with no counts a year ago to compare"
    if max(nu, foer) < LAVT_NIVEAU:
        return f"at a low level ({nu - foer:+.2f} lice per fish vs. a year ago)".replace("-", "−")
    return f"{abs(nu / foer - 1):.0%} {'lower' if nu < foer else 'higher'} than a year ago"


def gaeldende_graense(raekker: pd.DataFrame, standard: float) -> float:
    """Den lusegrænse, flest anlæg i rækkerne har stået med (0,2 i forårsugerne kommer på forskellige uger)."""
    g = appdata.graense_tal(raekker["Lusegrense uke"]).mode() if "Lusegrense uke" in raekker else pd.Series(dtype=float)
    return float(g.iloc[0]) if len(g) else standard


def retning_ord(nu: float, foer: float) -> str:
    """Et ord om udviklingen mod de 4 uger før ("rising", "falling", "stable", "at a low level") eller ""."""
    tekst = trend(nu, foer)[2]
    return "" if pd.isna(nu) or tekst == "no comparison" else "at a low level" if tekst.startswith("low") else tekst.split()[0]


nr = iter(range(1, 10))  # figurnumre i rækkefølge


# --- 1. Data og nøglefund -------------------------------------------------------
raa, panel, navne = appdata.indlaes()
seneste = panel["uge_start"].max()
# Trafiklyset slås op for den viste uge – det er en politisk beslutning hvert andet år, ikke ugens lusetal.
po = appdata.trafiklys_paa(appdata.omraader(), seneste).set_index("omraade")
status = appdata.status_pr_omraade(raa, panel).join(po[["navn", "trafiklys", "lys_fra"]])
profil = appdata.saesonprofil(panel)

iso = seneste.isocalendar()
talt = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste)]
aar_siden = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == seneste - pd.Timedelta(weeks=52))]

gns, gns_sidst = talt["hunlus"].mean(), aar_siden["hunlus"].mean()
aendring = gns / gns_sidst - 1
over = talt[talt["over_graense"] == "Ja"]
over_pr_omr = over.groupby("omraade").size().sort_values(ascending=False)
over_pr_omr.index = over_pr_omr.index.astype(int)
# Konklusioner bygger kun på områder med solidt datagrundlag; små områder vises, men markeres.
MIN_LOK = 10
solide = status[status["n_lok"] >= MIN_LOK]
top = solide["hunlus"].idxmax()
roede = po[po["trafiklys"] == "red"]
lys_fra = po["lys_fra"].max()
# Lusegrænsen er 0,5 – men 0,2 i forårsugerne, hvor vildlaksen vandrer ud. Den gældende grænse står i data.
graense = pd.to_numeric(talt.get("Lusegrense uke", pd.Series(dtype=str)).astype(str).str.replace(",", "."),
                        errors="coerce").mode()
graense = float(graense.iloc[0]) if len(graense) else 0.5
uge_nu = profil[profil["uge"] == iso.week].dropna(subset=["i_aar"])
over_snit = int((uge_nu["i_aar"] > uge_nu["snit"]).sum())
top_uge_pr_omr = profil.loc[profil.groupby("omraade")["snit"].idxmax()].set_index("omraade")["uge"]
syd_top, nord_top = int(top_uge_pr_omr.loc[[1, 2]].mean()), int(top_uge_pr_omr.loc[[12, 13]].mean())

retning = "lower" if aendring < 0 else "higher"

# Forklaringer til info-boblerne – samme ordlyd i nøgletal og tabeller
uger_foer = (f"weeks {(seneste - pd.Timedelta(weeks=4)).isocalendar().week}–"
             f"{(seneste - pd.Timedelta(weeks=1)).isocalendar().week}")
INFO_GRAENSE = ("A site is above the lice limit when its count is higher than the limit that week: <b>0.5</b> adult female "
                "lice per fish, or <b>0.2</b> in the spring weeks when young wild salmon migrate to sea (the weeks differ "
                "along the coast). The flag comes from the farm's own report.")
INFO_LYS = ("The government sets a colour for each production area every second year, from modelled lice-induced "
            "mortality in wild salmon. <b>Green</b>: farms may grow. <b>Yellow</b>: unchanged. <b>Red</b>: production "
            "capacity is cut. The colour does not follow this week's counts.")
INFO_SNIT = "Every site counts the same, whatever its number of fish (unweighted mean)."
INFO_AENDRING = (f"This week compared with the mean of the four weeks before ({uger_foer}). Rising or falling means a "
                 f"change of more than 15%. Below {LAVT_NIVEAU} lice per fish the change is shown in lice per fish, "
                 "because percentages of almost nothing look dramatic. Hover a value to see the calculation.")

# Indberetningen halter: en uges tal indberettes i løbet af ugen efter. Vis hvilke uger der stadig mangler.
i_dag = pd.Timestamp.now(tz="Europe/Oslo").tz_localize(None).normalize()
mangler = [u.isocalendar().week for u in pd.date_range(seneste + pd.Timedelta(weeks=1),
                                                         i_dag - pd.Timedelta(days=i_dag.weekday() + 7), freq="W-MON")]
if not mangler:
    indberetning = "latest complete week"
elif len(mangler) == 1:
    indberetning = f"week {mangler[0]} is still being reported"
else:
    indberetning = f"weeks {mangler[0]}–{mangler[-1]} are still being reported"
# --- 2. Søgning og valg ---------------------------------------------------------------
# Ét valg for hele siden: søgefeltet, kortet og søjlerne skriver alle til po_valgt/lok_valgt gennem vaelg().
# Søgefeltets værdi (soeg) holdes i takt med valget, og valget står i URL'en (?po=3 / ?site=12345), så en
# side kan bogmærkes og deles. Et nyt nøgletal (kort_n) tegner kort og graf forfra, så kortet zoomer ind
# på valget og markeringen nulstilles.
anlaeg = appdata.anlaeg()
valg = appdata.soegevalg(anlaeg, navne)
st.session_state.setdefault("po_valgt", None)
st.session_state.setdefault("lok_valgt", None)
st.session_state.setdefault("kort_n", 0)


def til_noegle(omraade: int | None, lokalitet: int | None) -> str | None:
    return f"site:{lokalitet}" if lokalitet is not None else (f"po:{omraade}" if omraade is not None else None)


def fra_noegle(noegle: str | None) -> tuple[int | None, int | None]:
    if not noegle:
        return None, None
    navn, nummer = noegle.split(":")
    return (int(anlaeg.loc[int(nummer), "omraade"]), int(nummer)) if navn == "site" else (int(nummer), None)


def vaelg(omraade: int | None, lokalitet: int | None = None) -> None:
    if lokalitet is not None and lokalitet not in anlaeg.index:
        lokalitet = None
    st.session_state.po_valgt, st.session_state.lok_valgt = omraade, lokalitet
    st.session_state.soeg = til_noegle(omraade, lokalitet)
    st.session_state.kort_n += 1


def fra_soeg() -> None:
    vaelg(*fra_noegle(st.session_state.soeg))


def aabn(omraade: int, lokalitet: int | None) -> None:
    """Fra et kort under nøgletallene: vælg – og rul til toppen, så man ser det nye sidehoved."""
    vaelg(omraade, lokalitet)
    st.session_state.rul_op = True


# Søgefeltets værdi forsvinder, når man skifter side. Første gang (og efter et sideskift) hentes valget fra
# URL'en – et delt link – og ellers fra det valg, man havde, før man skiftede side.
if "soeg" not in st.session_state:
    st.session_state.soeg = (appdata.fra_url(st.query_params.to_dict(), valg)
                             or til_noegle(st.session_state.po_valgt, st.session_state.lok_valgt))
    if st.session_state.soeg not in valg:
        st.session_state.soeg = None
    st.session_state.po_valgt, st.session_state.lok_valgt = fra_noegle(st.session_state.soeg)
n = st.session_state.kort_n

with st.container(key="soegning"):
    st.selectbox(":material/search: Find your area or site", list(valg), format_func=valg.get, index=None, key="soeg",
                 on_change=fra_soeg,
                 placeholder=f"Search {len(anlaeg)} farms or {len(navne)} areas")
if st.session_state.pop("rul_op", False):  # kun efter et klik på et kort – kort og søjler bliver hvor de er
    st.html("<script>document.querySelector('[data-testid=\"stMain\"]')?.scrollTo({top: 0, behavior: 'smooth'})</script>",
            unsafe_allow_javascript=True)
if st.query_params.to_dict() != appdata.til_url(st.session_state.soeg):
    st.query_params.from_dict(appdata.til_url(st.session_state.soeg))

valgt = st.session_state.po_valgt if st.session_state.po_valgt in status.index else None
lok_v = st.session_state.lok_valgt if valgt is not None and st.session_state.lok_valgt in anlaeg.index else None

# 2b. Nøgletal for det valgte område (bruges også, når et anlæg er valgt – så er det anlæggets område)
if valgt is not None:
    s_v = status.loc[valgt]
    a_talt = talt[talt["omraade"] == valgt]
    a_sidst = aar_siden[aar_siden["omraade"] == valgt]["hunlus"].mean()
    a_over = a_talt[a_talt["over_graense"] == "Ja"]
    a_graense = gaeldende_graense(a_talt, graense)
    a_top = a_talt.dropna(subset=["hunlus"]).sort_values("hunlus", ascending=False).head(1)
    a_rang = int((status["hunlus"] > s_v.hunlus).sum()) + 1

# 2c. Anlæggets historik og naboer
if lok_v is not None:
    a_lok = anlaeg.loc[lok_v]
    l_navn = a_lok.lokalitet_navn
    nab = appdata.naboer(anlaeg, raa, lok_v, seneste)
    hist = appdata.lokalitet_historik(raa, lok_v, list(nab["lokalitet"]), seneste)
    l_rad = talt[talt["lokalitet"] == lok_v]
    l_nu = float(l_rad["hunlus"].mean()) if len(l_rad) else float("nan")
    l_foer = hist["hunlus"].iloc[-5:-1].mean()
    l_graense = gaeldende_graense(l_rad, a_graense)
    l_over = bool(len(l_rad)) and (l_rad["over_graense"] == "Ja").any()
    l_sidst = hist.dropna(subset=["hunlus"]).iloc[-1]
    l_sidst_iso = l_sidst.uge_start.isocalendar()
    nab_talt = nab.dropna(subset=["hunlus"])
    nab_over = int((nab_talt["over_graense"] == "Ja").sum())
    nabo_nu, nabo_foer = hist["nabo_snit"].iloc[-1], hist["nabo_snit"].iloc[-5:-1].mean()
    nabo_ord = retning_ord(nabo_nu, nabo_foer)
    n_inden = int((nab["km"] <= appdata.NABO_KM).sum())
    nab_tekst = (f"the {len(nab)} sites within {appdata.NABO_KM} km" if n_inden == len(nab)
                 else f"the {len(nab)} nearest sites (up to {nab['km'].max():.0f} km away)")

# 2d. Minigrafer til nøgletallene
KURVE_NOTE = "26 weeks · dashed: a year earlier"
if lok_v is not None:
    l_kurve = kurve(hist["hunlus"].tail(26).tolist(), hist["nabo_snit"].tail(26).tolist(), l_graense,
                    "26 weeks · dashed: neighbours · red: limit")
    l_strimmel = strimmel(a_talt["hunlus"].dropna().tolist(), l_nu if len(l_rad) else None, a_graense,
                          f"Each dot a site in PO {valgt}" + (f" · ringed: {l_navn}" if len(l_rad) else ""))
    l_prikker = prikker([(LUS_FARVER[lus_niveau(r.hunlus)] if pd.notna(r.hunlus) else "#D5DDE3",
                          f"{r.lokalitet_navn}, {r.km:.1f} km: " + (tal(r.hunlus) if pd.notna(r.hunlus) else "not counted"),
                          False) for r in nab.itertuples()], "Neighbours, nearest first · grey: not counted")
elif valgt is not None:
    a_kurve = kurve(*ugeserie(raa[raa["omraade"] == valgt]), note=KURVE_NOTE)
    a_strimmel = strimmel(a_talt["hunlus"].dropna().tolist(), None, a_graense,
                          f"Each dot a site in PO {valgt} · red line: limit")

# --- 3. Sidehoved og resumé ------------------------------------------------------------
if lok_v is not None:
    if len(l_rad):
        l_titel = (f"{l_navn} is {'above' if l_over else 'below'} the {tal(l_graense, 1)} lice limit at {tal(l_nu)}"
                   + (f" – neighbouring sites average {tal(nabo_nu)}" + (f" and are {nabo_ord}" if nabo_ord else "")
                      if pd.notna(nabo_nu) else ""))
    else:
        l_titel = (f"{l_navn} did not count lice in week {iso.week} – its last count was {tal(l_sidst.hunlus)} "
                   f"in week {l_sidst_iso.week}")
    st.markdown(sidehoved(
        f"Site brief · {l_navn} · site no. {lok_v} · PO {valgt} {s_v.navn} · Week {iso.week}, {iso.year}",
        l_titel,
        f"Lice counts for one fish farm, set against the lice limit (lusegrense), the rest of production area {valgt} "
        "and the sites around it. Neighbours matter because lice drift between farms in the same fjord system. "
        "Clear the search to return to the whole coast.",
        [("live", appdata.opdatering_tekst(panel) + ("" if not mangler else f" · {indberetning}")),
         ("database", "BarentsWatch / Mattilsynet"), ("location_on", f"{len(nab)} neighbouring sites"),
         ("verified", "Independent analysis of open data")],
    ), unsafe_allow_html=True)
    l_trend = trend(l_nu, l_foer)[2]
    st.markdown(resume([
        (tal(l_nu), f"adult female lice per fish at {l_navn} in week {iso.week}; the limit this week is "
                    f"{tal(l_graense, 1)}. The level is {l_trend}.",
         f"The count {l_navn} reported for week {iso.week}. The trend compares it with the site's mean in {uger_foer}"
         + (f" (<b>{praecis(l_foer)}</b>)" if pd.notna(l_foer) else "") + ": rising or falling means a change of more than 15%."
         + f"<br><br>{INFO_GRAENSE}", l_kurve) if len(l_rad) else
        (tal(l_sidst.hunlus), f"adult female lice per fish at the last count, week {l_sidst_iso.week} "
                              f"{l_sidst_iso.year}. The site did not count lice in week {iso.week}.",
         "Sites report lice counts for the weeks they have fish in the sea. A site with no count may be between "
         "production cycles.", l_kurve),
        (f"{int((a_talt['hunlus'] > l_nu).sum()) + 1} of {len(a_talt)}",
         f"sites in PO {valgt} ranked by lice level (1 = highest). The area mean is {tal(s_v.hunlus)}.",
         f"The {len(a_talt)} sites in PO {valgt} that counted lice in week {iso.week}, sorted from the highest count. "
         f"Sites with the same count share a rank. The area mean is over the same sites. {INFO_SNIT}", l_strimmel) if len(l_rad) else
        (tal(s_v.hunlus), f"adult female lice per fish on average in PO {valgt} in week {iso.week}, "
                          f"across {len(a_talt)} sites.", INFO_SNIT, l_strimmel),
        (f"{nab_over} of {len(nab_talt)}", f"neighbouring sites above the limit this week ({len(nab_talt)} of "
                                           f"{nab_tekst} counted lice). Their mean is {tal(nabo_nu)}"
                                           + (f", {trend(nabo_nu, nabo_foer)[2]}." if nabo_ord else "."),
         f"Neighbours are sites within <b>{appdata.NABO_KM} km</b> in a straight line from {l_navn} that have counted lice in "
         f"the past year (if fewer than {appdata.MIN_NABOER}, the nearest {appdata.MIN_NABOER}). Lice larvae drift with the "
         f"currents, so high counts nearby raise the pressure on the site. Their mean is over the neighbours that counted "
         f"in week {iso.week}; the trend compares it with their mean in {uger_foer}"
         + (f" (<b>{praecis(nabo_foer)}</b>)" if pd.notna(nabo_foer) else "") + ".", l_prikker)
        if len(nab_talt) else ("–", f"None of {nab_tekst} counted lice in week {iso.week}."),
    ]), unsafe_allow_html=True)
elif valgt is not None:
    st.markdown(sidehoved(
        f"Area brief · PO {valgt} {s_v.navn} · Week {iso.week}, {iso.year} · latest complete week",
        f"{s_v.navn}: {len(a_over)} of {len(a_talt)} sites are above the {tal(a_graense, 1)} lice limit – "
        f"lice levels are {mod_sidste_aar(s_v.hunlus, a_sidst)}",
        f"Weekly status for production area {valgt}, {s_v.navn}, based on the lice counts its fish farms report to the "
        "Norwegian Food Safety Authority, set against the lice limit (lusegrense), the government traffic light "
        "(trafikklyssystemet) and the seasonal pattern of recent years. Clear the search to return to the whole coast.",
        [("live", appdata.opdatering_tekst(panel) + ("" if not mangler else f" · {indberetning}")),
         ("database", "BarentsWatch / Mattilsynet"), ("location_on", f"{len(a_talt)} sites in this week's figures"),
         ("verified", "Independent analysis of open data")],
    ), unsafe_allow_html=True)
    st.markdown(resume([
        (tal(s_v.hunlus), f"adult female lice per fish on average in PO {valgt} in week {iso.week} – "
                          f"{mod_sidste_aar(s_v.hunlus, a_sidst)}" + (f" ({tal(a_sidst)})" if pd.notna(a_sidst) else "")
                          + f". Rank {a_rang} of {len(status)} areas.",
         f"Mean over the {len(a_talt)} sites in PO {valgt} that counted lice in week {iso.week}. {INFO_SNIT}"
         + (f"<span class='regnestykke'>vs. the same week a year earlier: {praecis(s_v.hunlus)} ÷ {praecis(a_sidst)} − 1 "
            f"= {pct(s_v.hunlus / a_sidst - 1, True)}</span>" if pd.notna(a_sidst) and a_sidst else "")
         + f"<br>The rank compares the means of all {len(status)} areas; 1 is the highest.", a_kurve),
        (f"{len(a_over)} of {len(a_talt)}", f"sites ({pct(len(a_over) / len(a_talt))}) were above the "
                                            f"{tal(a_graense, 1)} lice limit"
                                            + (f"; the highest was {a_top.iloc[0].lokalitet_navn} ({tal(a_top.iloc[0].hunlus)})"
                                               if len(a_top) else "") + ".", INFO_GRAENSE, a_strimmel),
        (appdata.TRAFIKLYS[s_v.trafiklys], f"traffic light for PO {valgt}. The colour is set by the government "
                                           f"(latest decision {s_v.lys_fra:%b %Y}) from estimated lice mortality in wild "
                                           "salmon – not from this week's counts."
                                           + (" Red means a cut in production capacity." if s_v.trafiklys == "red" else ""),
         INFO_LYS, lys_prikker(valgt)),
    ]), unsafe_allow_html=True)
else:
    st.markdown(sidehoved(
        f"Weekly brief · Sea lice in Norwegian salmon farming · Week {iso.week}, {iso.year} · latest complete week",
        f"Lice levels are {abs(aendring):.0%} {retning} than a year ago – pressure is highest in {status.loc[top, 'navn']}",
        "Weekly status on sea lice (lakselus) in all 13 production areas (produksjonsområder), based on the lice counts "
        "fish farms report to the Norwegian Food Safety Authority. Figures are set against the lice limit (lusegrense), "
        "the government traffic-light system (trafikklyssystemet) and the seasonal pattern of recent years.",
        [("live", appdata.opdatering_tekst(panel) + ("" if not mangler else f" · {indberetning}")), ("database", "BarentsWatch / Mattilsynet"),
         ("location_on", f"{len(talt)} sites in this week's figures"), ("verified", "Independent analysis of open data")],
    ), unsafe_allow_html=True)

    st.markdown(resume([
        (tal(gns), f"adult female lice per fish on average along the coast in week {iso.week} – {abs(aendring):.0%} "
                   f"{retning} than the same week last year ({tal(gns_sidst)}).",
         f"Mean over the {len(talt)} sites that counted lice in week {iso.week}. {INFO_SNIT}"
         f"<span class='regnestykke'>vs. the same week a year earlier ({len(aar_siden)} sites): "
         f"{praecis(gns)} ÷ {praecis(gns_sidst)} − 1 = {pct(aendring, True)}</span>",
         kurve(*ugeserie(raa), note=KURVE_NOTE)),
        (f"{len(over)} of {len(talt)}", f"sites ({pct(len(over) / len(talt))}) were above the {tal(graense, 1)} lice limit"
                                        + ("; most in " + " and ".join(f"PO {o}" for o in over_pr_omr.index[:2]) if len(over) else "") + ".",
         INFO_GRAENSE, andelsbjaelke(len(over) / len(talt), f"Red: the {len(over)} sites above the limit")),
        (f"{len(roede)} of 13", f"production areas {'has' if len(roede) == 1 else 'have'} a red traffic light"
                                + (": " + ", ".join(roede["navn"]) if len(roede) else "")
                                + f". The colour is set by the government (latest decision {lys_fra:%b %Y}) from estimated lice "
                                "mortality in wild salmon – not from this week's counts. Red means a cut in production capacity.",
         INFO_LYS, lys_prikker()),
    ]), unsafe_allow_html=True)

# 3b. Værd at se på i denne uge: kort med det højeste lusetal og de største udsving – et klik åbner anlægget.
# Forskellen måles i lus pr. fisk, så små tal ikke giver store procenter; det højeste anlæg tælles ikke igen.
if lok_v is None:
    u = appdata.udsving(raa, seneste)
    u = u[u["omraade"] == valgt] if valgt is not None else u
    udsving_kort = []  # (nøgle, ikon, etiket, navn, stort tal, farve, note, (område, anlæg))
    if len(u):
        h = u.loc[u["nu"].idxmax()]
        udsving_kort.append(("hoejest", "priority_high", "Highest count", h.lokalitet_navn, tal(h.nu),
                             LUS_FARVER[lus_niveau(h.nu)], f"adult female lice per fish · PO {h.omraade}",
                             (h.omraade, h.lokalitet)))
        rest = u.drop(index=h.name).dropna(subset=["forskel"])
        for noegle, ikon_, etiket, r in (("op", "trending_up", "Sharpest rise", rest.loc[rest["forskel"].idxmax()] if len(rest) else None),
                                         ("ned", "trending_down", "Steepest fall", rest.loc[rest["forskel"].idxmin()] if len(rest) else None)):
            if r is not None and (r.forskel > 0 if noegle == "op" else r.forskel < 0):
                udsving_kort.append((noegle, ikon_, etiket, r.lokalitet_navn, f"{r.forskel:+.2f}".replace("-", "−"),
                                     "#D64545" if noegle == "op" else "#1F7A8C",
                                     f"{tal(r.nu)} now vs. {tal(r.foer)} in {uger_foer} · PO {r.omraade}",
                                     (r.omraade, r.lokalitet)))
    if valgt is None:
        stigning = (solide["hunlus"] / solide["hunlus_4u_foer"] - 1).dropna()
        if len(stigning) and stigning.max() > 0:
            o = int(stigning.idxmax())
            udsving_kort.append(("omraade", "map", "Fastest-rising area", f"PO {o} · {status.loc[o, 'navn']}",
                                 pct(stigning.max(), True), "#D64545",
                                 f"{tal(status.loc[o, 'hunlus'])} now vs. {tal(status.loc[o, 'hunlus_4u_foer'])} in {uger_foer}",
                                 (o, None)))
    if udsving_kort:
        st.markdown(f'<div class="udsving-hoved"><b>Worth a look this week</b><span>'
                    f'{"In PO " + str(valgt) + " · " if valgt is not None else ""}click a card to open it</span></div>',
                    unsafe_allow_html=True)
        for kol, (noegle, ikon_, etiket, navn_, stort, farve, note, maal) in zip(st.columns(len(udsving_kort)), udsving_kort):
            with kol, st.container(key=f"udsving_{noegle}"):
                st.markdown(f'<div class="udsving-kort"><div class="etiket">{ikon(ikon_)} {etiket}</div>'
                            f'<div class="navn">{navn_}</div><div class="stort" style="color:{farve}">{stort}</div>'
                            f'<div class="note">{note}</div></div>', unsafe_allow_html=True)
                st.button("Open area →" if maal[1] is None else "Open site →", key=f"aabn_{noegle}",
                          on_click=aabn, args=maal, type="tertiary")

# --- 4. Figur: kort og rangering --------------------------------------------------

# 4a. Kortudsnit
def udsnit(polygon: list, bredde: int = 420, hoejde: int = 440) -> pdk.ViewState:
    """Kortudsnit, der rammer polygonet (web-mercator), så det valgte område fylder kortet."""
    lon, lat = [p[0] for p in polygon], [p[1] for p in polygon]
    y = lambda b: math.log(math.tan(math.pi / 4 + math.radians(b) / 2))
    midt_y = (y(max(lat)) + y(min(lat))) / 2
    zoom = min(math.log2(bredde / 512 * 360 / (max(lon) - min(lon))),  # deck.gl: verden er 512 px bred ved zoom 0
               math.log2(hoejde / 512 * 2 * math.pi / (y(max(lat)) - y(min(lat))))) - 0.2
    return pdk.ViewState(longitude=(max(lon) + min(lon)) / 2, latitude=math.degrees(2 * math.atan(math.exp(midt_y)) - math.pi / 2),
                         zoom=min(zoom, 8))


def naer_udsnit(lat: float, lon: float, bredde: int = 420) -> pdk.ViewState:
    """Kortudsnit om et anlæg, så ringen med naboerne (20 km) fylder kortet."""
    meter_pr_px = 40_075_016 / 512 * math.cos(math.radians(lat))  # ved zoom 0
    return pdk.ViewState(latitude=lat, longitude=lon, zoom=math.log2(meter_pr_px * bredde / (2.5 * appdata.NABO_KM * 1000)))


def fra_kort() -> None:
    objekter = [o for liste in st.session_state[f"kort_{n}"].selection.get("objects", {}).values() for o in liste]
    if objekter:
        o = objekter[0]
        vaelg(int(o["omraade"]), int(o["lokalitet"]) if "lokalitet" in o else None)


def fra_soejler() -> None:
    valg_ = st.session_state[f"rang_{n}"].selection.get("vaelg", [])
    if valg_ and "lokalitet" in valg_[0]:
        vaelg(st.session_state.po_valgt, int(valg_[0]["lokalitet"]))
    elif valg_:
        vaelg(int(valg_[0]["omraade"]))


# 4b. Overskrift – konklusionen og den gældende lusegrænse står i titlen
kort_under = (f"Adult female lice per fish, week {iso.week} {iso.year}. Dots: sites, coloured by lice level. Area outline: the "
              "government traffic light, which reflects estimated harm to wild salmon – not this week's counts.")
if valgt is None:
    over_tekst = "above" if status.loc[top, "hunlus"] > graense else "below"
    st.markdown(figur(
        next(nr), f"{status.loc[top, 'navn']} has the highest lice level among the larger areas ({tal(status.loc[top, 'hunlus'])}) – "
                  f"{over_tekst} the {tal(graense, 1)} lice limit",
        kort_under,
    ), unsafe_allow_html=True)
else:
    st.markdown(figur(
        next(nr), f"{len(a_over)} of {len(a_talt)} sites in {s_v.navn} are above the {tal(a_graense, 1)} lice limit"
                  + (f" – the highest is {a_top.iloc[0].lokalitet_navn} ({tal(a_top.iloc[0].hunlus)})" if len(a_top) else ""),
        kort_under + (f" Ring: {appdata.NABO_KM} km around {l_navn}." if lok_v is not None else ""),
    ), unsafe_allow_html=True)

venstre, hoejre = st.columns([1, 1.15], gap="large")
# 4c. Kort: områder farvet efter trafiklys, anlæg farvet efter lusetal
with venstre:
    st.markdown(f'<div class="korthjaelp">{ikon("touch_app")} Click an area on the map or a bar to see every site in it</div>',
                unsafe_allow_html=True)
    lok = talt.dropna(subset=["lat", "lon", "hunlus"]).assign(omraade=lambda d: d["omraade"].astype(int))
    # Med et valgt anlæg står naboerne i fuld farve; med et valgt område hele området.
    if lok_v is not None:
        i_valgt = lok["lokalitet"].isin(set(nab["lokalitet"]) | {lok_v})
    else:
        i_valgt = (lok["omraade"] == valgt) if valgt else pd.Series(True, index=lok.index)
    lok["farve"] = [rgba(LUS_FARVER[lus_niveau(v)], 235 if v_ else 70) for v, v_ in zip(lok["hunlus"], i_valgt)]
    lok["tip"] = ("<b>" + lok["lokalitet_navn"] + "</b><br>PO " + lok["omraade"].astype(str) + " · "
                  + lok["hunlus"].map(tal) + " adult female lice per fish")
    lok = lok[["lon", "lat", "omraade", "lokalitet", "farve", "tip"]]
    po_kort = po.reset_index().join(status[["hunlus", "n_lok"]], on="omraade").assign(
        # Fladen er neutral grå; trafiklyset står kun i kanten, så prikkerne (lusetallet) er det eneste, der lyser op.
        fyld=lambda d: [rgba(FARVER["taage"], 70 if o == valgt else 14 if valgt else 38) for o in d["omraade"]],
        kant=lambda d: [rgba(LYS_FARVER[c][0], 255 if o == valgt else 80 if valgt else 210) for c, o in zip(d["trafiklys"], d["omraade"])],
        tip=lambda d: "<b>PO " + d["omraade"].astype(str) + " · " + d["navn"] + "</b><br>"
                      + d["hunlus"].map(tal) + " adult female lice per fish · " + d["n_lok"].fillna(0).astype(int).astype(str)
                      + " sites<br>Traffic light: " + d["trafiklys"].map(appdata.TRAFIKLYS)
                      + " (decided " + d["lys_fra"].dt.strftime("%b %Y") + ")<br><i>Click to see its sites</i>",
    )[["omraade", "polygon", "fyld", "kant", "tip"]]
    lag = [
        pdk.Layer("PolygonLayer", po_kort, id="omraader", get_polygon="polygon", get_fill_color="fyld",
                  get_line_color="kant", line_width_min_pixels=1.6, pickable=True, auto_highlight=True,
                  highlight_color=[111, 125, 60, 70]),
        pdk.Layer("ScatterplotLayer", lok, id="anlaeg", get_position=["lon", "lat"], get_fill_color="farve",
                  get_radius=2400, radius_min_pixels=2.2 if not valgt else 4, radius_max_pixels=9, stroked=True,
                  get_line_color=[255, 255, 255], line_width_min_pixels=0.4, pickable=True, auto_highlight=True),
    ]
    if lok_v is not None:
        # Anlægget markeres, også når det ikke talte i ugen (så gråt); ringen viser, hvor naboerne er talt fra.
        markeret = lok[lok["lokalitet"] == lok_v]
        if markeret.empty:
            markeret = pd.DataFrame({"lon": [a_lok.lon], "lat": [a_lok.lat], "omraade": [valgt], "lokalitet": [lok_v],
                                     "farve": [rgba(FARVER["skifer"], 235)],
                                     "tip": [f"<b>{l_navn}</b><br>No count in week {iso.week}"]})
        lag.insert(1, pdk.Layer("ScatterplotLayer", markeret, id="ring", get_position=["lon", "lat"],
                                get_radius=appdata.NABO_KM * 1000, filled=False, stroked=True,
                                get_line_color=[11, 34, 48, 140], line_width_min_pixels=1.2))
        lag.append(pdk.Layer("ScatterplotLayer", markeret, id="markeret",
                             get_position=["lon", "lat"], get_fill_color="farve", get_radius=2400, radius_min_pixels=8,
                             stroked=True, get_line_color=[11, 34, 48], line_width_min_pixels=2.5, pickable=True))
    st.pydeck_chart(pdk.Deck(
        layers=lag,
        initial_view_state=(naer_udsnit(float(a_lok.lat), float(a_lok.lon)) if lok_v is not None
                            else udsnit(po.loc[valgt, "polygon"]) if valgt else pdk.ViewState(latitude=65.0, longitude=14.2, zoom=3.25)),
        views=[pdk.View(type="MapView", controller={"scrollZoom": False, "dragPan": True, "doubleClickZoom": True})],
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={"html": "{tip}", "style": {"backgroundColor": "#0B2230", "color": "#FFFFFF",
                                             "fontFamily": "Inter, sans-serif", "fontSize": "12px"}},
    ), height=440, on_select=fra_kort, selection_mode="single-object", key=f"kort_{n}")

# 4d. Søjler: alle områder – eller hvert anlæg i det valgte område
# Grænselinjer: 0,2 i forårsugerne og den almindelige grænse på 0,5. Teksterne står på hver sin linje.
graenser = pd.DataFrame({"x": [0.2, 0.5], "t": ["0.2 spring weeks", "0.5 lice limit"]})
linjer = alt.Chart(graenser).mark_rule(strokeDash=[3, 3], color="#D64545", opacity=.7).encode(x="x:Q")
linjetekst = (
    alt.Chart(graenser.iloc[[0]]).mark_text(align="left", dx=3, fontSize=10, color="#D64545")
    .encode(x="x:Q", y=alt.value(-16), text="t:N")
    + alt.Chart(graenser.iloc[[1]]).mark_text(align="right", dx=-3, fontSize=10, color="#D64545")
    .encode(x="x:Q", y=alt.value(-4), text="t:N")
)
farveskala = alt.Scale(domain=["lav", "mellem", "hoej"], range=[LUS_FARVER["lav"], LUS_FARVER["mellem"], LUS_FARVER["hoej"]])

with hoejre:
    if valgt is None:
        rang = status.reset_index().assign(
            etiket=lambda d: "PO " + d["omraade"].astype(str) + "  " + d["navn"] + d["n_lok"].map(lambda n_: " *" if n_ < MIN_LOK else ""),
            niveau=lambda d: d["hunlus"].map(lus_niveau),
            tekst=lambda d: d["hunlus"].map(tal),
            lille=lambda d: d["n_lok"] < MIN_LOK,
        )
        # Små områder nederst og nedtonet, så rangeringen stemmer med konklusionen (som kun bygger på de solide).
        rang = rang.sort_values(["lille", "hunlus"], ascending=[True, False])
        y = alt.Y("etiket:N", sort=list(rang["etiket"]), title=None, axis=alt.Axis(labelLimit=220, labelFontSize=11.5, labelColor="#1B2B36"))
        soejler = alt.Chart(rang).mark_bar(height=15, cursor="pointer").encode(
            x=alt.X("hunlus:Q", title="Adult female lice per fish", scale=alt.Scale(domain=[0, 0.55]),
                    axis=alt.Axis(format=".1f", tickCount=6, grid=True)),
            y=y,
            color=alt.Color("niveau:N", legend=None, scale=farveskala),
            opacity=alt.condition("datum.lille", alt.value(0.35), alt.value(1.0)),
            tooltip=[alt.Tooltip("etiket:N", title="Area"), alt.Tooltip("hunlus:Q", title="Female lice", format=".3f"),
                     alt.Tooltip("n_lok:Q", title="Sites")],
        ).add_params(alt.selection_point(name="vaelg", fields=["omraade"]))
        tekster = alt.Chart(rang).mark_text(align="left", dx=4, fontSize=11, color="#1B2B36").encode(
            x="hunlus:Q", y=y, text="tekst:N")
        st.altair_chart((soejler + tekster + linjer + linjetekst).properties(height=440), width="stretch",
                        on_select=fra_soejler, key=f"rang_{n}")
    else:
        s = status.loc[valgt]
        omr_tal = talt.loc[talt["omraade"] == valgt, "hunlus"].dropna()
        top_x = max(0.55, min(float(omr_tal.max()) * 1.12, 1.2))
        omr_anlaeg = talt[talt["omraade"] == valgt].dropna(subset=["hunlus"]).sort_values("hunlus", ascending=False).assign(
            niveau=lambda d: d["hunlus"].map(lus_niveau), tekst=lambda d: d["hunlus"].map(tal),
            markeret=lambda d: d["lokalitet"] == lok_v,
            # Enkelte anlæg kan ligge langt over resten; aksen kappes, og søjlen ender i en pil med det rigtige tal.
            x_vis=lambda d: d["hunlus"].clip(upper=top_x), kappet=lambda d: d["hunlus"] > top_x,
            tekst_vis=lambda d: d["tekst"].where(~d["kappet"], d["tekst"] + " →"),
            # Navne kan gå igen – lokalitetsnummeret skiller dem ad på aksen.
            etiket=lambda d: d["lokalitet_navn"].where(~d["lokalitet_navn"].duplicated(keep=False),
                                                       d["lokalitet_navn"] + " (" + d["lokalitet"].astype(int).astype(str) + ")"),
        )
        n_over = int((omr_anlaeg["over_graense"] == "Ja").sum())
        lys_kant, lys_bg, lys_tekst = LYS_FARVER[s.trafiklys]
        with st.container(horizontal=True, gap="small"):
            st.button("← All areas", on_click=vaelg, args=(None,), key="alle_omraader", type="tertiary")
            if lok_v is not None:
                st.button(f"← All of PO {valgt}", on_click=vaelg, args=(valgt,), key="hele_omraadet", type="tertiary")
        st.markdown(
            f'<div class="omraadehoved"><b>PO {valgt} · {s.navn}</b>'
            f'<span>{len(omr_anlaeg)} sites · mean {tal(s.hunlus)} · {n_over} above the limit · '
            f'<i class="prik" style="background:{lys_kant}"></i>{appdata.TRAFIKLYS[s.trafiklys]} traffic light</span></div>',
            unsafe_allow_html=True)
        y = alt.Y("etiket:N", sort=list(omr_anlaeg["etiket"]), title=None,
                  axis=alt.Axis(labelLimit=180, labelFontSize=11, labelColor="#1B2B36", labelOverlap=False))
        soejler = alt.Chart(omr_anlaeg).mark_bar(height=11, cursor="pointer", stroke=FARVER["blaek"]).encode(
            x=alt.X("x_vis:Q", title="Adult female lice per fish", scale=alt.Scale(domain=[0, top_x]),
                    axis=alt.Axis(format=".1f", grid=True, orient="top")),
            y=y,
            color=alt.Color("niveau:N", legend=None, scale=farveskala),
            strokeWidth=alt.condition("datum.markeret", alt.value(2), alt.value(0)),
            tooltip=[alt.Tooltip("lokalitet_navn:N", title="Site"), alt.Tooltip("hunlus:Q", title="Female lice", format=".2f"),
                     alt.Tooltip("temp:Q", title="Sea temp. °C", format=".1f")],
        ).add_params(alt.selection_point(name="vaelg", fields=["lokalitet"]))
        tekster = alt.Chart(omr_anlaeg).mark_text(align="left", dx=4, fontSize=10, color="#1B2B36").encode(
            x="x_vis:Q", y=y, text="tekst_vis:N")
        snit_linje = alt.Chart(pd.DataFrame({"x": [s.hunlus]})).mark_rule(color=FARVER["blaek"], strokeWidth=1.2).encode(x="x:Q")
        omr_graenser = alt.Chart(graenser).mark_rule(strokeDash=[4, 3], color="#D64545", strokeWidth=1.2).encode(x="x:Q")
        graf = soejler + tekster + snit_linje + omr_graenser
        # Lange områder rulles i en ramme med samme højde som kortet.
        with st.container(height=360, border=False):
            st.altair_chart(graf.properties(height=max(120, 17 * len(omr_anlaeg))), width="stretch",
                            on_select=fra_soejler, key=f"rang_{n}")
        st.markdown(f'<div class="kilde">Bars: each site that counted lice in week {iso.week}. Solid line: area mean. '
                    f'Dashed: 0.2 and 0.5 limits. Click a bar to open that site.</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="forklaring">'
    f'<span><i class="prik" style="background:{LUS_FARVER["lav"]}"></i>Below 0.2</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["mellem"]}"></i>0.2–0.5</span>'
    f'<span><i class="prik" style="background:{LUS_FARVER["hoej"]}"></i>Above 0.5</span>'
    f'<span><i class="prik" style="background:{LYS_FARVER["green"][0]}"></i><i class="prik" style="background:{LYS_FARVER["yellow"][0]}"></i>'
    f'<i class="prik" style="background:{LYS_FARVER["red"][0]}"></i>Traffic light (area outline: government decision on wild-salmon risk)</span></div>',
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Area figures are unweighted means over sites that counted lice that week. "
                  f"* Fewer than {MIN_LOK} sites (faded, at the bottom) – the figure is uncertain and excluded from the conclusions."),
            unsafe_allow_html=True)

# --- 5. Figurer for et anlæg -----------------------------------------------------------
if lok_v is not None:
    # 5a. Lusehistorik: anlægget mod lusegrænsen og naboernes snit, de seneste to år
    # Titlen tæller over de samme to år, som grafen viser, og siger hvornår anlægget sidst var over grænsen.
    talte = hist.dropna(subset=["hunlus"])
    over_uger = talte[talte["hunlus"] > talte["graense"]]
    sidst_over = over_uger["uge_start"].max().isocalendar() if len(over_uger) else None
    st.markdown(figur(
        next(nr), (f"{l_navn} was above the lice limit in {len(over_uger)} of the {len(talte)} weeks it counted in the "
                   f"past two years – last in week {sidst_over.week}, {sidst_over.year}") if sidst_over else
                  f"{l_navn} stayed below the lice limit in all {len(talte)} weeks it counted in the past two years",
        f"Adult female lice per fish per week, past two years. Solid line: {l_navn}. Dashed: mean of {nab_tekst}. "
        f"Red step: the lice limit in PO {valgt} (0.2 in the spring weeks). Gaps: weeks without a count.",
    ), unsafe_allow_html=True)
    hx = alt.X("uge_start:T", title=None, axis=alt.Axis(format="%b %Y", grid=False, labelFontSize=10))
    h_graense = alt.Chart(hist).mark_line(interpolate="step-after", color="#D64545", strokeDash=[4, 3], strokeWidth=1.2).encode(
        x=hx, y=alt.Y("graense:Q", title="Adult female lice per fish", axis=alt.Axis(format=".1f")))
    h_nabo = alt.Chart(hist).mark_line(color=FARVER["skifer"], strokeDash=[3, 2], strokeWidth=1.2).encode(x=hx, y="nabo_snit:Q")
    h_selv = alt.Chart(hist).mark_line(color=FARVER["serie"], strokeWidth=2, point=alt.OverlayMarkDef(size=14, color=FARVER["serie"])).encode(
        x=hx, y="hunlus:Q",
        tooltip=[alt.Tooltip("uge_start:T", title="Week of", format="%d %b %Y"),
                 alt.Tooltip("hunlus:Q", title=l_navn, format=".2f"),
                 alt.Tooltip("nabo_snit:Q", title="Neighbours' mean", format=".2f"),
                 alt.Tooltip("graense:Q", title="Lice limit", format=".1f")])
    st.altair_chart((h_graense + h_nabo + h_selv).properties(height=260), width="stretch")
    st.markdown(kilde(f"{l_navn} (site no. {lok_v}). The limit is the one most sites in PO {valgt} reported that week."),
                unsafe_allow_html=True)

    # 5b. Naboerne: smittepresset omkring anlægget – hvem er over grænsen, og hvor går det hen?
    st.markdown(figur(
        next(nr), (f"{nab_over} of {len(nab_talt)} neighbouring sites {'is' if nab_over == 1 else 'are'} above the limit this week"
                   + (f" – lice pressure around {l_navn} is {nabo_ord}" if nabo_ord else "")) if len(nab_talt) else
                  f"None of the neighbouring sites counted lice in week {iso.week}",
        f"{nab_tekst[0].upper() + nab_tekst[1:]}, nearest first: adult female lice per fish in week {iso.week} and the change "
        "vs. the previous 4 weeks.",
    ), unsafe_allow_html=True)

    def nabo_raekke(navn: str, km: str, omraade: int, nu: float, foer: float, over_: str, klasse: str = "") -> str:
        t_ikon, t_farve, t_tekst = trend(nu, foer)
        # Over grænsen står tallet i rødt, så det også ses på mobil, hvor kolonnen "Above limit" er skjult.
        lus = (f'<span style="color:{"#D64545" if over_ == "Ja" else "inherit"}">{tal(nu)}</span><span class="minibar" style="width:{min(nu / 0.5, 1) * 60:.0f}px;'
               f'background:{LUS_FARVER[lus_niveau(nu)]}"></span>') if pd.notna(nu) else '<span style="color:#6B7A86">not counted</span>'
        over_tekst_ = {"Ja": '<span style="color:#D64545;font-weight:600">Yes</span>', "Nei": "No"}.get(over_, "–")
        return (f'<tr class="{klasse}"><td class="navn">{navn}</td><td class="tal">{km}</td><td class="po ekstra">{omraade}</td>'
                f'<td class="tal">{lus}</td>'
                f'<td class="tal" style="color:{t_farve}"><span class="ekstra">{ikon(t_ikon, t_farve, t_tekst) if pd.notna(nu) else ""}</span> '
                f'{aendring_celle(nu, foer)}</td><td class="tal ekstra">{over_tekst_}</td></tr>')

    nabo_raekker = [nabo_raekke(f"{l_navn} <span style='color:#6B7A86'>(selected)</span>", "–", valgt, l_nu, l_foer,
                                "Ja" if l_over else ("Nei" if len(l_rad) else ""), "valgt")]
    nabo_raekker += [nabo_raekke(radlink(r.lokalitet_navn, f"site:{r.lokalitet}"), f"{r.km:.1f} km", r.omraade, r.hunlus, r.hunlus_4u_foer,
                                 r.over_graense if isinstance(r.over_graense, str) else "") for r in nab.itertuples()]
    st.markdown(
        '<table class="tabel"><thead><tr><th>Site</th>'
        f'<th class="tal">Distance{info(f"Straight-line distance from the position {l_navn} reports. The way by sea can be longer.", "hoejre")}</th>'
        '<th class="ekstra">PO</th>'
        f'<th class="tal">Female lice / fish{info(f"The count each site reported for week {iso.week}. Red: above the lice limit. <i>Not counted</i>: no count that week, for example between production cycles.", "hoejre")}</th>'
        f'<th class="tal">Δ 4 weeks{info(INFO_AENDRING, "hoejre")}</th>'
        f'<th class="tal ekstra">Above limit{info(INFO_GRAENSE, "hoejre")}</th></tr></thead><tbody>'
        + "".join(nabo_raekker) + "</tbody></table>",
        unsafe_allow_html=True,
    )
    st.markdown(kilde(f"Neighbours: sites that counted lice in the past year, by straight-line distance from the reported "
                      f"position (sea routes can be longer). Within {appdata.NABO_KM} km, or the {appdata.MIN_NABOER} nearest "
                      "if fewer are that close. Red figure: above the lice limit. Δ 4 weeks as in the status table below."), unsafe_allow_html=True)

# --- 6. Figur: statustabel ----------------------------------------------------------
st.markdown(figur(
    next(nr), "Status by production area",
    "Lice level, change vs. the previous 4 weeks, share of sites above the limit and sea temperature.",
), unsafe_allow_html=True)

raekker = []
for o, s in status.iterrows():
    t_ikon, t_farve, t_tekst = trend(s.hunlus, s.hunlus_4u_foer)
    aend_tekst = aendring_celle(s.hunlus, s.hunlus_4u_foer)
    farve = LUS_FARVER[lus_niveau(s.hunlus)]
    lys_kant, _, lys_tekst = LYS_FARVER[s.trafiklys]
    raekker.append(
        f'<tr class="{"valgt" if o == valgt else ""}"><td class="po ekstra">{o}</td><td class="navn">{s.navn if o == valgt else radlink(s.navn, f"po:{o}")}{" <span style=\'color:#6B7A86\'>*</span>" if s.n_lok < MIN_LOK else ""}</td>'
        f'<td class="lys"><i class="prik" style="background:{lys_kant}"></i>{appdata.TRAFIKLYS[s.trafiklys]}</td>'
        f'<td class="tal">{tal(s.hunlus)}<span class="minibar" style="width:{min(s.hunlus / 0.5, 1) * 60:.0f}px;background:{farve}"></span></td>'
        f'<td class="tal" style="color:{t_farve}"><span class="ekstra">{ikon(t_ikon, t_farve, t_tekst)}</span> {aend_tekst}</td>'
        f'<td class="tal" style="color:{"#D64545" if s.andel_over >= .1 else "inherit"}">{pct(s.andel_over)}</td>'
        f'<td class="tal ekstra">{tal(s.temp, 1)} °C</td><td class="tal ekstra">{int(s.n_lok)}</td></tr>'
    )
st.markdown(
    '<table class="tabel"><thead><tr><th class="ekstra">PO</th><th>Production area</th>'
    f'<th>Traffic<span class="ekstra"> light</span>{info(INFO_LYS)}</th>'
    f'<th class="tal">Female lice / fish{info(f"Mean adult female lice per fish over the sites in the area that counted in week {iso.week}. {INFO_SNIT}", "hoejre")}</th>'
    f'<th class="tal">Δ 4 weeks{info(INFO_AENDRING, "hoejre")}</th>'
    f'<th class="tal">Above limit{info(f"Share of the sites in the area that counted in week {iso.week} with a count above the limit. Red from 10%.<br><br>{INFO_GRAENSE}", "hoejre")}</th>'
    f'<th class="tal ekstra">Sea temp.{info("Mean sea temperature reported by the sites in the area. Lice develop faster in warm water, so temperature drives the season.", "hoejre")}</th>'
    f'<th class="tal ekstra">Sites{info(f"Sites that counted lice in week {iso.week}. Fewer than {MIN_LOK} (*): the area figures are uncertain.", "hoejre")}</th>'
    '</tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde(f"Δ 4 weeks: change vs. the mean of the four preceding weeks; below {LAVT_NIVEAU} lice per fish "
                  f"shown in lice per fish instead of percent. * Fewer than {MIN_LOK} sites."), unsafe_allow_html=True)

# --- 7. Figur: små multipler --------------------------------------------------------
foerste, i_aar = int(profil["foerste_aar"].iloc[0]), int(profil["aar"].iloc[0])
st.markdown(figur(
    next(nr), f"{over_snit} of {len(uge_nu)} areas are above the normal level for the time of year",
    f"Adult female lice per fish per week. Line: {i_aar}. Dashed: mean {foerste}–{i_aar - 1}. Band: lowest–highest level in the same period."
    + (f" PO {valgt} is shown first." if valgt is not None else ""),
), unsafe_allow_html=True)

sm = profil.assign(titel=lambda d: "PO " + d["omraade"].astype(str) + " · " + d["omraade"].map(navne))
orden = [f"PO {o} · {navne[o]}" for o in sorted(navne)]
orden_sm = sorted(orden, key=lambda t: t != f"PO {valgt} · {navne.get(valgt)}")  # det valgte område først
basis = alt.Chart().encode(x=alt.X("uge:Q", title=None, scale=alt.Scale(domain=[1, 52]),
                                   axis=alt.Axis(values=[1, 13, 26, 39, 52], grid=False, labelFontSize=9)))
baand = basis.mark_area(color=FARVER["taage"], opacity=.35).encode(
    y=alt.Y("lav:Q", title=None, axis=alt.Axis(values=[0, 0.5, 1], format=".1f", labelFontSize=9)), y2="hoej:Q")
snit = basis.mark_line(color=FARVER["skifer"], strokeDash=[3, 2], strokeWidth=1).encode(y="snit:Q")
nu = basis.mark_line(color=FARVER["serie"], strokeWidth=2).encode(y="i_aar:Q")
# Annotation: seneste uges værdi markeres og skrives direkte i hvert panel.
sm["er_sidste"] = sm["uge"] == sm.dropna(subset=["i_aar"])["uge"].max()
nu_pkt = basis.mark_circle(color=FARVER["serie"], size=26, opacity=1).encode(y="i_aar:Q").transform_filter("datum.er_sidste")
nu_tal = basis.mark_text(align="left", dx=5, fontSize=10, fontWeight=600, color=FARVER["serie"]).encode(
    y="i_aar:Q", text=alt.Text("i_aar:Q", format=".2f")).transform_filter("datum.er_sidste")
def smaa_multipler(kolonner: int, bredde: int, hoejde: int) -> alt.FacetChart:
    return alt.layer(baand, snit, nu, nu_pkt, nu_tal, data=sm).properties(width=bredde, height=hoejde).facet(
        facet=alt.Facet("titel:N", sort=orden_sm, header=alt.Header(labelFontSize=11, labelPadding=4)), columns=kolonner,
    ).resolve_scale(y="shared")


# Tre kolonner på brede skærme, én på mobil – CSS i udseende.py viser den ene og skjuler den anden.
with st.container(key="smaa_bred"):
    st.altair_chart(smaa_multipler(3, 225, 90), width="content")
with st.container(key="smaa_mobil"):
    st.altair_chart(smaa_multipler(1, 285, 64), width="content")
st.markdown(kilde(f"Week 53 is omitted. Mean and band are based on {foerste}–{i_aar - 1}."), unsafe_allow_html=True)

# --- 8. Figur: sæsonmønster ---------------------------------------------------------
st.markdown(figur(
    next(nr), (f"The peak comes later the further north: around week {syd_top} in the south vs. week {nord_top} in Finnmark"
        if nord_top > syd_top else
        f"The lice peak comes around week {syd_top} in the south and week {nord_top} in Finnmark"),
    f"Mean adult female lice per fish by ISO week, {foerste}–{i_aar - 1}.",
), unsafe_allow_html=True)
vx = alt.X("uge:O", title="ISO week", axis=alt.Axis(values=[1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50], labelAngle=0))
vy = alt.Y("titel:N", sort=orden, title=None, axis=alt.Axis(labelLimit=240, labelColor="#1B2B36", labelOverlap=False))
varme = alt.Chart(sm).mark_rect().encode(
    x=vx, y=vy,
    color=alt.Color("snit:Q", title="Female lice / fish", scale=alt.Scale(range=SEKVENS),
                    legend=alt.Legend(orient="right", gradientLength=180, format=".1f")),
    tooltip=[alt.Tooltip("titel:N", title="Area"), alt.Tooltip("uge:O", title="Week"),
             alt.Tooltip("snit:Q", title="Mean", format=".3f")],
)
# Annotation: hvert områdes topuge markeres, så forskydningen mod nord kan ses direkte.
topper = sm.loc[sm.groupby("titel")["snit"].idxmax(), ["titel", "uge", "snit"]]
top_pkt = alt.Chart(topper).mark_point(shape="circle", filled=True, size=34, color="#FFFFFF", stroke=FARVER["blaek"],
                                       strokeWidth=1.2, opacity=1).encode(
    x=vx, y=vy, tooltip=[alt.Tooltip("titel:N", title="Area"), alt.Tooltip("uge:O", title="Peak week")])
st.altair_chart((varme + top_pkt).properties(height=13 * 28), width="stretch")
st.markdown(kilde("○ = the area's peak week (highest mean)."), unsafe_allow_html=True)

# --- 9. Metode og forbehold -----------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Method and caveats.</b> Data are weekly lice counts per site from BarentsWatch '
    "(reported to the Norwegian Food Safety Authority). Area figures are unweighted means over sites that counted "
    "lice that week; the number of fish per site is not included. Farms report a week's counts during the following "
    "week, so the brief usually trails the calendar by 1–2 weeks: the latest week is only included once at least "
    "80% of sites have reported. The lice limit is 0.5 adult female lice per fish (0.2 during the spring weeks). "
    "The traffic light is the colour the government had set for each production area in the week shown. It is decided "
    "every second year from estimated lice-induced mortality in wild salmon, so an area can be red even when its farms "
    "are below the lice limit. The analysis is independent "
    "and not prepared for or by any company.</div>",
    unsafe_allow_html=True,
)
