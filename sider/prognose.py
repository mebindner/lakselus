"""Prognose: lusetallet de næste fire uger, behandlingernes effekt og en ærlig evaluering af modellen.

Siden er delt i to: først det, alle kan bruge (prognosen og behandlingseffekten, i almindeligt sprog),
derefter evalueringen for fagfolk (modelsammenligning, hvor modellen hjælper, backtest).

Indhold
0. Hjælpefunktioner
1. Data og modelresultater  – backtest, valgt model, skill og Diebold–Mariano-test
2. Områdevalg               – følger valget på forsiden; prognosen for området beregnes
3. Sidehoved og resumé      – prognosen for området i almindeligt sprog
4. Figur: prognose for det valgte område (med 80 %-interval)
5. Figur: behandlingernes effekt (hændelsesstudie med kontrolgruppe)
6. Afsnit for fagfolk: hvor god er prognosen? – opsummering af skill, test og kalibrering
7. Figur: modelsammenligning
8. Figur: hvor hjælper modellen
9. Figur: backtest-forløb
9b. Figur: regnskabet – de offentliggjorte prognoser mod det, der skete
10. Metode

Figurerne nummereres i rækkefølge (nr).
"""

import altair as alt
import pandas as pd
import streamlit as st

from lakselus import appdata, evaluering as ev, regnskab
from lakselus.modelrapport import BASELINES, NAVNE
from lakselus.udseende import FARVER, afsnit, figur, ikon, info, kilde, resume, sidehoved


# --- 0. Hjælpefunktioner ---------------------------------------------------------------

def tal(v: float, d: int = 3) -> str:
    return f"{v:.{d}f}"


def pct(v: float) -> str:
    return f"{v:+.0%}".replace("-", "−")


def p_tekst(p: float) -> str:
    return "< 0.001" if p < 0.001 else tal(p, 3)


nr = iter(range(1, 10))  # figurnumre i rækkefølge


# --- 1. Data og modelresultater ---------------------------------------------------------
raa, panel, navne = appdata.indlaes()
seneste = panel["uge_start"].max()
iso = seneste.isocalendar()
res = appdata.backtest_resultater(panel)
o = appdata.model_opsummering(res)
valgt = o["valgt"]
skill_t, p_dm, daek = o["skill_test"][valgt], o["dm_test"][valgt], o["daekning_test"]
n_sig = int((p_dm < 0.05).sum())
test_fra = ev.TEST[0][:4]
mae_t, sk_t, dm = o["mae_test"], o["skill_test"], o["dm_test"]

# Forklaringer til info-boblerne – samme ordlyd i nøgletal og tabel
INFO_NAIV = ("The <b>naive forecast</b> simply assumes the coming weeks look like the latest week. It is the benchmark "
             "every model has to beat.")
INFO_SKILL = (f"<b>Skill</b> compares the model's errors with the naive forecast: 1 − MAE<sub>model</sub> ÷ "
              f"MAE<sub>naive</sub>. 27% means 27% smaller errors; below 0% the model is worse. {INFO_NAIV}")
# MAE sat i forhold til lusegrænsen, så 0,03 betyder noget for en læser uden for faget.
INFO_MAE = ("<b>Mean absolute error</b>: the average distance between forecast and actual lice level, in adult female "
            f"lice per fish. Lower is better. For scale: {mae_t.loc[4, valgt]:.3f} four weeks ahead is "
            f"{mae_t.loc[4, valgt] / 0.5:.0%} of the lice limit of 0.5.")
INFO_DM = ("The <b>Diebold–Mariano test</b> checks whether the gap in errors between the model and the naive forecast "
           "is bigger than chance would give. p < 0.05: less than a 5% chance of a gap this large if the two were "
           "equally good.")
INFO_INTERVAL = ("An <b>80% interval</b> should contain the actual lice level 8 times out of 10. More often: the "
                 "intervals are too wide; less often: too narrow. It is built from the model's own past errors.")

# --- 2. Områdevalg -------------------------------------------------------------------------
# Områdevalget fremhæves med en hjælpeboble og en pulserende kant, indtil brugeren selv har valgt et område.
# Har man valgt et område (eller et anlæg) på forsiden, åbner prognosen på det område – ellers PO 3.
fra_oversigt = st.session_state.get("po_valgt") if st.session_state.get("po_valgt") in navne else None
with st.container(key="omraadevalg"):
    if not st.session_state.get("omraade_skiftet") and fra_oversigt is None:
        st.markdown(
            f'<div class="valghjaelp" role="status"><b>{ikon("touch_app")} Pick a production area</b>'
            f'See the forecast for any of the {len(navne)} areas along the coast.</div>', unsafe_allow_html=True)
    valg = st.selectbox("Find your production area", options=sorted(navne), format_func=lambda x: f"PO {x} · {navne[x]}",
                        index=sorted(navne).index(fra_oversigt or 3), key="omraade",
                        on_change=lambda: st.session_state.update(omraade_skiftet=True))
live = appdata.live_prognose(panel, valgt, res)
lv = live[live["omraade"] == valg]
# Ét års historik, så prognosen (de sidste 4 uger) får plads – også på en smal mobilskærm.
omr = panel[(panel["omraade"] == valg) & (panel["uge_start"] >= seneste - pd.Timedelta(weeks=52))]
sidst = omr.dropna(subset=["hunlus"]).iloc[-1]
# Gennemsigtighed: hvor mange lokaliteter den seneste uge bygger på, mod en normal uge.
indb = appdata.indberetning(raa, panel)
indb_kort, indb_forklaring = appdata.indberetning_tekst(indb.loc[0, "n"], indb.loc[0, "normal"], iso.week)
indb_kort = "Built on " + indb_kort[0].lower() + indb_kort[1:]

# --- 3. Sidehoved og resumé ------------------------------------------------------------
# Toppen taler til alle: hvad sker der med lusetallet i området, hvor sikkert er det, og kan man stole på modellen?
uge_fra, uge_til = (u.isocalendar().week for u in lv["uge_start"].iloc[[0, -1]])
uge_nu = sidst["uge_start"].isocalendar().week
slut = lv.iloc[-1]
retning = "rise" if slut["pred"] > sidst["hunlus"] * 1.05 else "fall" if slut["pred"] < sidst["hunlus"] * 0.95 else "hold"
st.markdown(sidehoved(
    f"Forecast · weeks {uge_fra}–{uge_til} · Data up to week {iso.week}, {iso.year}",
    (f"Lice in {navne[valg]} are expected to {retning} to {tal(slut['pred'], 2)} by week {uge_til}" if retning != "hold"
     else f"Lice in {navne[valg]} are expected to hold at about {tal(slut['pred'], 2)} through week {uge_til}")
    + (f" – above the 0.5 lice limit" if slut["pred"] > 0.5 else ""),
    f"A 4-week forecast of adult female lice per fish for each of the {len(navne)} production areas, made by "
    f"{NAVNE[valgt].lower()} – the model that did best when tested on past seasons. Further down: how much each "
    "treatment type lowers lice, and how the model was tested.",
    [("live", appdata.opdatering_tekst(panel)), ("location_on", f"PO {valg} · {navne[valg]}"),
     ("database", indb_kort + info(indb_forklaring, "hoejre")),
     ("model_training", f"Model: {NAVNE[valgt]}"), ("straighten", "80% range")],
), unsafe_allow_html=True)
st.markdown(resume([
    (tal(slut["pred"], 2), f"expected adult female lice per fish in PO {valg} in week {uge_til}, "
                           f"from {tal(sidst['hunlus'], 2)} in week {uge_nu}.",
     f"The forecast for each of the next four weeks comes from its own model, trained on lice counts, sea temperature "
     f"and season since 2019. The area figure is the unweighted mean over its farms."),
    (f"{tal(slut['lo'], 2)}–{tal(slut['hi'], 2)}",
     f"likely range for week {uge_til}. In tests on past seasons, the actual level landed inside such a range "
     f"{daek.mean():.0%} of the time.", INFO_INTERVAL),
    (f"{abs(skill_t.loc[4]):.0%}", f"{'smaller' if skill_t.loc[4] >= 0 else 'larger'} errors 4 weeks ahead than simply "
                                   "assuming nothing changes – measured on data the model never saw.",
     f"{INFO_SKILL}<span class='regnestykke'>4 weeks: 1 − {mae_t.loc[4, valgt]:.4f} ÷ {mae_t.loc[4, 'naiv']:.4f} = "
     f"{pct(skill_t.loc[4])}</span>Test period {test_fra} onwards."),
]), unsafe_allow_html=True)

# --- 4. Figur: prognose for valgt område ------------------------------------------------
# Prognosen angives i kalenderuger: data ligger 1–2 uger bagud, så "om fire uger" ville være misvisende.
st.markdown(figur(
    next(nr), f"{navne[valg]}: {NAVNE[valgt].lower()} expects {tal(lv['pred'].iloc[-1], 2)} adult female lice per fish in week {uge_til} "
       f"({'rising' if lv['pred'].iloc[-1] > sidst['hunlus'] * 1.05 else 'falling' if lv['pred'].iloc[-1] < sidst['hunlus'] * 0.95 else 'stable'})",
    f"Adult female lice per fish, last 12 months and forecast for weeks {uge_fra}–{uge_til} (1–4 weeks after the latest "
    "complete week) with 80% interval. Dashed: naive forecast."
    + (f" No farm in the area reported lice counts for week {iso.week}; the latest count is from week {uge_nu}, and "
       "the forecast is built on the weeks before." if sidst["uge_start"] < seneste else ""),
), unsafe_allow_html=True)

forbind = pd.DataFrame([{"uge_start": sidst["uge_start"], "pred": sidst["hunlus"], "lo": sidst["hunlus"], "hi": sidst["hunlus"]}])
lv_plot = pd.concat([forbind, lv[["uge_start", "pred", "lo", "hi"]]], ignore_index=True)
naiv_plot = pd.DataFrame({"uge_start": lv_plot["uge_start"], "naiv": sidst["hunlus"]})
# Aksen går lidt forbi sidste prognoseuge, så prognosetallet kan stå lige til højre for punktet.
x_slut = lv["uge_start"].max() + pd.Timedelta(weeks=5)
x = alt.X("uge_start:T", title=None, scale=alt.Scale(domain=[omr["uge_start"].min().isoformat(), x_slut.isoformat()]),
          axis=alt.Axis(format="%b %Y", grid=False, tickCount=6, labelOverlap=True))
historik = alt.Chart(omr).mark_line(color=FARVER["blaek"], strokeWidth=1.6).encode(
    x=x, y=alt.Y("hunlus:Q", title="Adult female lice per fish"),
    tooltip=[alt.Tooltip("uge_start:T", title="Week", format="%d.%m.%Y"), alt.Tooltip("hunlus:Q", format=".3f")])
baand = alt.Chart(lv_plot).mark_area(color=FARVER["model"], opacity=.18, tooltip=None).encode(x=x, y="lo:Q", y2="hi:Q")
linje = alt.Chart(lv_plot).mark_line(color=FARVER["model"], strokeWidth=2.2, point=alt.OverlayMarkDef(size=36, color=FARVER["model"])).encode(
    x=x, y="pred:Q", tooltip=[alt.Tooltip("uge_start:T", title="Week"), alt.Tooltip("pred:Q", title="Forecast", format=".3f"),
                              alt.Tooltip("lo:Q", title="80% low", format=".3f"), alt.Tooltip("hi:Q", title="80% high", format=".3f")])
naiv_linje = alt.Chart(naiv_plot).mark_line(color=FARVER["skifer"], strokeDash=[4, 3], strokeWidth=1.2).encode(x=x, y="naiv:Q")
graense = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(color="#D64545", strokeDash=[3, 3], opacity=.7, tooltip=None).encode(y="y:Q")

# Annotationer direkte i grafen: seneste måling, prognosen om 4 uger og lusegrænsen.
uge_slut = uge_til


def note(uge_start, y, tekst, farve, dy):
    return alt.Chart(pd.DataFrame({"uge_start": [uge_start], "y": [y], "t": [tekst]})).mark_text(tooltip=None, 
        align="right", dx=-6, dy=dy, fontSize=11, fontWeight=600, color=farve).encode(x=x, y="y:Q", text="t:N")


# Seneste måling står over kurven; prognosetallet står lige til højre for sidste prognosepunkt.
top = max(sidst["hunlus"], lv["hi"].max())
annotation = (note(sidst["uge_start"], top, f"Week {uge_nu}: {tal(sidst['hunlus'], 2)}", FARVER["blaek"], -12)
              + alt.Chart(pd.DataFrame({"uge_start": [slut["uge_start"]], "y": [slut["pred"]], "t": [f"Week {uge_slut}: {tal(slut['pred'], 2)}"]}))
              .mark_text(tooltip=None, align="left", dx=8, fontSize=11, fontWeight=600, color=FARVER["model_tekst"]).encode(x=x, y="y:Q", text="t:N"))
graense_tekst = alt.Chart(pd.DataFrame({"uge_start": [omr["uge_start"].min()], "y": [0.5], "t": ["Lice limit 0.5"]})).mark_text(tooltip=None, 
    align="left", dx=2, dy=-6, fontSize=10, color="#D64545").encode(x=x, y="y:Q", text="t:N")
st.altair_chart((baand + historik + naiv_linje + linje + graense + graense_tekst + annotation).properties(height=340),
                width="stretch")
st.markdown(kilde("The interval is the empirical 10th–90th percentile of the model's own backtest errors for the area and horizon. "
                  "Red dashed line: the lice limit of 0.5. Each week ahead has its own model, so the path can bend – "
                  "for example when lice rebound after a treatment."), unsafe_allow_html=True)

# --- 5. Figur: behandlingernes effekt --------------------------------------------------
# Hændelsesstudie (se lakselus/behandlingseffekt.py): lusetallet uge for uge omkring en behandling, i procent af
# ugen før, mod en kontrolgruppe af ubehandlede lokaliteter med samme lusetal og samme årstid.
effekt = appdata.behandlingseffekt_tabel()
if effekt is not None and "omraade" not in effekt:  # ældre publicerede data uden opdeling pr. område
    effekt = effekt.assign(omraade=0)
if effekt is not None and len(effekt):
    # Hele kysten er grundlaget; det valgte område lægges ovenpå, hvor det selv har nok behandlinger.
    kyst = effekt[effekt["omraade"] == 0].drop(columns="omraade")
    omr = (effekt[effekt["omraade"] == valg][["type", "k", "median", "n"]]
           .rename(columns={"median": "omr_median", "n": "omr_n"}))
    eff = kyst.merge(omr, on=["type", "k"], how="left")
    omr_navn = navne[valg]

    # Effekt = hvor meget færre lus de behandlede har end sammenlignelige ubehandlede: 1 − behandlet / ubehandlet.
    netto = kyst.assign(netto=1 - kyst["median"] / kyst["kontrol"]).set_index(["type", "k"])["netto"]
    # "Other" er en blandet kategori – den vises sidst og bruges ikke i titlen.
    orden = sorted(netto.xs(0, level="k").sort_values(ascending=False).index, key=lambda t: t == "Other")
    bedst = orden[0]
    st.markdown(figur(
        next(nr), f"{bedst} treatment leaves {netto[(bedst, 0)]:.0%} fewer lice than at similar untreated farms within a "
           f"week – six weeks later the gap {'has shrunk to' if netto[(bedst, 6)] < netto[(bedst, 0)] else 'is'} "
           f"{netto[(bedst, 6)]:.0%}",
        "How lice numbers develop around a treatment, compared with similar farms that were not treated. "
        "100% = the farm's lice level in the week before treatment.",
    ), unsafe_allow_html=True)

    # Forklaring over grafen: hvad hver linje og flade betyder, med samme farver som i grafen.
    har_omr = eff["omr_median"].notna().any()
    st.markdown(
        '<div class="effektnoegle">'
        f'<span><i class="streg" style="border-color:{FARVER["model"]}"></i>Treated farms</span>'
        f'<span><i class="streg stiplet" style="border-color:{FARVER["skifer"]}"></i>Similar untreated farms</span>'
        f'<span><i class="flade" style="background:{FARVER["model"]}"></i>Effect of the treatment</span>'
        + (f'<span><i class="streg" style="border-color:{FARVER["blaek"]}"></i>Treated farms in {omr_navn}</span>'
           if har_omr else "")
        + "</div>", unsafe_allow_html=True)

    # Paneltitel i tre linjer: behandling og antal (og om området har nok behandlinger) – derefter effekten i ord.
    def faerre(v: float) -> str:
        return f"{v:.0%} fewer" if v >= 0 else f"{-v:.0%} more"

    omr_antal = eff.groupby("type")["omr_n"].max()

    def titel(t: str) -> str:
        omraade = ("" if not har_omr else f" · {omr_antal[t]:.0f} in PO {valg}" if pd.notna(omr_antal[t])
                   else f" · too few in PO {valg}")
        return (f"{t} · {eff.loc[eff['type'] == t, 'n'].iloc[0]} treatments{omraade}\n"
                f"Same week: {faerre(netto[(t, 0)])} lice\nAfter 6 weeks: {faerre(netto[(t, 6)])} lice")

    eff["titel"] = eff["type"].map(titel)
    titler = [titel(t) for t in orden]

    skala_y = alt.Scale(domain=[0, 1.5])
    ex = alt.X("k:Q", title="Weeks before / after treatment", scale=alt.Scale(domain=[-3, 6], nice=False),
               axis=alt.Axis(values=[-3, 0, 3, 6], grid=False, labelFontSize=10, titleFontSize=10, titleFontWeight=400,
                             labelExpr="datum.value == 0 ? 'Treatment' : (datum.value > 0 ? '+' : '') + datum.value"))
    ey = alt.Y("median:Q", title=None, scale=skala_y,
               axis=alt.Axis(values=[0, 0.5, 1, 1.5], format=".0%", labelFontSize=10))
    # Fladen mellem behandlede og ubehandlede er effekten; den starter i ugen før, hvor begge er 100 %.
    effekt_flade = alt.Chart().mark_area(color=FARVER["model"], opacity=.18, tooltip=None).encode(
        x=ex, y=alt.Y("median:Q", scale=skala_y), y2="kontrol:Q").transform_filter("datum.k >= -1")
    kontrol_linje = alt.Chart().mark_line(color=FARVER["skifer"], strokeDash=[5, 3], strokeWidth=1.6).encode(
        x=ex, y=alt.Y("kontrol:Q", scale=skala_y),
        tooltip=[alt.Tooltip("type:N", title="Treatment"), alt.Tooltip("k:Q", title="Week"),
                 alt.Tooltip("kontrol:Q", title="Similar untreated farms", format=".0%")])
    linje = alt.Chart().mark_line(color=FARVER["model"], strokeWidth=2.6,
                                  point=alt.OverlayMarkDef(size=18, color=FARVER["model"])).encode(
        x=ex, y=ey, tooltip=[alt.Tooltip("type:N", title="Treatment"), alt.Tooltip("k:Q", title="Week"),
                             alt.Tooltip("median:Q", title="Treated farms (median)", format=".0%"),
                             alt.Tooltip("kontrol:Q", title="Similar untreated farms", format=".0%"),
                             alt.Tooltip("q25:Q", title="Treated, 25th percentile", format=".0%"),
                             alt.Tooltip("q75:Q", title="Treated, 75th percentile", format=".0%")])
    omr_linje = alt.Chart().mark_line(color=FARVER["blaek"], strokeWidth=1.8, clip=True,
                                      point=alt.OverlayMarkDef(size=12, color=FARVER["blaek"])).encode(
        x=ex, y=alt.Y("omr_median:Q", scale=skala_y),
        tooltip=[alt.Tooltip("type:N", title="Treatment"), alt.Tooltip("k:Q", title="Week"),
                 alt.Tooltip("omr_median:Q", title=f"{omr_navn} (median)", format=".0%")],
    ).transform_filter("isValid(datum.omr_median)")
    hundrede = alt.Chart().mark_rule(color=FARVER["taage"], tooltip=None).encode(y=alt.datum(1))
    behandling = alt.Chart().mark_rule(color=FARVER["blaek"], strokeDash=[2, 2], opacity=.45, tooltip=None).encode(x=alt.datum(0))

    def effekt_multipler(kolonner: int, bredde: int, hoejde: int) -> alt.FacetChart:
        return alt.layer(hundrede, behandling, effekt_flade, kontrol_linje, linje, omr_linje, data=eff).properties(width=bredde, height=hoejde).facet(
            facet=alt.Facet("titel:N", sort=titler, header=alt.Header(
                labelExpr="split(datum.value, '\\n')", labelFontSize=11.5, labelFontWeight=600, labelPadding=8,
                labelLineHeight=17, labelColor=FARVER["blaek"])),
            columns=kolonner, spacing={"row": 28, "column": 22})

    # Tre kolonner på brede skærme, én på mobil – CSS i udseende.py viser den ene og skjuler den anden.
    with st.container(key="effekt_bred"):
        st.altair_chart(effekt_multipler(3, 280, 165), width="content")
    with st.container(key="effekt_mobil"):
        st.altair_chart(effekt_multipler(1, 285, 150), width="content")
    # Forklaringen af fôrbehandling står kun, når data viser mønsteret: lille straks-effekt, større efter 6 uger.
    foder = "In-feed (medicinal)"
    foder_tekst = ("In-feed treatment works slowly and mainly stops lice numbers from growing. "
                   if (foder, 0) in netto and netto[(foder, 0)] < 0.2 and netto[(foder, 6)] > netto[(foder, 0)] + 0.1
                   else "")
    st.markdown(kilde(
        f"Isolated treatments: one treatment type for the whole farm and no other treatment from 3 weeks before to "
        f"6 weeks after; the week before had at least 0.05 lice per fish. Types with fewer than 30 such treatments are "
        f"left out. Observational data: farms choose when and how to treat, so the comparison with untreated farms "
        f"removes the natural drop after a peak but cannot rule out every difference. {foder_tekst}Treated farms: "
        f"median of the farms; the middle half is shown on hover."), unsafe_allow_html=True)

# --- 6. Afsnit for fagfolk: hvor god er prognosen? ------------------------------------------
st.markdown(afsnit(
    "For the technically curious · How good is the forecast?",
    # Overskriften skal holde, uanset hvordan tallene ændrer sig: et interval kun, når alle horisonter er bedre.
    f"{NAVNE[valgt]} cuts forecast error by {skill_t.min():.0%}–{skill_t.max():.0%} versus the naive forecast "
    "in the test period" if (skill_t > 0).all() else
    f"{NAVNE[valgt]} cuts forecast error by up to {skill_t.max():.0%} versus the naive forecast in the test period"
    if skill_t.mean() > 0 else f"{NAVNE[valgt]} does not beat the naive forecast in the test period",
    f"{len(NAVNE)} models were backtested week by week using only the data available at the time. The model was "
    f"selected on 2023–24 and then measured once on {test_fra} onwards – data it was never tuned on.",
), unsafe_allow_html=True)

st.markdown(resume([
    (f"{abs(skill_t.loc[4]):.0%}", f"{'lower' if skill_t.loc[4] >= 0 else 'higher'} mean absolute error than the "
                                   f"naive forecast 4 weeks ahead in the test period ({pct(skill_t.loc[1])} skill at 1 week).",
     f"{INFO_SKILL}<span class='regnestykke'>4 weeks: 1 − {mae_t.loc[4, valgt]:.4f} ÷ {mae_t.loc[4, 'naiv']:.4f} = "
     f"{pct(skill_t.loc[4])}</span>Test period {test_fra} onwards – data the model was never tuned on."),
    (f"{n_sig} of 4", "horizons where the improvement is statistically significant (Diebold–Mariano, p < 0.05).",
     INFO_DM + " Tested separately for 1, 2, 3 and 4 weeks ahead."),
    (f"{daek.mean():.0%}", "of actual outcomes in the test period fell inside the 80% interval – "
                           + ("the intervals are well calibrated." if abs(daek.mean() - 0.8) <= 0.05 else
                              "the intervals are too narrow." if daek.mean() < 0.8 else "the intervals are too wide."),
     INFO_INTERVAL + " Within 5 points of 80% counts as well calibrated."),
]), unsafe_allow_html=True)

# --- 7. Figur: modelsammenligning -------------------------------------------------------
def figur2_titel(vindere: pd.Index, skill: pd.Series) -> str:
    """Titlen skal sige, hvilken model der faktisk er bedst i testperioden – også når det ikke er den valgte.

    skill: gennemsnitlig skill i testperioden pr. model. Under et halvt procentpoint fra den valgte er det uafgjort,
    for så kan forskellen ikke ses i tabellen.
    """
    bedst_test = skill.idxmax()
    if list(vindere) == [valgt]:
        return f"Only {NAVNE[valgt].lower()} beats the naive forecast at all four horizons"
    start = f"{len(vindere)} models beat the naive forecast at all horizons"
    if bedst_test == valgt:
        return f"{start}; {NAVNE[valgt].lower()} is best"
    if skill[bedst_test] - skill[valgt] < 0.005:
        return f"{start}; {NAVNE[valgt].lower()} and {NAVNE[bedst_test].lower()} are level in the test period"
    return (f"{start}; {NAVNE[bedst_test].lower()} is marginally ahead in the test period, but "
            f"{NAVNE[valgt].lower()} was chosen on validation")


st.markdown(figur(
    # En model "slår" den naive prognose, når forbedringen kan ses i tabellen (mindst +1 %) på alle fire horisonter.
    next(nr), figur2_titel(o["skill_test"].columns[(o["skill_test"] > 0.005).all()], o["skill_test"].mean().drop("naiv")),
    f"Mean absolute error (MAE) in female lice per fish in the test period ({test_fra}→), skill vs. naive and "
    "Diebold–Mariano p-value. The model was selected on the 2023–24 validation period.",
), unsafe_allow_html=True)

sk_v = o["skill_validering"]
raekker = []
for m in mae_t.columns:
    stil = ' class="valgt" style="font-weight:600"' if m == valgt else (' style="color:#6B7A86"' if m in BASELINES else "")
    # Parentesen i navnet ("same week last year") skjules på mobil, så navnet ikke fylder fire linjer.
    navn, _, parentes = NAVNE[m].partition(" (")
    navn += f'<span class="ekstra"> ({parentes}</span>' if parentes else ""
    celler = "".join(f'<td class="tal{" ekstra" if h in (2, 3) else ""}">{tal(mae_t.loc[h, m])}</td>' for h in (1, 2, 3, 4))
    sk = lambda h: "–" if m == "naiv" else pct(sk_t.loc[h, m])  # noqa: E731
    # En lav p-værdi for en model, der er dårligere end naiv, må ikke kunne læses som en gevinst.
    p4 = "–" if m == "naiv" else "worse" if sk_t.loc[4, m] < 0 else p_tekst(dm.loc[4, m])
    raekker.append(
        f'<tr{stil}><td class="navn">{navn}{" ★" if m == valgt else ""}</td>{celler}'
        f'<td class="tal ekstra">{sk(1)}</td><td class="tal">{sk(4)}</td><td class="tal">{p4}</td>'
        f'<td class="tal ekstra">{"–" if m == "naiv" else pct(sk_v.loc[:, m].mean())}</td></tr>'
    )
st.markdown(
    f'<table class="tabel modeller"><thead><tr><th>Model{info("The two naive forecasts (grey) are the benchmarks. The rest are trained models; ★ marks the one selected. " + INFO_NAIV)}</th>'
    f'<th class="tal">MAE 1 week{info(INFO_MAE, "hoejre")}</th><th class="tal ekstra">2 weeks</th>'
    f'<th class="tal ekstra">3 weeks</th><th class="tal">4 weeks</th><th class="tal ekstra">Skill 1 week</th>'
    f'<th class="tal">Skill 4 weeks{info(INFO_SKILL, "hoejre")}</th>'
    f'<th class="tal">DM p (4 weeks){info(INFO_DM + " <i>worse</i>: the model has larger errors than the naive forecast.", "hoejre")}</th>'
    f'<th class="tal ekstra">Skill validation{info(f"Skill in 2023–24, the period used to choose the model. The model with the highest mean skill here was selected (★) – before the test period from {test_fra} was looked at.", "hoejre")}</th>'
    '</tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde("Skill = 1 − MAE_model / MAE_naive. ★ = selected on validation (highest mean skill 2023–24). "
                  "The DM test uses Newey–West variance and the Harvey correction; "
                  "\"worse\" = higher error than the naive forecast."), unsafe_allow_html=True)

# --- 8. Figur: hvor hjælper modellen ----------------------------------------------------
pr_omr = o["mae_omraade_test"]
omr_skill = (1 - pr_omr[valgt] / pr_omr["naiv"]).groupby(level="omraade").mean().rename("skill").reset_index()
omr_skill["etiket"] = "PO " + omr_skill["omraade"].astype(str) + "  " + omr_skill["omraade"].map(navne)
omr_skill = omr_skill.sort_values("skill", ascending=False)
bedst, svagest = omr_skill.iloc[0], omr_skill.iloc[-1]
st.markdown(figur(
    next(nr), f"The gain is largest in {bedst['etiket'].split('  ')[1]} ({bedst['skill']:.0%}); "
       + (f"no measurable gain in {svagest['etiket'].split('  ')[1]}" if abs(svagest["skill"]) < 0.01
          else f"smallest in {svagest['etiket'].split('  ')[1]} ({pct(svagest['skill'])})"),
    f"Skill vs. naive forecast by production area, mean over 1–4 weeks, test period {test_fra}→.",
), unsafe_allow_html=True)
y = alt.Y("etiket:N", sort=list(omr_skill["etiket"]), title=None, axis=alt.Axis(labelLimit=240, labelColor="#1B2B36"))
bar = alt.Chart(omr_skill).mark_bar(height=14).encode(
    x=alt.X("skill:Q", title="Skill vs. naive", axis=alt.Axis(format="%")), y=y,
    color=alt.condition("datum.skill > 0", alt.value(FARVER["hav"]), alt.value("#D64545")),
    tooltip=[alt.Tooltip("etiket:N", title="Area"), alt.Tooltip("skill:Q", format=".1%")])
nul = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=FARVER["skifer"], tooltip=None).encode(x="x:Q")
st.altair_chart((bar + nul).properties(height=13 * 26), width="stretch")
smaa = panel.loc[panel["uge_start"] == seneste].query("n_lok < 10")["omraade"].astype(int).tolist()
st.markdown(kilde(f"Area{'s' if len(smaa) > 1 else ''} {' and '.join(map(str, smaa))} "
                  f"{'have' if len(smaa) > 1 else 'has'} fewer than 10 farms and {'are' if len(smaa) > 1 else 'is'} "
                  "noisier." if smaa else ""), unsafe_allow_html=True)

# --- 9. Figur: backtest-forløb ----------------------------------------------------------
# Titlen afhænger af horisonten, men skal stå over valget: en plads reserveres og fyldes, når valget kendes.
titel_plads = st.empty()
h_valg = st.segmented_control("Horizon", options=[1, 2, 3, 4], default=2, format_func=lambda h: f"{h} week{'s' if h > 1 else ''}",
                              key="horisont") or 2
bt = ev.intervaller(res[res["model"] == valgt].drop(columns="model"))
bt = ev.periode(bt[(bt["omraade"] == valg) & (bt["h"] == h_valg)], ev.TEST).sort_values("maal")
daek_omr = ((bt["faktisk"] >= bt["lo"]) & (bt["faktisk"] <= bt["hi"])).mean()
titel_plads.markdown(figur(
    next(nr), f"How the forecast would have performed in {navne[valg]} – {daek_omr:.0%} of outcomes fell inside the interval",
    f"Backtest in the test period: forecast made {h_valg} week{'s' if h_valg > 1 else ''} ahead (line and 80% interval) vs. the actual lice level (black).",
), unsafe_allow_html=True)
xb = alt.X("maal:T", title=None, axis=alt.Axis(format="%b %Y", grid=False))
st.altair_chart((
    alt.Chart(bt).mark_area(color=FARVER["model"], opacity=.15, tooltip=None).encode(x=xb, y=alt.Y("lo:Q", title="Adult female lice per fish"), y2="hi:Q")
    + alt.Chart(bt).mark_line(color=FARVER["model"], strokeWidth=1.6).encode(x=xb, y="pred:Q")
    + alt.Chart(bt).mark_line(color=FARVER["blaek"], strokeWidth=1.4).encode(
        x=xb, y="faktisk:Q", tooltip=[alt.Tooltip("maal:T", title="Week", format="%d.%m.%Y"),
                                      alt.Tooltip("faktisk:Q", title="Actual", format=".3f"), alt.Tooltip("pred:Q", title="Forecast", format=".3f")])
).properties(height=300), width="stretch")
st.markdown(kilde(), unsafe_allow_html=True)

# --- 9b. Figur: regnskabet ---------------------------------------------------------------------
# Backtesten er, hvad modellen ville have gjort. Regnskabet er, hvad siden faktisk viste: hver uges prognose gemmes
# (regnskab.py), og når ugen kommer, holdes den op mod det faktiske lusetal – uden mulighed for at rette bagefter.
arkiv = regnskab.laes()
if len(arkiv):
    vurderet = regnskab.vurder(arkiv, panel)
    rs = regnskab.opsummer(vurderet)
    foerste_uge = pd.Timestamp(arkiv["lavet"].min()).isocalendar().week
    if rs["n"]:
        titel = (f"Live track record: {rs['inde']} of {rs['n']} published forecasts landed inside the 80% range")
        bedre = rs["mae_naiv"] is not None and rs["mae"] < rs["mae_naiv"]
        vurdering = (f"Mean error so far is {rs['mae']:.3f} against {rs['mae_naiv']:.3f} for the naive forecast "
                     f"({'better' if bedre else 'worse'} than naive)" if rs["mae_naiv"] is not None else "")
        faa = rs["uger"] < 8
    else:
        titel, vurdering, faa = "Live track record: the first published forecasts are still waiting for their week", "", True
    st.markdown(figur(
        next(nr), titel,
        f"Every forecast this page has published since week {foerste_uge}, kept unchanged and compared with what "
        f"happened once the week's counts arrived. {navne[valg]}: actual level (black) and each published forecast "
        "with its 80% range (blue, older forecasts paler).",
    ), unsafe_allow_html=True)

    omr_a = arkiv[arkiv["omraade"] == valg].copy()
    omr_a["udgang"] = omr_a["lavet"].map(lambda d: f"Made week {pd.Timestamp(d).isocalendar().week}")
    alder = {l: i for i, l in enumerate(sorted(omr_a["lavet"].unique(), reverse=True))}
    omr_a["styrke"] = omr_a["lavet"].map(lambda l: max(1 - 0.28 * alder[l], 0.25))
    fra = pd.Timestamp(arkiv["lavet"].min()) - pd.Timedelta(weeks=6)
    faktisk = panel[(panel["omraade"] == valg) & (panel["uge_start"] >= fra)][["uge_start", "hunlus"]]
    # Etiketterne står på ugernes mandage (uge_start); D3's egne uge-ticks ligger på søndage og ville vise ugen før.
    mandage = pd.date_range(fra, max(omr_a["uge_start"].max(), faktisk["uge_start"].max()), freq="W-MON")
    xr = alt.X("uge_start:T", title=None, axis=alt.Axis(values=[d.strftime("%Y-%m-%dT00:00:00") for d in mandage],
                                                          labelExpr="'w' + timeFormat(datum.value, '%V')", grid=False))
    tip = [alt.Tooltip("udgang:N", title="Forecast"), alt.Tooltip("uge_start:T", title="For week", format="%d.%m.%Y"),
           alt.Tooltip("pred:Q", title="Forecast", format=".3f"), alt.Tooltip("lo:Q", title="80% range from", format=".3f"),
           alt.Tooltip("hi:Q", title="to", format=".3f")]
    st.altair_chart((
        alt.Chart(omr_a).mark_rule(color=FARVER["model"], strokeWidth=2).encode(
            x=xr, y=alt.Y("lo:Q", title="Adult female lice per fish"), y2="hi:Q", opacity=alt.Opacity("styrke:Q", legend=None, scale=None))
        + alt.Chart(omr_a).mark_line(color=FARVER["model"], strokeWidth=1.4, strokeDash=[4, 3]).encode(
            x=xr, y="pred:Q", detail="udgang:N", opacity=alt.Opacity("styrke:Q", legend=None, scale=None))
        + alt.Chart(omr_a).mark_point(color=FARVER["model"], filled=True, size=40).encode(
            x=xr, y="pred:Q", opacity=alt.Opacity("styrke:Q", legend=None, scale=None), tooltip=tip)
        + alt.Chart(faktisk).mark_line(color=FARVER["blaek"], strokeWidth=1.8, point=alt.OverlayMarkDef(size=22, color=FARVER["blaek"])).encode(
            x=xr, y="hunlus:Q", tooltip=[alt.Tooltip("uge_start:T", title="Week", format="%d.%m.%Y"),
                                         alt.Tooltip("hunlus:Q", title="Actual", format=".3f")])
    ).properties(height=280), width="stretch")
    forbehold = (" With so few weeks, this says little yet – the backtest above is the fair test until the record "
                 "has grown. It fills up by itself every Wednesday." if faa else "")
    st.markdown(kilde(f"All areas: {vurdering}.{forbehold} Forecasts are archived in "
                      "<code>data/app/prognose_arkiv.parquet</code> in the public repository."
                      if vurdering else forbehold.strip()), unsafe_allow_html=True)

# --- 10. Metode -------------------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Method.</b> The models predict the <i>change</i> in an area\'s lice level 1–4 weeks ahead '
    "(direct multi-horizon, one model per horizon), so the naive forecast is the starting point. Features: level and "
    "changes over 1–8 weeks, rolling mean and spread, sea temperature and its change, ISO week (sine/cosine), "
    "the area's typical seasonal change in other years, number of farms, and the coast-wide level and change. Gradient boosting is "
    "trained with an MAE loss, pooled across areas. Models are retrained every quarter in the backtest and only see "
    "data up to the forecast week – this is tested automatically by corrupting all future data and checking that "
    "the forecasts are unchanged.<br><br><b>Evaluation.</b> Model choice and settings were decided on 2023–24; the "
    f"figures above are from {test_fra} onwards, which was not used for any choice. The Diebold–Mariano test compares "
    "errors week by week against the naive forecast. Prediction intervals are causal empirical quantiles of the "
    "model's own past errors by area and horizon.<br><br><b>Lice treatments.</b> One candidate also uses the share of "
    "an area's farms treated against lice that week and over the past four weeks (mechanical, thermal, freshwater and "
    + ("medicinal). On 2023–24 it did not improve on gradient boosting without treatments: farms treat when lice "
       "counts are high, which the lice history already shows. It stays in the weekly backtest, so the comparison "
       "shows if that changes." if valgt != "gbm_beh" else
       "medicinal). On 2023–24 it had the lowest error of all models and is the selected model.")
    + "<br><br><b>Lice stages.</b> Another candidate also uses the younger lice stages the farms count: attached "
    "and mobile lice per fish, and the change in mobile lice over two weeks. These stages grow into adult females "
    "over the following weeks, so they are an early warning. "
    + ("On 2023–24 this candidate had the lowest error of all models and is the selected model. Sea temperature "
       "summed over 4–8 weeks, neighbouring areas and how far farms are into their production cycle were also tested "
       "and gave no reliable gain." if valgt == "gbm_stadier" else
       "It is in the weekly backtest alongside the other candidates.")
    + "<br><br><b>Fish stock.</b> A third candidate adds the area's fish stock from the Directorate of Fisheries' "
    "monthly statistics: number of fish, adult female lice per fish times the number of fish, mean fish weight, and "
    "the share of fish stocked and harvested over the past three months. Only months already published in the "
    "forecast week are used (the figures come out on the 20th of the following month). "
    + ("On 2023–24 it did not improve on gradient boosting with lice stages (average skill 18.0% vs 18.7%, no "
       "significant difference): the figures are monthly and several weeks old, and the lice history already "
       "reflects much of what they say. It stays in the weekly backtest." if valgt != "gbm_biomasse" else
       "On 2023–24 it had the lowest error of all models and is the selected model.")
    + "<br><br><b>Caveats.</b> The forecasts are statistical estimates, not advice, and come with no guarantee; "
    "do not use them as the sole basis for operational or regulatory decisions. Treatments explain some of the "
    "abrupt drops but cannot be known ahead of time. Data are retrieved as they look today; late corrections were not necessarily known in the "
    "forecast week.</div>",
    unsafe_allow_html=True,
)
