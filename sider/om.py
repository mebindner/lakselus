"""About & methods: data, modeller, evaluering, forbehold og ændringslog – samlet ét sted (engelsk UI).

Siden er til den besøgende, der vil vide, om tallene kan bruges: hvor data kommer fra, hvordan de er bearbejdet,
hvordan prognosen er bygget og testet, hvad analysen ikke kan sige, og hvad der er ændret undervejs.
Nøgletal fra evalueringen beregnes fra den publicerede backtest, så teksten følger data uge for uge.

Indhold
0. Hjælpefunktioner
1. Data og nøgletal      – lokaliteter, periode og modelresultater fra backtesten
2. Sidehoved
3. Data                  – kilde, bearbejdning, indberetningsforsinkelse, lusegrænse og trafiklys
4. Prognosemodellen      – idé, kandidater, disciplin i modelvalget og resultater på test
5. Behandlingseffekt     – hændelsesstudie med matchet kontrolgruppe
6. Begrænsninger
7. Ændringslog           – ændringer, der påvirker tal eller metode (ikke rent tekniske ændringer)
"""

import streamlit as st

from lakselus import appdata, evaluering as ev
from lakselus.modelrapport import BASELINES, NAVNE
from lakselus.udseende import afsnit, info, kilde, sidehoved


# --- 0. Hjælpefunktioner ---------------------------------------------------------------

def pct(v: float) -> str:
    return f"{v:+.0%}".replace("-", "−")


def p_tekst(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def tekst(html: str) -> None:
    st.markdown(f'<div class="om-tekst">{html}</div>', unsafe_allow_html=True)


# Siden er mest tekst; lidt luft og en læsbar linjelængde. Tabellerne bruger appens fælles .tabel-stil.
st.markdown(
    "<style>.om-tekst { margin-top: 1.2rem; max-width: 46em; font-size: .95rem; line-height: 1.6; color: #1B2B36; }"
    ".om-tekst p { margin: 0 0 .8rem; } .om-tekst ul { margin: 0 0 .8rem 1.1rem; padding: 0; }"
    ".om-tekst li { margin-bottom: .35rem; } .om-tekst h3 { font-size: 1rem !important; margin: 1.4rem 0 .4rem; padding: 0; }"
    "table.tabel.log td.dato { white-space: nowrap; color: #4A5A66; font-variant-numeric: tabular-nums; width: 7.5em; }"
    "table.tabel.ideer td.navn { white-space: nowrap; }</style>",
    unsafe_allow_html=True,
)

# --- 1. Data og nøgletal ----------------------------------------------------------------
raa, panel, navne = appdata.indlaes()
n_lok = raa.loc[raa["har_talt"] == "Ja", "lokalitet"].nunique()
fra_aar = panel["uge_start"].min().isocalendar().year  # ISO-år: uge 1 2019 begynder mandag 31.12.2018
seneste = panel["uge_start"].max().isocalendar()
res = appdata.backtest_resultater(panel)
o = appdata.model_opsummering(res)
valgt = o["valgt"]
mae_t, sk_t, sk_v, dm, daek = o["mae_test"], o["skill_test"], o["skill_validering"], o["dm_test"], o["daekning_test"]
test_fra = ev.TEST[0][:4]
val_fra, val_til = ev.VALIDERING[0][:4], ev.VALIDERING[1][:4]
n_test_uger = ev.periode(res[res["model"] == valgt], ev.TEST)["origin"].nunique()

# --- 2. Sidehoved -----------------------------------------------------------------------
st.markdown(sidehoved(
    "About · data, methods and changes",
    "How the figures are made, and how far to trust them",
    "Where the data come from, how they are processed, how the forecast is built and tested, what the analysis "
    "cannot tell you, and what has changed along the way. Figures on this page are computed from the same "
    "backtest the Forecast page uses, so they update every week.",
    [("live", appdata.opdatering_tekst(panel)), ("database", f"{n_lok:,} farms · {fra_aar}→"),
     ("model_training", f"Selected model: {NAVNE[valgt]}")],
), unsafe_allow_html=True)

# --- 3. Data ----------------------------------------------------------------------------
st.markdown(afsnit("1 · Data", "Weekly lice counts from every Norwegian salmon farm",
                   "Open government data, processed as little as possible and in the same way every week."),
            unsafe_allow_html=True)
tekst(
    "<p><b>Source.</b> Every marine salmon and trout farm in Norway must count sea lice and report weekly to the "
    "Norwegian Food Safety Authority (Mattilsynet). BarentsWatch publishes the reports per farm: adult female lice, "
    "mobile and attached lice per fish, sea temperature and lice treatments, plus the production-area boundaries and "
    f"the government traffic lights. The app uses all {n_lok:,} farms (farm sites, <i>lokaliteter</i>) that have reported counts since {fra_aar}, "
    "under the Norwegian Licence for Open Government Data (NLOD).</p>"
    "<p><b>Processing.</b></p><ul>"
    "<li><b>Area figures are unweighted means</b> over the farms that counted lice that week. The number of fish "
    "per farm is not in the open data, so a small farm weighs as much as a large one. The figures describe the "
    "typical farm in an area, not the total number of lice in the water.</li>"
    "<li><b>Only counted weeks are used.</b> Weeks where a farm reports no count (fallow farms, or low "
    "temperatures, when counting is required less often) are left out rather than set to zero.</li>"
    "<li><b>The latest week waits for complete reporting.</b> Farms report a week's counts during the following "
    "week. A week is included once the number of farms that have counted reaches 80% of the median of the eight "
    "weeks before, so the app usually trails the calendar by 1–2 weeks.</li>"
    "<li><b>Areas with fewer than 10 farms</b> are shown but flagged and are not used for headline conclusions, as a "
    "single farm can move the mean a lot.</li></ul>"
    "<p><b>Lice limit and traffic light.</b> The lice limit is 0.5 adult female lice per fish, and 0.2 during the "
    "spring weeks, when wild salmon smolts migrate out to sea. The traffic light (<i>trafikklyssystemet</i>) is set "
    "for each of the 13 production areas every second year, from estimated lice-related mortality in wild salmon. "
    "An area can therefore be red although its farms are below the lice limit. The app shows the colour in force in "
    "the week displayed.</p>"
    "<p><b>Ocean currents.</b> The Currents page shows the daily mean surface current for the same week as the lice "
    "counts, from MET Norway's NorKyst v3 ocean model (800 m grid, CC BY 4.0). It is shown on a grid of about 3 km, "
    "so narrow fjords are smoothed. The particles show how the water moved; they are not a model of lice larvae.</p>"
    "<p><b>Update.</b> A scheduled job runs early every Wednesday morning (with two backup attempts). It fetches new "
    "counts, treatments and ocean currents, re-runs the whole backtest, runs the test suite as a quality gate and only then "
    "publishes the data.</p>"
)

# --- 4. Prognosemodellen ----------------------------------------------------------------
st.markdown(afsnit("2 · Forecast", "A forecast that has to beat “nothing changes”",
                   "Several models are tested the same way, and one is chosen before the test results are seen."),
            unsafe_allow_html=True)
tekst(
    "<p><b>What is forecast.</b> The mean number of adult female lice per fish in each production area, one to four "
    "weeks after the latest complete week. Each horizon has its own model, which predicts the <i>change</i> from "
    "today's level. The simplest possible forecast, that next week looks like this week, is the starting point. "
    "The models only have to learn when and by how much the level moves.</p>"
    "<p><b>The candidates.</b> Two naive benchmarks and six models are run side by side:</p>"
)
VALGT = ' class="valgt"'
IDEER = {
    "naiv": "Next week looks like the latest week. The benchmark every model has to beat.",
    "saeson_naiv": "The level in the same week last year.",
    "saeson_justeret": "Latest level plus the area's typical change at this time of year in other years.",
    "ridge": "Linear regression on the change, one model per horizon.",
    "gbm": "Gradient boosting (non-linear), trained on all areas together with an absolute-error loss.",
    "gbm_beh": "As gradient boosting, plus the share of the area's farms treated against lice in recent weeks.",
    "gbm_stadier": "As gradient boosting, plus the younger lice stages (attached and mobile lice), which become adult "
                   "females over the following weeks.",
    "ensemble": "Mean of the seasonal model, ridge and gradient boosting.",
}
st.markdown(
    '<table class="tabel ideer"><thead><tr><th>Model</th><th>Idea</th></tr></thead><tbody>'
    + "".join(f'<tr{VALGT if m == valgt else ""}><td class="navn">{NAVNE[m]}{" ★" if m == valgt else ""}</td>'
              f"<td>{IDEER.get(m, '')}</td></tr>" for m in NAVNE if m in mae_t.columns)
    + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde("★ = the selected model. Inputs for the learning models: level and changes over 1–8 weeks, rolling "
                  "mean and spread, sea temperature, time of year, the area's seasonal profile, number of farms and "
                  "the coast-wide level and change."), unsafe_allow_html=True)

tekst(
    "<h3>How the models are tested</h3><ul>"
    "<li><b>Only the past.</b> Every forecast in the test is made week by week with only the data that existed at "
    "the time (an expanding window, retrained every quarter). A test in the code corrupts all future data and "
    "checks that the forecasts do not change.</li>"
    "<li><b>No peeking at the answer.</b> The seasonal profile a training row sees is computed from <i>other</i> "
    "years only, so it never contains its own outcome.</li>"
    f"<li><b>Choice and test are kept apart.</b> Models and settings are chosen on {val_fra}–{val_til} (validation). "
    f"The results below are from {test_fra} onwards (test), a period that was not used for any choice. The model with "
    "the highest mean skill on validation is selected, so a model that only happens to do well on the test period "
    "does not get picked.</li>"
    "<li><b>Against a benchmark, with a significance test.</b> Errors are measured as mean absolute error (MAE) and "
    "compared with the naive forecast as skill = 1 − MAE<sub>model</sub> ÷ MAE<sub>naive</sub>. The Diebold–Mariano "
    "test (Newey–West variance, Harvey correction) checks whether the difference is larger than chance.</li>"
    "<li><b>Honest uncertainty.</b> The 80% range is the 10th–90th percentile of the model's own past errors for the "
    "area and horizon, using only errors that were known at the time of the forecast. If it is well calibrated, the "
    "outcome lands inside it 8 times out of 10.</li></ul>"
    f"<h3>Results in the test period ({test_fra} onwards, {n_test_uger} forecast weeks)</h3>"
)
h = (1, 2, 3, 4)
raekker = [
    ("MAE, naive forecast", [f"{mae_t.loc[i, 'naiv']:.3f}" for i in h], ""),
    (f"MAE, {NAVNE[valgt].lower()}", [f"<b>{mae_t.loc[i, valgt]:.3f}</b>" for i in h], ""),
    ("Skill vs. naive", [pct(sk_t.loc[i, valgt]) for i in h],
     "Share of the naive forecast's error the model removes. 0% = no better than assuming nothing changes."),
    ("Diebold–Mariano p", [p_tekst(dm.loc[i, valgt]) for i in h],
     "Below 0.05: the gain over the naive forecast is unlikely to be chance."),
    ("Inside 80% range", [f"{daek.loc[i]:.0%}" for i in h], "Should be close to 80%."),
]
st.markdown(
    '<table class="tabel"><thead><tr><th></th>'
    + "".join(f'<th class="tal">{i} week{"s" if i > 1 else ""}</th>' for i in h) + "</tr></thead><tbody>"
    + "".join(f'<tr><td class="navn">{n}{info(f, "venstre") if f else ""}</td>'
              + "".join(f'<td class="tal">{v}</td>' for v in vs) + "</tr>" for n, vs, f in raekker)
    + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde("MAE in adult female lice per fish. The figures move slightly from week to week as new weeks and "
                  "late corrections arrive. The full comparison of all models is on the Forecast page."),
            unsafe_allow_html=True)

andre = [m for m in sk_v.columns if m not in BASELINES and m != valgt]
# Fejlen sat i forhold til noget, man kender: lusegrænsen og det typiske niveau i testperioden.
niveau = ev.periode(panel.rename(columns={"uge_start": "origin"}), ev.TEST)["hunlus"].mean()
mae4 = mae_t.loc[4, valgt]
tekst(
    f"<p><b>What the error means.</b> Four weeks ahead the forecast is off by {mae4:.3f} adult female lice per fish "
    f"on average. That is {mae4 / 0.5:.0%} of the lice limit of 0.5, and {mae4 / niveau:.0%} of the typical area "
    f"level in the test period ({niveau:.2f} lice per fish).</p>"
    "<p><b>Reading the results.</b> One week ahead the naive forecast is hard to beat: lice levels change slowly. The "
    "gain grows with the horizon, because the model picks up the seasonal rhythm and momentum that matter more "
    f"further out. On validation, {NAVNE[valgt].lower()} had a mean skill of {sk_v[valgt].mean():.1%}, against "
    f"{max(sk_v[m].mean() for m in andre):.1%} for the best of the other candidates.</p>"
    "<p><b>What was tried and not kept.</b> Lice treatments as an input did not improve the forecast on validation. "
    "Farms treat when lice counts are already high, and the model already sees the lice history. Sea temperature "
    "summed over 4–8 weeks (degree-days), neighbouring areas' lice levels and how far farms are into their production "
    "cycle were tested the same way and gave no reliable gain. Rejected candidates that still run in the weekly "
    "backtest are shown on the Forecast page, so it is visible if that changes.</p>"
)

# --- 5. Behandlingseffekt ---------------------------------------------------------------
st.markdown(afsnit("3 · Treatments", "How much a treatment lowers lice, compared with similar farms",
                   "An event study with a matched comparison group, not a controlled trial."),
            unsafe_allow_html=True)
tekst(
    "<p>The Forecast page shows how lice counts develop in the weeks around a treatment, by treatment type. Only "
    "<b>isolated, whole-farm treatments</b> are used: one treatment type for the whole farm, and no other treatment "
    "from three weeks before to six weeks after, so the effects of several treatments are not mixed.</p>"
    "<p>Farms treat when lice counts are high, and high counts often fall somewhat on their own. The treated farms "
    "are therefore compared with <b>untreated farm-weeks weighted to have the same lice level the week before and the "
    "same month</b>. The effect is the gap between the two, as a median.</p>"
    "<p>This removes the most obvious bias, but not all of it: farms that treat may differ from farms that do not in "
    "ways the data do not show. Read the figures as well-founded estimates, not as the result of a trial.</p>"
)

# --- 6. Begrænsninger -------------------------------------------------------------------
st.markdown(afsnit("4 · Limitations", "What the figures cannot tell you",
                   "Worth knowing before you use a number from the app."), unsafe_allow_html=True)
tekst(
    "<ul>"
    "<li><b>Not weighted by fish.</b> Area figures describe the typical farm, not the total lice pressure.</li>"
    "<li><b>Self-reported counts.</b> The data are the farms' own counts as reported to the authorities. The app does "
    "not correct or audit them.</li>"
    "<li><b>Data as they look today.</b> Late corrections are included in the history, so the backtest may have known "
    "a slightly more accurate value than a forecaster would have had in that week.</li>"
    "<li><b>Treatments cannot be foreseen.</b> A treatment can make the lice level fall sharply in a week the forecast "
    "did not expect. This is the main source of large errors.</li>"
    "<li><b>Areas, not farms.</b> The forecast is for production areas. The farm view on Latest week shows history "
    "and neighbours, but no farm-level forecast.</li>"
    "<li><b>Not advice.</b> The figures and forecasts are statistical estimates with no guarantee. Do not use them as "
    "the sole basis for operational or regulatory decisions.</li></ul>"
)

# --- 7. Ændringslog ---------------------------------------------------------------------
# Kun ændringer, der påvirker tal, metode eller hvad siderne viser – ikke design og drift.
# Tallene er fra commit-beskeden på den pågældende dag og kan afvige lidt fra dagens tal ovenfor.
st.markdown(afsnit("5 · Changelog", "Changes to data, methods and models",
                   "Changes to the data, methods and pages. Design-only and technical changes are left out; the full history "
                   "is on GitHub."), unsafe_allow_html=True)
LOG = [
    ("2026-11-06", "<b>Currents map follows your choice.</b> A farm or area chosen on Latest week (or in the link, "
                   "<code>?site=</code> / <code>?po=</code>) makes the currents map fly there and mark it, with the farm's lice "
                   "count and how far the water moved. No figure changes."),
    ("2026-11-06", "<b>Life cycle of the salmon louse on the Currents page.</b> An illustration from drifting larva to "
                   "adult female, with this week's average of each counted stage, the sea temperature and how far the "
                   "water moved. Explanatory only; no figure or model changes."),
    ("2026-11-05", "<b>History rebuilt around one question: is this year worse than usual?</b> One line per year with "
                   "this year highlighted, the usual peak weeks shaded and a headline computed from the data. The 3D "
                   "column map became a flat dot map, where farms can be compared directly."),
    ("2026-11-05", "<b>Currents page added.</b> An animated map of the daily mean surface current from MET Norway's "
                   "NorKyst v3 ocean model for the week of the lice counts, with the farms coloured by lice level. It "
                   "shows how the water moves, not where lice larvae end up, and does not change any other figure."),
    ("2026-11-05", "<b>Younger lice stages added; new selected model.</b> Gradient boosting with attached and mobile "
                   "lice had the best skill on validation and replaced gradient boosting without them. In the test "
                   "period, skill one week ahead rose from 8% to 12% and four weeks ahead from 27% to 29%."),
    ("2026-11-04", "<b>Reporting made visible.</b> Pages show how many farms reported in the latest week compared with "
                   "a normal week. Areas without counts in that week stay visible instead of disappearing."),
    ("2026-10-31", "<b>Lice treatments added.</b> Treatment data from BarentsWatch, a forecast candidate that uses "
                   "them (not selected: no gain on validation), and the treatment-effect event study."),
    ("2026-10-28", "<b>Correction: seasonal leak fixed.</b> The seasonal input could include a training row's own "
                   "outcome. It is now computed from other years only. The correction <i>raised</i> test skill from "
                   "5–23% to 8–27%, and the gain became significant at every horizon."),
    ("2026-10-26", "<b>First version.</b> Weekly panel by production area from 2019, naive benchmarks, ridge, "
                   f"gradient boosting and ensemble, chosen on {val_fra}–{val_til} and tested from {test_fra}. "
                   "Automatic weekly update."),
]
st.markdown(
    '<table class="tabel log"><thead><tr><th>Date</th><th>Change</th></tr></thead><tbody>'
    + "".join(f'<tr><td class="dato">{d}</td><td>{t}</td></tr>' for d, t in LOG)
    + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="kilde">Figures in the changelog are as reported on the day of the change. Code, tests and full '
    'history: <a href="https://github.com/mebindner/lakselus" target="_blank">github.com/mebindner/lakselus</a>.</div>',
    unsafe_allow_html=True,
)
