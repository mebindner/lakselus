"""Prognose: modelvalg, prognose med usikkerhed og ærlig evaluering i konsulentformat."""

import altair as alt
import pandas as pd
import streamlit as st

from lakselus import appdata, evaluering as ev
from lakselus.modelrapport import BASELINES, NAVNE
from lakselus.udseende import FARVER, figur, kilde, resume, sidehoved


def tal(v: float, d: int = 3) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def pct(v: float) -> str:
    return f"{v:+.0%}".replace("-", "−")


def p_tekst(p: float) -> str:
    return "< 0,001" if p < 0.001 else tal(p, 3)


raa, panel, navne = appdata.indlaes()
seneste = panel["uge_start"].max()
iso = seneste.isocalendar()
res = appdata.backtest_resultater(panel)
o = appdata.model_opsummering(res)
valgt = o["valgt"]
skill_t, p_dm, daek = o["skill_test"][valgt], o["dm_test"][valgt], o["daekning_test"]
n_sig = int((p_dm < 0.05).sum())
test_fra = ev.TEST[0][:4]

st.markdown(sidehoved(
    f"Prognose · 1–4 uger · Data til og med uge {iso.week}, {iso.year}",
    f"{NAVNE[valgt]} giver {abs(skill_t.loc[1]):.0%}–{abs(skill_t.loc[4]):.0%} "
    f"{'lavere' if skill_t.mean() > 0 else 'højere'} fejl end den naive prognose i testperioden",
    "Seks modeller er backtestet uge for uge med kun de data, der fandtes på tidspunktet. Modellen er valgt på "
    f"2023–24 og derefter målt én gang på {test_fra} og frem – data, den aldrig har været tilpasset til.",
    [("model_training", f"Valgt model: {NAVNE[valgt]}"), ("science", "Diebold–Mariano-test"),
     ("straighten", "80 %-prognoseinterval")],
), unsafe_allow_html=True)

st.markdown(resume([
    (f"{skill_t.loc[4]:.0%}", f"lavere gennemsnitlig fejl end den naive prognose 4 uger frem i testperioden "
                              f"({skill_t.loc[1]:.0%} på 1 uge)."),
    (f"{n_sig} af 4", "horisonter, hvor forbedringen er statistisk signifikant (Diebold–Mariano, p < 0,05)."),
    (f"{daek.mean():.0%}", "af de faktiske udfald i testperioden lå inden for 80 %-intervallet – "
                           "intervallerne er altså ærligt kalibrerede."),
]), unsafe_allow_html=True)

# --- Figur 1: prognose for valgt område ------------------------------------------------
valg = st.selectbox("Produktionsområde", options=sorted(navne), format_func=lambda x: f"{x} · {navne[x]}",
                    index=sorted(navne).index(3), key="omraade")
live = appdata.live_prognose(panel, valgt, res)
lv = live[live["omraade"] == valg]
omr = panel[(panel["omraade"] == valg) & (panel["uge_start"] >= seneste - pd.Timedelta(weeks=104))]
sidst = omr.dropna(subset=["hunlus"]).iloc[-1]

st.markdown(figur(
    1, f"{navne[valg]}: {NAVNE[valgt].lower()} forventer {tal(lv['pred'].iloc[-1], 2)} hunlus pr. fisk om fire uger "
       f"({'stigende' if lv['pred'].iloc[-1] > sidst['hunlus'] * 1.05 else 'faldende' if lv['pred'].iloc[-1] < sidst['hunlus'] * 0.95 else 'stabilt'})",
    "Voksne hunlus pr. fisk, seneste to år og prognose 1–4 uger frem med 80 %-interval. Stiplet: naiv prognose.",
), unsafe_allow_html=True)

forbind = pd.DataFrame([{"uge_start": sidst["uge_start"], "pred": sidst["hunlus"], "lo": sidst["hunlus"], "hi": sidst["hunlus"]}])
lv_plot = pd.concat([forbind, lv[["uge_start", "pred", "lo", "hi"]]], ignore_index=True)
naiv_plot = pd.DataFrame({"uge_start": lv_plot["uge_start"], "naiv": sidst["hunlus"]})
x = alt.X("uge_start:T", title=None, axis=alt.Axis(format="%b %Y", grid=False))
historik = alt.Chart(omr).mark_line(color=FARVER["blaek"], strokeWidth=1.6).encode(
    x=x, y=alt.Y("hunlus:Q", title="Voksne hunlus pr. fisk"),
    tooltip=[alt.Tooltip("uge_start:T", title="Uge", format="%d.%m.%Y"), alt.Tooltip("hunlus:Q", format=".3f")])
baand = alt.Chart(lv_plot).mark_area(color=FARVER["laks"], opacity=.18).encode(x=x, y="lo:Q", y2="hi:Q")
linje = alt.Chart(lv_plot).mark_line(color=FARVER["laks"], strokeWidth=2.2, point=alt.OverlayMarkDef(size=36, color=FARVER["laks"])).encode(
    x=x, y="pred:Q", tooltip=[alt.Tooltip("uge_start:T", title="Uge"), alt.Tooltip("pred:Q", title="Prognose", format=".3f"),
                              alt.Tooltip("lo:Q", title="80 % fra", format=".3f"), alt.Tooltip("hi:Q", title="80 % til", format=".3f")])
naiv_linje = alt.Chart(naiv_plot).mark_line(color=FARVER["skifer"], strokeDash=[4, 3], strokeWidth=1.2).encode(x=x, y="naiv:Q")
graense = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(color="#D64545", strokeDash=[3, 3], opacity=.7).encode(y="y:Q")
st.altair_chart((baand + historik + naiv_linje + linje + graense).properties(height=340), width="stretch")
st.markdown(kilde("Intervallet er de empiriske 10.–90. percentiler af modellens egne backtest-fejl for området og horisonten. "
                  "Rød stiplet linje: lusegrænsen 0,5."), unsafe_allow_html=True)

# --- Figur 2: modelsammenligning -------------------------------------------------------
st.markdown(figur(
    2, (lambda vindere: f"Kun {NAVNE[valgt].lower()} slår den naive prognose på alle fire horisonter"
        if list(vindere) == [valgt] else
        f"{len(vindere)} modeller slår den naive prognose på alle horisonter; {NAVNE[valgt].lower()} er bedst")(
        o["skill_test"].columns[(o["skill_test"] > 0).all()]),
    f"Gennemsnitlig absolut fejl (MAE) i hunlus pr. fisk i testperioden ({test_fra}→), skill mod naiv og "
    "Diebold–Mariano p-værdi. Modellen er valgt på valideringsperioden 2023–24.",
), unsafe_allow_html=True)

mae_t, sk_t, dm = o["mae_test"], o["skill_test"], o["dm_test"]
sk_v = o["skill_validering"]
raekker = []
for m in mae_t.columns:
    stil = ' style="font-weight:600;background:#FFF4F0"' if m == valgt else (' style="color:#6B7A86"' if m in BASELINES else "")
    celler = "".join(f'<td class="tal">{tal(mae_t.loc[h, m])}</td>' for h in (1, 2, 3, 4))
    sk = lambda h: "–" if m == "naiv" else pct(sk_t.loc[h, m])  # noqa: E731
    p4 = "–" if m == "naiv" else p_tekst(dm.loc[4, m])
    raekker.append(
        f'<tr{stil}><td class="navn">{NAVNE[m]}{" ★" if m == valgt else ""}</td>{celler}'
        f'<td class="tal">{sk(1)}</td><td class="tal">{sk(4)}</td><td class="tal">{p4}</td>'
        f'<td class="tal">{"–" if m == "naiv" else pct(sk_v.loc[:, m].mean())}</td></tr>'
    )
st.markdown(
    '<table class="tabel"><thead><tr><th>Model</th><th class="tal">MAE 1 uge</th><th class="tal">2 uger</th>'
    '<th class="tal">3 uger</th><th class="tal">4 uger</th><th class="tal">Skill 1 uge</th><th class="tal">Skill 4 uger</th>'
    '<th class="tal">DM p (4 uger)</th><th class="tal">Skill validering</th></tr></thead><tbody>'
    + "".join(raekker) + "</tbody></table>",
    unsafe_allow_html=True,
)
st.markdown(kilde("Skill = 1 − MAE_model / MAE_naiv. ★ = valgt på validering (højeste gennemsnitlige skill 2023–24). "
                  "DM-testen bruger Newey–West-varians og Harvey-korrektion."), unsafe_allow_html=True)

# --- Figur 3: hvor hjælper modellen ----------------------------------------------------
pr_omr = o["mae_omraade_test"]
omr_skill = (1 - pr_omr[valgt] / pr_omr["naiv"]).groupby(level="omraade").mean().rename("skill").reset_index()
omr_skill["etiket"] = "PO " + omr_skill["omraade"].astype(str) + "  " + omr_skill["omraade"].map(navne)
omr_skill = omr_skill.sort_values("skill", ascending=False)
bedst, svagest = omr_skill.iloc[0], omr_skill.iloc[-1]
st.markdown(figur(
    3, f"Gevinsten er størst i {bedst['etiket'].split('  ')[1]} ({bedst['skill']:.0%}); "
       + (f"ingen målbar gevinst i {svagest['etiket'].split('  ')[1]}" if abs(svagest["skill"]) < 0.01
          else f"mindst i {svagest['etiket'].split('  ')[1]} ({pct(svagest['skill'])})"),
    f"Skill mod naiv prognose pr. produktionsområde, gennemsnit over 1–4 uger, testperioden {test_fra}→.",
), unsafe_allow_html=True)
y = alt.Y("etiket:N", sort=list(omr_skill["etiket"]), title=None, axis=alt.Axis(labelLimit=240, labelColor="#1B2B36"))
bar = alt.Chart(omr_skill).mark_bar(height=14).encode(
    x=alt.X("skill:Q", title="Skill mod naiv", axis=alt.Axis(format="%")), y=y,
    color=alt.condition("datum.skill > 0", alt.value(FARVER["hav"]), alt.value("#D64545")),
    tooltip=[alt.Tooltip("etiket:N", title="Område"), alt.Tooltip("skill:Q", format=".1%")])
nul = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=FARVER["skifer"]).encode(x="x:Q")
st.altair_chart((bar + nul).properties(height=13 * 26), width="stretch")
st.markdown(kilde("Område 1 og 13 har under 10 lokaliteter og er mere støjfyldte."), unsafe_allow_html=True)

# --- Figur 4: backtest-forløb ----------------------------------------------------------
h_valg = st.segmented_control("Horisont", options=[1, 2, 3, 4], default=2, format_func=lambda h: f"{h} uge{'r' if h > 1 else ''}",
                              key="horisont") or 2
bt = ev.intervaller(res[res["model"] == valgt].drop(columns="model"))
bt = ev.periode(bt[(bt["omraade"] == valg) & (bt["h"] == h_valg)], ev.TEST).sort_values("maal")
daek_omr = ((bt["faktisk"] >= bt["lo"]) & (bt["faktisk"] <= bt["hi"])).mean()
st.markdown(figur(
    4, f"Sådan ville prognosen have set ud i {navne[valg]} – {daek_omr:.0%} af udfaldene lå inden for intervallet",
    f"Backtest i testperioden: prognose lavet {h_valg} uge{'r' if h_valg > 1 else ''} før (linje og 80 %-interval) mod det faktiske lusetal (sort).",
), unsafe_allow_html=True)
xb = alt.X("maal:T", title=None, axis=alt.Axis(format="%b %Y", grid=False))
st.altair_chart((
    alt.Chart(bt).mark_area(color=FARVER["laks"], opacity=.15).encode(x=xb, y=alt.Y("lo:Q", title="Voksne hunlus pr. fisk"), y2="hi:Q")
    + alt.Chart(bt).mark_line(color=FARVER["laks"], strokeWidth=1.6).encode(x=xb, y="pred:Q")
    + alt.Chart(bt).mark_line(color=FARVER["blaek"], strokeWidth=1.4).encode(
        x=xb, y="faktisk:Q", tooltip=[alt.Tooltip("maal:T", title="Uge", format="%d.%m.%Y"),
                                      alt.Tooltip("faktisk:Q", format=".3f"), alt.Tooltip("pred:Q", title="Prognose", format=".3f")])
).properties(height=300), width="stretch")
st.markdown(kilde(), unsafe_allow_html=True)

# --- Metode -------------------------------------------------------------------------------
st.markdown(
    '<div class="metode"><b>Metode.</b> Modellerne forudsiger <i>ændringen</i> i områdets lusetal 1–4 uger frem '
    "(direkte multi-horisont, én model pr. horisont), så den naive prognose er udgangspunktet. Features: niveau og "
    "ændringer over 1–8 uger, glidende gennemsnit og spredning, havtemperatur og dens ændring, ISO-uge (sinus/cosinus), "
    "områdets typiske sæsonændring, antal lokaliteter og hele kystens niveau og ændring. Gradient boosting trænes med "
    "MAE-tab, fælles for alle områder. Modellerne gen-trænes hvert kvartal i backtesten og ser kun data til og med "
    "forecast-ugen – det er testet automatisk ved at ødelægge alle fremtidige data og kontrollere, at prognoserne er "
    "uændrede.<br><br><b>Evaluering.</b> Modelvalg og indstillinger er besluttet på 2023–24; tallene ovenfor er fra "
    f"{test_fra} og frem, som ikke er brugt til noget valg. Diebold–Mariano-testen sammenligner fejl uge for uge mod "
    "den naive prognose. Prognoseintervallerne er kausale empiriske kvantiler af modellens egne tidligere fejl pr. "
    "område og horisont.<br><br><b>Forbehold.</b> Lusebehandlinger er ikke med som forklarende variabel og forklarer "
    "en del af de bratte fald. Data hentes som de ser ud i dag; sene rettelser var ikke nødvendigvis kendt i "
    "forecast-ugen.</div>",
    unsafe_allow_html=True,
)
