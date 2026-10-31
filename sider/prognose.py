"""Prognose: modelvalg, prognose med usikkerhed og ærlig evaluering i konsulentformat.

Indhold
0. Hjælpefunktioner
1. Data og modelresultater  – backtest, valgt model, skill og Diebold–Mariano-test
2. Sidehoved og resumé
3. Figur 1: prognose for det valgte område (med 80 %-interval)
4. Figur 2: modelsammenligning
5. Figur 3: hvor hjælper modellen
6. Figur 4: backtest-forløb
7. Figur 5: behandlingernes effekt (hændelsesstudie med kontrolgruppe)
8. Metode
"""

import altair as alt
import pandas as pd
import streamlit as st

from lakselus import appdata, evaluering as ev
from lakselus.modelrapport import BASELINES, NAVNE
from lakselus.udseende import FARVER, figur, ikon, kilde, resume, sidehoved


# --- 0. Hjælpefunktioner ---------------------------------------------------------------

def tal(v: float, d: int = 3) -> str:
    return f"{v:.{d}f}"


def pct(v: float) -> str:
    return f"{v:+.0%}".replace("-", "−")


def p_tekst(p: float) -> str:
    return "< 0.001" if p < 0.001 else tal(p, 3)


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

# --- 2. Sidehoved og resumé ------------------------------------------------------------
st.markdown(sidehoved(
    f"Forecast · weeks {(seneste + pd.Timedelta(weeks=1)).isocalendar().week}–"
    f"{(seneste + pd.Timedelta(weeks=4)).isocalendar().week} · Data up to week {iso.week}, {iso.year}",
    f"{NAVNE[valgt]} cuts forecast error by {abs(skill_t.loc[1]):.0%}–{abs(skill_t.loc[4]):.0%} "
    f"versus the naive forecast in the test period" if skill_t.mean() > 0 else
    f"{NAVNE[valgt]} does not beat the naive forecast in the test period",
    f"{len(NAVNE)} models were backtested week by week using only the data available at the time. The model was selected on "
    f"2023–24 and then measured once on {test_fra} onwards – data it was never tuned on.",
    [("live", appdata.opdatering_tekst(panel)), ("model_training", f"Selected model: {NAVNE[valgt]}"), ("science", "Diebold–Mariano test"),
     ("straighten", "80% prediction interval")],
), unsafe_allow_html=True)

st.markdown(resume([
    (f"{skill_t.loc[4]:.0%}", f"lower mean absolute error than the naive forecast 4 weeks ahead in the test period "
                              f"({skill_t.loc[1]:.0%} at 1 week)."),
    (f"{n_sig} of 4", "horizons where the improvement is statistically significant (Diebold–Mariano, p < 0.05)."),
    (f"{daek.mean():.0%}", "of actual outcomes in the test period fell inside the 80% interval – "
                           "the intervals are well calibrated."),
]), unsafe_allow_html=True)

# --- 3. Figur 1: prognose for valgt område ------------------------------------------------
# Områdevalget fremhæves med en hjælpeboble og en pulserende kant, indtil brugeren selv har valgt et område.
with st.container(key="omraadevalg"):
    if not st.session_state.get("omraade_skiftet"):
        st.markdown(
            f'<div class="valghjaelp" role="status"><b>{ikon("touch_app")} Pick a production area</b>'
            f'See the forecast for any of the {len(navne)} areas along the coast.</div>', unsafe_allow_html=True)
    valg = st.selectbox("Production area", options=sorted(navne), format_func=lambda x: f"{x} · {navne[x]}",
                        index=sorted(navne).index(3), key="omraade",
                        on_change=lambda: st.session_state.update(omraade_skiftet=True))
live = appdata.live_prognose(panel, valgt, res)
lv = live[live["omraade"] == valg]
# Ét års historik, så prognosen (de sidste 4 uger) får plads – også på en smal mobilskærm.
omr = panel[(panel["omraade"] == valg) & (panel["uge_start"] >= seneste - pd.Timedelta(weeks=52))]
sidst = omr.dropna(subset=["hunlus"]).iloc[-1]

# Prognosen angives i kalenderuger: data ligger 1–2 uger bagud, så "om fire uger" ville være misvisende.
uge_fra, uge_til = (u.isocalendar().week for u in lv["uge_start"].iloc[[0, -1]])
st.markdown(figur(
    1, f"{navne[valg]}: {NAVNE[valgt].lower()} expects {tal(lv['pred'].iloc[-1], 2)} adult female lice per fish in week {uge_til} "
       f"({'rising' if lv['pred'].iloc[-1] > sidst['hunlus'] * 1.05 else 'falling' if lv['pred'].iloc[-1] < sidst['hunlus'] * 0.95 else 'stable'})",
    f"Adult female lice per fish, last 12 months and forecast for weeks {uge_fra}–{uge_til} (1–4 weeks after the latest "
    "complete week) with 80% interval. Dashed: naive forecast.",
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
baand = alt.Chart(lv_plot).mark_area(color=FARVER["laks"], opacity=.18).encode(x=x, y="lo:Q", y2="hi:Q")
linje = alt.Chart(lv_plot).mark_line(color=FARVER["laks"], strokeWidth=2.2, point=alt.OverlayMarkDef(size=36, color=FARVER["laks"])).encode(
    x=x, y="pred:Q", tooltip=[alt.Tooltip("uge_start:T", title="Week"), alt.Tooltip("pred:Q", title="Forecast", format=".3f"),
                              alt.Tooltip("lo:Q", title="80% low", format=".3f"), alt.Tooltip("hi:Q", title="80% high", format=".3f")])
naiv_linje = alt.Chart(naiv_plot).mark_line(color=FARVER["skifer"], strokeDash=[4, 3], strokeWidth=1.2).encode(x=x, y="naiv:Q")
graense = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(color="#D64545", strokeDash=[3, 3], opacity=.7).encode(y="y:Q")

# Annotationer direkte i grafen: seneste måling, prognosen om 4 uger og lusegrænsen.
slut = lv.iloc[-1]
uge_nu, uge_slut = sidst["uge_start"].isocalendar().week, slut["uge_start"].isocalendar().week


def note(uge_start, y, tekst, farve, dy):
    return alt.Chart(pd.DataFrame({"uge_start": [uge_start], "y": [y], "t": [tekst]})).mark_text(
        align="right", dx=-6, dy=dy, fontSize=11, fontWeight=600, color=farve).encode(x=x, y="y:Q", text="t:N")


# Seneste måling står over kurven; prognosetallet står lige til højre for sidste prognosepunkt.
top = max(sidst["hunlus"], lv["hi"].max())
annotation = (note(sidst["uge_start"], top, f"Week {uge_nu}: {tal(sidst['hunlus'], 2)}", FARVER["blaek"], -12)
              + alt.Chart(pd.DataFrame({"uge_start": [slut["uge_start"]], "y": [slut["pred"]], "t": [f"Week {uge_slut}: {tal(slut['pred'], 2)}"]}))
              .mark_text(align="left", dx=8, fontSize=11, fontWeight=600, color=FARVER["laks_tekst"]).encode(x=x, y="y:Q", text="t:N"))
graense_tekst = alt.Chart(pd.DataFrame({"uge_start": [omr["uge_start"].min()], "y": [0.5], "t": ["Lice limit 0.5"]})).mark_text(
    align="left", dx=2, dy=-6, fontSize=10, color="#D64545").encode(x=x, y="y:Q", text="t:N")
st.altair_chart((baand + historik + naiv_linje + linje + graense + graense_tekst + annotation).properties(height=340),
                width="stretch")
st.markdown(kilde("The interval is the empirical 10th–90th percentile of the model's own backtest errors for the area and horizon. "
                  "Red dashed line: the lice limit of 0.5. Each week ahead has its own model, so the path can bend – "
                  "for example when lice rebound after a treatment."), unsafe_allow_html=True)

# --- 4. Figur 2: modelsammenligning -------------------------------------------------------
st.markdown(figur(
    2, (lambda vindere: f"Only {NAVNE[valgt].lower()} beats the naive forecast at all four horizons"
        if list(vindere) == [valgt] else
        f"{len(vindere)} models beat the naive forecast at all horizons; {NAVNE[valgt].lower()} is best")(
        o["skill_test"].columns[(o["skill_test"] > 0).all()]),
    f"Mean absolute error (MAE) in female lice per fish in the test period ({test_fra}→), skill vs. naive and "
    "Diebold–Mariano p-value. The model was selected on the 2023–24 validation period.",
), unsafe_allow_html=True)

mae_t, sk_t, dm = o["mae_test"], o["skill_test"], o["dm_test"]
sk_v = o["skill_validering"]
raekker = []
for m in mae_t.columns:
    stil = ' style="font-weight:600;background:#FFF4F0"' if m == valgt else (' style="color:#6B7A86"' if m in BASELINES else "")
    celler = "".join(f'<td class="tal{" ekstra" if h in (2, 3) else ""}">{tal(mae_t.loc[h, m])}</td>' for h in (1, 2, 3, 4))
    sk = lambda h: "–" if m == "naiv" else pct(sk_t.loc[h, m])  # noqa: E731
    # En lav p-værdi for en model, der er dårligere end naiv, må ikke kunne læses som en gevinst.
    p4 = "–" if m == "naiv" else "worse" if sk_t.loc[4, m] < 0 else p_tekst(dm.loc[4, m])
    raekker.append(
        f'<tr{stil}><td class="navn">{NAVNE[m]}{" ★" if m == valgt else ""}</td>{celler}'
        f'<td class="tal ekstra">{sk(1)}</td><td class="tal">{sk(4)}</td><td class="tal">{p4}</td>'
        f'<td class="tal ekstra">{"–" if m == "naiv" else pct(sk_v.loc[:, m].mean())}</td></tr>'
    )
st.markdown(
    '<table class="tabel"><thead><tr><th>Model</th><th class="tal">MAE 1 week</th><th class="tal ekstra">2 weeks</th>'
    '<th class="tal ekstra">3 weeks</th><th class="tal">4 weeks</th><th class="tal ekstra">Skill 1 week</th><th class="tal">Skill 4 weeks</th>'
    '<th class="tal">DM p (4 weeks)</th><th class="tal ekstra">Skill validation</th></tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde("Skill = 1 − MAE_model / MAE_naive. ★ = selected on validation (highest mean skill 2023–24). "
                  "The DM test uses Newey–West variance and the Harvey correction; "
                  "\"worse\" = higher error than the naive forecast."), unsafe_allow_html=True)

# --- 5. Figur 3: hvor hjælper modellen ----------------------------------------------------
pr_omr = o["mae_omraade_test"]
omr_skill = (1 - pr_omr[valgt] / pr_omr["naiv"]).groupby(level="omraade").mean().rename("skill").reset_index()
omr_skill["etiket"] = "PO " + omr_skill["omraade"].astype(str) + "  " + omr_skill["omraade"].map(navne)
omr_skill = omr_skill.sort_values("skill", ascending=False)
bedst, svagest = omr_skill.iloc[0], omr_skill.iloc[-1]
st.markdown(figur(
    3, f"The gain is largest in {bedst['etiket'].split('  ')[1]} ({bedst['skill']:.0%}); "
       + (f"no measurable gain in {svagest['etiket'].split('  ')[1]}" if abs(svagest["skill"]) < 0.01
          else f"smallest in {svagest['etiket'].split('  ')[1]} ({pct(svagest['skill'])})"),
    f"Skill vs. naive forecast by production area, mean over 1–4 weeks, test period {test_fra}→.",
), unsafe_allow_html=True)
y = alt.Y("etiket:N", sort=list(omr_skill["etiket"]), title=None, axis=alt.Axis(labelLimit=240, labelColor="#1B2B36"))
bar = alt.Chart(omr_skill).mark_bar(height=14).encode(
    x=alt.X("skill:Q", title="Skill vs. naive", axis=alt.Axis(format="%")), y=y,
    color=alt.condition("datum.skill > 0", alt.value(FARVER["hav"]), alt.value("#D64545")),
    tooltip=[alt.Tooltip("etiket:N", title="Area"), alt.Tooltip("skill:Q", format=".1%")])
nul = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=FARVER["skifer"]).encode(x="x:Q")
st.altair_chart((bar + nul).properties(height=13 * 26), width="stretch")
st.markdown(kilde("Areas 1 and 13 have fewer than 10 sites and are noisier."), unsafe_allow_html=True)

# --- 6. Figur 4: backtest-forløb ----------------------------------------------------------
h_valg = st.segmented_control("Horizon", options=[1, 2, 3, 4], default=2, format_func=lambda h: f"{h} week{'s' if h > 1 else ''}",
                              key="horisont") or 2
bt = ev.intervaller(res[res["model"] == valgt].drop(columns="model"))
bt = ev.periode(bt[(bt["omraade"] == valg) & (bt["h"] == h_valg)], ev.TEST).sort_values("maal")
daek_omr = ((bt["faktisk"] >= bt["lo"]) & (bt["faktisk"] <= bt["hi"])).mean()
st.markdown(figur(
    4, f"How the forecast would have performed in {navne[valg]} – {daek_omr:.0%} of outcomes fell inside the interval",
    f"Backtest in the test period: forecast made {h_valg} week{'s' if h_valg > 1 else ''} ahead (line and 80% interval) vs. the actual lice level (black).",
), unsafe_allow_html=True)
xb = alt.X("maal:T", title=None, axis=alt.Axis(format="%b %Y", grid=False))
st.altair_chart((
    alt.Chart(bt).mark_area(color=FARVER["laks"], opacity=.15).encode(x=xb, y=alt.Y("lo:Q", title="Adult female lice per fish"), y2="hi:Q")
    + alt.Chart(bt).mark_line(color=FARVER["laks"], strokeWidth=1.6).encode(x=xb, y="pred:Q")
    + alt.Chart(bt).mark_line(color=FARVER["blaek"], strokeWidth=1.4).encode(
        x=xb, y="faktisk:Q", tooltip=[alt.Tooltip("maal:T", title="Week", format="%d.%m.%Y"),
                                      alt.Tooltip("faktisk:Q", title="Actual", format=".3f"), alt.Tooltip("pred:Q", title="Forecast", format=".3f")])
).properties(height=300), width="stretch")
st.markdown(kilde(), unsafe_allow_html=True)

# --- 7. Figur 5: behandlingernes effekt --------------------------------------------------
# Hændelsesstudie (se lakselus/behandlingseffekt.py): lusetallet uge for uge omkring en behandling, i procent af
# ugen før, mod en kontrolgruppe af ubehandlede lokaliteter med samme lusetal og samme årstid.
effekt = appdata.behandlingseffekt_tabel()
if effekt is not None and len(effekt):
    # Nettoeffekt = hvor meget lavere de behandlede ligger end kontrollen; bruges til titel og rækkefølge.
    netto = effekt.assign(netto=1 - effekt["median"] / effekt["kontrol"]).set_index(["type", "k"])["netto"]
    # "Other" er en blandet kategori – den vises sidst og bruges ikke i titlen.
    orden = sorted(netto.xs(0, level="k").sort_values(ascending=False).index, key=lambda t: t == "Other")
    bedst = orden[0]
    st.markdown(figur(
        5, f"{bedst} treatment removes {netto[(bedst, 0)]:.0%} of lice in the treatment week – six weeks later the "
           f"level is still {netto[(bedst, 6)]:.0%} below comparable untreated sites",
        "Adult female lice per fish, relative to the week before treatment (= 100%). Line: median of single, "
        "whole-site treatments; band: middle half of the sites. Dashed: untreated sites with the same lice level "
        "in the same month.",
    ), unsafe_allow_html=True)

    eff = effekt.assign(titel=lambda d: d["type"] + " · " + d["n"].astype(str) + " treatments")
    titler = [eff.loc[eff["type"] == t, "titel"].iloc[0] for t in orden]
    ex = alt.X("k:Q", title=None, scale=alt.Scale(domain=[-3, 6], nice=False),
               axis=alt.Axis(values=list(range(-3, 7)), labelExpr="datum.value == 0 ? 'Treat.' : (datum.value > 0 ? '+' : '') + datum.value",
                             grid=False, labelFontSize=9))
    ey = alt.Y("median:Q", title=None, scale=alt.Scale(domain=[0, 1.5]),
               axis=alt.Axis(values=[0, 0.5, 1, 1.5], format=".0%", labelFontSize=9))
    baand = alt.Chart().mark_area(color=FARVER["laks"], opacity=.15, clip=True).encode(
        x=ex, y=alt.Y("q25:Q", title=None, scale=alt.Scale(domain=[0, 1.5])), y2="q75:Q")
    kontrol_linje = alt.Chart().mark_line(color=FARVER["skifer"], strokeDash=[4, 3], strokeWidth=1.3).encode(
        x=ex, y="kontrol:Q")
    linje = alt.Chart().mark_line(color=FARVER["laks"], strokeWidth=2.2, point=alt.OverlayMarkDef(size=14)).encode(
        x=ex, y=ey, tooltip=[alt.Tooltip("type:N", title="Treatment"), alt.Tooltip("k:Q", title="Week"),
                             alt.Tooltip("median:Q", title="Treated (median)", format=".0%"),
                             alt.Tooltip("kontrol:Q", title="Untreated", format=".0%")])
    # Tallet i behandlingsugen står til højre for punktet (fri af den lodrette linje), tallet efter 6 uger over det.
    tal_0 = alt.Chart().mark_text(align="left", dx=6, dy=2, fontSize=10, fontWeight=600, color=FARVER["laks_tekst"]).encode(
        x=ex, y=ey, text=alt.Text("median:Q", format=".0%")).transform_filter("datum.k == 0")
    tal_6 = alt.Chart().mark_text(align="right", dy=-9, fontSize=10, fontWeight=600, color=FARVER["laks_tekst"]).encode(
        x=ex, y=ey, text=alt.Text("median:Q", format=".0%")).transform_filter("datum.k == 6")
    hundrede = alt.Chart().mark_rule(color=FARVER["taage"]).encode(y=alt.datum(1))
    behandling = alt.Chart().mark_rule(color=FARVER["blaek"], strokeDash=[2, 2], opacity=.5).encode(x=alt.datum(0))

    def effekt_multipler(kolonner: int, bredde: int, hoejde: int) -> alt.FacetChart:
        return alt.layer(hundrede, behandling, baand, kontrol_linje, linje, tal_0, tal_6, data=eff).properties(
            width=bredde, height=hoejde).facet(
            facet=alt.Facet("titel:N", sort=titler, header=alt.Header(labelFontSize=11, labelPadding=4)),
            columns=kolonner)

    # Tre kolonner på brede skærme, én på mobil – CSS i udseende.py viser den ene og skjuler den anden.
    with st.container(key="effekt_bred"):
        st.altair_chart(effekt_multipler(3, 225, 130), width="content")
    with st.container(key="effekt_mobil"):
        st.altair_chart(effekt_multipler(1, 285, 120), width="content")
    st.markdown(kilde(
        f"Isolated treatments: one treatment type for the whole site and no other treatment from 3 weeks before to "
        f"6 weeks after; the week before had at least 0.05 lice per fish. Types with fewer than 30 such treatments are "
        f"left out. Observational data: sites choose when and how to treat, so the comparison with untreated sites "
        f"removes the natural drop after a peak but cannot rule out every difference. In-feed treatment works "
        f"slowly and mainly stops lice numbers from growing."), unsafe_allow_html=True)

# --- 8. Metode -------------------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Method.</b> The models predict the <i>change</i> in an area\'s lice level 1–4 weeks ahead '
    "(direct multi-horizon, one model per horizon), so the naive forecast is the starting point. Features: level and "
    "changes over 1–8 weeks, rolling mean and spread, sea temperature and its change, ISO week (sine/cosine), "
    "the area's typical seasonal change in other years, number of sites, and the coast-wide level and change. Gradient boosting is "
    "trained with an MAE loss, pooled across areas. Models are retrained every quarter in the backtest and only see "
    "data up to the forecast week – this is tested automatically by corrupting all future data and checking that "
    "the forecasts are unchanged.<br><br><b>Evaluation.</b> Model choice and settings were decided on 2023–24; the "
    f"figures above are from {test_fra} onwards, which was not used for any choice. The Diebold–Mariano test compares "
    "errors week by week against the naive forecast. Prediction intervals are causal empirical quantiles of the "
    "model's own past errors by area and horizon.<br><br><b>Lice treatments.</b> One candidate also uses the share of "
    "an area's sites treated against lice that week and over the past four weeks (mechanical, thermal, freshwater and "
    "medicinal). On 2023–24 it did not improve on gradient boosting without treatments: farms treat when lice counts "
    "are high, which the lice history already shows. It stays in the weekly backtest, so the model choice would pick "
    "it up if that changes.<br><br><b>Caveats.</b> Treatments explain some of the abrupt drops but cannot be known "
    "ahead of time. Data are retrieved as they look today; late corrections were not necessarily known in the "
    "forecast week.</div>",
    unsafe_allow_html=True,
)
