"""Designsystem i konsulentstil.

Hvid flade, dyb havblå tekst og én dæmpet tanggrøn accent (nøglen hedder stadig "laks").
Hver farve har ét job: navy og grå bærer struktur og hoveddataserien, tanggrøn betyder "du kan klikke her",
teal/rav/rød er forbeholdt lusetal, og trafiklyset vises altid med tekst eller som kant – aldrig som flade.
Serif-handlingstitler (konklusionen står i titlen), nummererede figurer med enhed og kildeangivelse,
minimalistiske tabeller og små multipler.

Indhold
1. Farver og skrifttyper
2. CSS               – al styling af appen samlet ét sted, opdelt efter komponent
3. HTML-byggeklodser – sidehoved, resumé, figurtitel, kildeangivelse, nøgletalskort, info-bobler
3b. Minigrafer       – små SVG-grafer til nøgletallene: kurve, andelsbjælke, prikker og strimmel
4. Lusetal i tekst   – niveau og trend til tabeller og forklaringer
5. Altair-tema       – fælles grafstil
"""

import altair as alt
import pandas as pd

# --- 1. Farver og skrifttyper ---------------------------------------------------------------

FARVER = {
    "blaek": "#0B2230",      # dyb havblå – titler, primære dataserier
    "hav": "#1D4E6B",        # sekundær blå
    "skifer": "#5B6B78",     # brødtekst, akser
    "taage": "#AEBBC5",      # sekundære dataserier, bånd
    "linje": "#E1E6EA",      # kanter og gitter
    "flade": "#FFFFFF",
    "baggrund": "#FFFFFF",
    "laks": "#6F7D3C",       # accent (tang/mos) – kun til det, man kan klikke på: links, knapper, søgefelt, valg
    "laks_tekst": "#55602B", # samme accent, mørkere til tekst: kontrast ≥ 4,5:1 mod hvid (WCAG AA)
    "serie": "#0B2230",      # hoveddataserien: i år, det valgte anlæg, de faktiske lusetal
    "model": "#5B92BA",      # modellens tal (prognose, behandlede anlæg) – lys fjordblå, så den skilles fra navy
    "model_tekst": "#3E6A86",# samme blå, mørkere til tekst (kontrast ≥ 4,5:1 mod hvid)
    "rav": "#E2A23B",
    # Bagudkompatible navne brugt i graferne
    "fjord": "#1D4E6B",
    "lyng": "#5B6B78",
}

LYS_FARVER = {  # trafiklys: kant, baggrund, tekst
    "green": ("#2E8B57", "#E5F3EB", "#1D5C39"),
    "yellow": ("#D9A21B", "#FBF2DA", "#7A5A08"),
    "red": ("#C8403A", "#FBE4E2", "#8A231F"),
}
LUS_FARVER = {"lav": "#1F7A8C", "mellem": "#E2A23B", "hoej": "#D64545"}  # < 0,2 · 0,2–0,5 · > 0,5
SEKVENS = ["#F3F6F8", "#C9D8E2", "#7FA2BA", "#2F5D7C", "#0B2230"]  # én-farvet blå skala til heatmaps

SERIF = "'Source Serif 4', Georgia, serif"
SANS = "Inter, 'Helvetica Neue', Arial, sans-serif"

# --- 2. CSS ---------------------------------------------------------------------------------

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

html, body, [class*="css"], .stMarkdown, p, li, td, th, label, button, input { font-family: Inter, sans-serif; }
.stMarkdown p, .stMarkdown li { color: #2A3A46; }
h1, h2, h3 { font-family: 'Source Serif 4', Georgia, serif !important; font-weight: 600 !important; color: #0B2230; letter-spacing: -0.01em; }
.block-container { padding-top: 4.4rem; max-width: 1160px; }
/* Topbjælke: mørk blå med en svag dybde, ordmærket til venstre og siderne som bløde "piller" med ikon.
   Den aktive side står i en lys pille med et tanggrønt ikon; hover lysner pillen let. */
header[data-testid="stHeader"] { background: linear-gradient(180deg, #0E2A3B 0%, #0B2230 100%); height: 3.75rem;
  border-bottom: 2px solid #6F7D3C; box-shadow: 0 6px 18px rgba(11,34,48,.18); }
header[data-testid="stHeader"] button, header[data-testid="stHeader"] [data-testid="stIconMaterial"] { color: #FFFFFF; }
[data-testid="stHeaderLogo"], [data-testid="stLogo"] { height: 32px; margin-right: 1.4rem; }
[data-testid="stTopNav"] { gap: .25rem; }
[data-testid="stTopNavLink"] { position: relative; color: #B9C6D0 !important; background: transparent !important;
  border-radius: 999px; padding: .38rem .9rem !important; font-weight: 500; letter-spacing: .01em;
  transition: color .15s, background-color .15s; }
[data-testid="stTopNavLink"] span, [data-testid="stTopNavLink"] div, [data-testid="stTopNavLink"] p { color: inherit !important; }
[data-testid="stTopNavLink"] p { font-size: .9rem; }
[data-testid="stTopNavLink"]:hover { color: #FFFFFF !important; background: rgba(255,255,255,.07) !important; }
[data-testid="stTopNavLink"][aria-current="page"] { color: #FFFFFF !important; font-weight: 600;
  background: rgba(255,255,255,.12) !important; box-shadow: inset 0 0 0 1px rgba(255,255,255,.10); }
header[data-testid="stHeader"] [data-testid="stTopNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {
  color: #B7C47E !important; }
[data-testid="stTopNavLink"]:focus-visible { outline: 2px solid #A3B26A; outline-offset: 2px; }
/* På mobil foldes siderne sammen bag en knap – giv den en tydelig "Pages"-etiket */
[data-testid="stExpandSidebarButton"] { width: auto !important; gap: .35rem; padding: 0 .7rem !important;
  border: 1px solid rgba(255,255,255,.35) !important; border-radius: 6px; color: #FFFFFF !important; }
[data-testid="stExpandSidebarButton"]::after { content: "Pages"; font: 600 .85rem Inter, sans-serif; color: #FFFFFF; }
[data-testid="stCaptionContainer"] { color: #6B7A86; }
hr { border-color: #E1E6EA; }

.ikon { font-family: 'Material Symbols Outlined'; font-weight: normal; font-style: normal; line-height: 1;
        display: inline-block; vertical-align: -0.2em; font-size: 1.15em; -webkit-font-smoothing: antialiased; }

/* Forside / sidehoved */
/* Ingen linje under sidehovedet: nøgletallenes navy linje er afsnittets eneste skillelinje */
.sidehoved { padding: .6rem 0 .6rem; margin-bottom: 1.4rem; }
.sidehoved .overlinje { font-size: .72rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; color: #5B6B78; }
.sidehoved h1 { font-size: clamp(1.7rem, 3.4vw, 2.5rem) !important; line-height: 1.15; margin: .5rem 0 .6rem; padding: 0; max-width: 24em; }
.sidehoved .under { color: #4A5A66; font-size: 1rem; max-width: 52em; margin: 0; line-height: 1.55; }
.sidehoved .chips { display: flex; gap: .5rem 1.4rem; flex-wrap: wrap; margin-top: 1rem; }
.chip { display: inline-flex; align-items: center; gap: .35rem; font-size: .78rem; color: #5B6B78; }
.chip.live { color: #1B2B36; font-weight: 600; gap: .5rem; }
.live-prik { width: 8px; height: 8px; border-radius: 50%; background: #2E9E6B; flex: none; animation: live 2.4s ease-out infinite; }
@keyframes live { 0% { box-shadow: 0 0 0 0 rgba(46,158,107,.5); } 70%, 100% { box-shadow: 0 0 0 7px rgba(46,158,107,0); } }
@media (prefers-reduced-motion: reduce) { .live-prik { animation: none; } }

/* Executive summary */
.resume { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; border-top: 1px solid #0B2230; border-bottom: 1px solid #E1E6EA; margin: .4rem 0 2rem; }
.resume > div { padding: 1rem 1.2rem 1.1rem 0; }
.resume > div + div { padding-left: 1.2rem; border-left: 1px solid #E1E6EA; }
.resume .nr { font-family: 'Source Serif 4', serif; font-size: .9rem; color: #5B6B78; font-weight: 600; }
.resume .stor { font-family: 'Source Serif 4', serif; font-size: 2.3rem; font-weight: 600; color: #0B2230; line-height: 1.05;
                margin: .3rem 0 .35rem; font-variant-numeric: tabular-nums; }
.resume .tekst { font-size: .9rem; color: #2A3A46; line-height: 1.45; }
.resume .mini { margin: .1rem 0 .55rem; max-width: 220px; }
.mini svg { display: block; width: 100%; height: auto; overflow: visible; }
.mini-note { font-size: .68rem; color: #8A99A6; margin-top: .2rem; letter-spacing: .01em; }
.mini .andel { height: 8px; background: #EDF1F4; border-radius: 4px; overflow: hidden; margin: .9rem 0 .2rem; }
.mini .andel i { display: block; height: 100%; background: #D64545; border-radius: 4px; }
.mini .prikrad { display: flex; gap: 5px; flex-wrap: wrap; margin: .75rem 0 .1rem; }
.mini .prikrad i { width: 11px; height: 11px; border-radius: 50%; display: block; }
.mini .prikrad i.valgt { box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 3.5px #0B2230; }
@media (max-width: 760px) { .resume { grid-template-columns: 1fr; } .resume > div + div { padding-left: 0; border-left: 0; border-top: 1px solid #E1E6EA; } }

/* Figurer */
.figur { margin: 2.2rem 0 .5rem; }
.figur .label { font-size: .72rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: #5B6B78; }
.figur .titel { font-family: 'Source Serif 4', serif; font-size: 1.35rem; font-weight: 600; color: #0B2230; line-height: 1.25; margin: .25rem 0 .2rem; }
.figur .undertitel { font-size: .85rem; color: #5B6B78; }
.kilde { font-size: .74rem; color: #6B7A86; border-top: 1px solid #E1E6EA; padding-top: .4rem; margin-top: .3rem; }

/* Områdevalg: tydelig kant og en hjælpeboble i samme stil som tidsmaskinens; boblen bliver, indtil man selv har valgt et område */
.st-key-omraadevalg { position: relative; }
.st-key-omraadevalg:has(.valghjaelp) { padding-top: 2rem; }
.st-key-omraadevalg label p { font-weight: 600; color: #0B2230; }
.st-key-omraadevalg .react-aria-ComboBox [role="group"] { border: 1.5px solid #6F7D3C; background: #FFFFFF; cursor: pointer; }
.st-key-omraadevalg:has(.valghjaelp) .react-aria-ComboBox [role="group"] { animation: valgpuls 1.4s ease-in-out .6s 3; }
@keyframes valgpuls { 0%, 100% { box-shadow: 0 0 0 0 rgba(111,125,60,0); } 50% { box-shadow: 0 0 0 5px rgba(111,125,60,.35); } }
.st-key-omraadevalg [data-testid="stElementContainer"]:has(.valghjaelp) { position: absolute; right: 0; bottom: calc(2.5rem + 8px);
  width: auto; z-index: 5; pointer-events: none; }
.valghjaelp { position: relative; width: 250px; background: #5E6B30; color: #FFFFFF; border-radius: 8px;
  padding: 9px 13px 10px; font-size: .8rem; line-height: 1.45; box-shadow: 0 10px 28px rgba(11,34,48,.22);
  animation: valghjaelp .5s ease .3s both; }
.valghjaelp b { display: flex; align-items: center; gap: .3rem; font-size: .86rem; margin-bottom: 2px; }
.valghjaelp::after { content: ""; position: absolute; right: 22px; bottom: -6px; border: 6px solid transparent;
  border-bottom: 0; border-top-color: #5E6B30; }
@keyframes valghjaelp { from { opacity: 0; transform: translateY(6px); } }
@media (max-width: 640px) {  /* smal skærm: boblen står over feltet i stedet for at dække etiketten */
  .st-key-omraadevalg:has(.valghjaelp) { padding-top: 0; }
  .st-key-omraadevalg [data-testid="stElementContainer"]:has(.valghjaelp) { position: static; }
  .valghjaelp { width: auto; margin-bottom: 2px; }
  .valghjaelp::after { right: auto; left: 22px; }
}
@media (prefers-reduced-motion: reduce) { .valghjaelp, .st-key-omraadevalg .react-aria-ComboBox [role="group"] { animation: none; } }

/* Ugens udsving: klikbare kort under nøgletallene. Hele kortet løfter sig ved hover, knappen er handlingen. */
.st-key-kortbaand { background: #F3F5F7; border-radius: 14px; padding: 1.1rem 1.2rem 1.2rem; margin: .2rem 0 1rem; gap: .7rem; }
.udsving-hoved { display: flex; align-items: baseline; gap: .8rem; flex-wrap: wrap; margin: 0; }
.udsving-hoved b { font-family: 'Source Serif 4', serif; font-size: 1.15rem; color: #0B2230; }
.udsving-hoved span { font-size: .8rem; color: #6B7A86; }
[class*="st-key-udsving_"] { background: #FFFFFF; border: 1px solid #E1E6EA; border-radius: 10px; padding: .85rem 1rem .55rem;
  gap: .2rem; height: 100%; transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease; }
[class*="st-key-udsving_"]:hover { border-color: #C5CCA6; box-shadow: 0 8px 22px rgba(11,34,48,.10); transform: translateY(-2px); }
.udsving-kort .etiket { display: flex; align-items: center; gap: .3rem; font-size: .68rem; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: #6B7A86; }
.udsving-kort .navn { font-weight: 600; color: #0B2230; font-size: .98rem; margin-top: .45rem; line-height: 1.25; }
.udsving-kort .stort { font-family: 'Source Serif 4', serif; font-size: 1.7rem; font-weight: 600; line-height: 1.1; margin: .15rem 0;
  font-variant-numeric: tabular-nums; }
.udsving-kort .note { font-size: .76rem; color: #5B6B78; line-height: 1.4; }
.udsving-kort { padding-bottom: .9rem; }
/* Kortene i rækken får samme højde, og knappen står nederst i hvert kort */
[data-testid="stHorizontalBlock"]:has([class*="st-key-udsving_"]) { align-items: stretch; }
[data-testid="stColumn"]:has([class*="st-key-udsving_"]) > [data-testid="stVerticalBlock"] { height: 100%; }
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-udsving_"]) { flex: 1; }
[class*="st-key-udsving_"] { justify-content: space-between; }
[class*="st-key-aabn_"] button { color: #55602B; font-weight: 600; padding: 0; min-height: 0; }
@media (max-width: 640px) {  /* to kort pr. række på mobil i stedet for fire under hinanden */
  [data-testid="stHorizontalBlock"]:has([class*="st-key-udsving_"]) { flex-wrap: wrap; gap: .6rem; }
  [data-testid="stColumn"]:has([class*="st-key-udsving_"]) { flex: 1 1 calc(50% - .3rem) !important;
    min-width: calc(50% - .3rem) !important; width: calc(50% - .3rem) !important; }
  [class*="st-key-udsving_"] { padding: .7rem .75rem .45rem; }
  .udsving-kort .stort { font-size: 1.45rem; }
  .udsving-kort .navn { font-size: .9rem; }
}
@media (prefers-reduced-motion: reduce) { [class*="st-key-udsving_"] { transition: none; } [class*="st-key-udsving_"]:hover { transform: none; } }

/* Søgefeltet øverst på forsiden: rundt felt med lup; grå kant i hvile, grøn ved hover og fokus. Valgt række i tabeller fremhæves */
.st-key-soegning { max-width: 680px; margin-bottom: .4rem; }
.st-key-soegning .react-aria-ComboBox [role="group"] { position: relative; border: 1px solid #CBD3D9; border-radius: 999px;
  background: #FFFFFF; min-height: 3.1rem; padding-left: 2.7rem; box-shadow: 0 2px 10px rgba(11,34,48,.06);
  transition: border-color .15s, box-shadow .15s; }
.st-key-soegning .react-aria-ComboBox [role="group"]::before { content: "search"; font-family: 'Material Symbols Outlined';
  position: absolute; left: 1.05rem; top: 50%; transform: translateY(-50%); font-size: 22px; line-height: 1; color: #6F7D3C; }
.st-key-soegning .react-aria-ComboBox [role="group"]:hover { border-color: #6F7D3C; }
.st-key-soegning .react-aria-ComboBox [role="group"]:focus-within { border-color: #6F7D3C; box-shadow: 0 0 0 4px rgba(111,125,60,.18); }
.st-key-soegning input { font-size: 1rem; }
.tabel tr.valgt td { background: #EEF1E4; }
.tabel tr.valgt td:first-child { box-shadow: inset 3px 0 0 #6F7D3C; }

/* Kort og søjler i figur 1 er forbundet: lille hjælpelinje over kortet og et hoved for det valgte område */
.korthjaelp { display: flex; align-items: center; gap: .35rem; font-size: .8rem; font-weight: 500; color: #55602B; margin-bottom: .35rem; }
.omraadehoved { margin: -.3rem 0 .6rem; }
.omraadehoved b { display: block; font-family: 'Source Serif 4', serif; font-size: 1.1rem; color: #0B2230; }
.omraadehoved span { font-size: .8rem; color: #5B6B78; }
.omraadehoved .prik { margin-left: .1rem; }
.st-key-alle_omraader button, .st-key-hele_omraadet button { color: #55602B; font-weight: 600; padding: 0; min-height: 0; }

/* Forklaring over behandlingsfiguren: linjer og flade tegnet som i grafen */
.effektnoegle { display: flex; flex-wrap: wrap; gap: .4rem 1.4rem; font-size: .82rem; color: #1B2B36; margin: .3rem 0 .8rem; }
.effektnoegle span { display: inline-flex; align-items: center; gap: .45rem; }
.effektnoegle .streg { display: inline-block; width: 22px; border-top: 3px solid; }
.effektnoegle .streg.stiplet { border-top-style: dashed; border-top-width: 2px; }
.effektnoegle .flade { display: inline-block; width: 16px; height: 11px; opacity: .3; border-radius: 2px; }

/* Tabel */
table.tabel { width: 100%; border-collapse: collapse; font-size: .84rem; font-variant-numeric: tabular-nums; }
.tabel th { text-align: left; font-size: .68rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6B7A86;
            border-bottom: 1px solid #0B2230; padding: .45rem .5rem; white-space: nowrap; }
.tabel td { border-bottom: 1px solid #EDF1F4; padding: .42rem .5rem; color: #1B2B36; vertical-align: middle; }
.tabel td.tal, .tabel th.tal { text-align: right; }
.tabel td.tal { white-space: nowrap; }
.tabel tr:hover td { background: #F6F8FA; }
.tabel .navn { font-weight: 500; }
.tabel td.lys { white-space: nowrap; }
@media (min-width: 641px) { .tabel td.navn { white-space: nowrap; } }  /* navne på én linje, når der er plads */
/* Kolonneoverskrifter må bryde (med info-ikon bliver de brede); navnet holdes på én linje, undtagen i modeltabellen,
   der har ni kolonner */
.tabel th { white-space: normal; vertical-align: bottom; }
.tabel.modeller td.navn { white-space: normal; }
@media (min-width: 641px) { .tabel.modeller td.navn { min-width: 10rem; } }
.tabel.modeller th { letter-spacing: .05em; }
.st-key-prognoselink { margin: -1.2rem 0 1.6rem; }
.st-key-prognoselink a { color: #55602B !important; font-weight: 600; padding: 0; }
.st-key-prognoselink a:hover { text-decoration: underline; }
/* Navne i tabellerne er links: diskrete i hvile, i accentfarven med pil, når rækken peges på */
.tabel a.radlink { color: inherit; text-decoration: none; }
.tabel a.radlink::after { content: " →"; color: #55602B; opacity: 0; transition: opacity .15s; }
.tabel tr:hover a.radlink { color: #55602B; }
.tabel tr:hover a.radlink::after, .tabel a.radlink:focus-visible::after { opacity: 1; }
/* Hele rækken er klikbar (linket strækkes over rækken); info-boblerne ligger ovenpå og virker stadig */
.tabel tr:has(a.radlink) { position: relative; }
.tabel a.radlink::before { content: ""; position: absolute; inset: 0; }
.tabel .info { z-index: 2; }
.tabel .info:hover, .tabel .info:focus { z-index: 70; }
.tabel .po { color: #6B7A86; width: 2.2rem; }
.tabel .minibar { display: inline-block; height: 6px; border-radius: 1px; vertical-align: middle; margin-left: .45rem; }
/* Brede tabeller og små multipler scrolles vandret på mobil i stedet for at blive skåret af */
/* (tabeller kun på mobil – på brede skærme passer de, og så klippes info-boblerne ikke af rammen) */
[data-testid="stFullScreenFrame"]:has([data-testid="stVegaLiteChart"]) { overflow-x: auto; }
.st-key-smaa_mobil, .st-key-effekt_mobil { display: none; }
.stort-panel-hoved { display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap; margin: .6rem 0 .1rem; }
.stort-panel-hoved b { font-family: 'Source Serif 4', serif; font-size: 1.1rem; color: #0B2230; }
.stort-panel-hoved span { font-size: .8rem; color: #6B7A86; }
@media (max-width: 640px) {
  [data-testid="stMarkdownContainer"]:has(table.tabel) { overflow-x: auto; }
  .st-key-smaa_bred, .st-key-effekt_bred { display: none; }
  .st-key-smaa_mobil, .st-key-effekt_mobil { display: block; }
  .tabel .ekstra { display: none; }             /* sekundære kolonner skjules på mobil */
  .tabel th, .tabel th.tal { white-space: normal; letter-spacing: .04em; }
  .tabel td, .tabel th { padding: .4rem .3rem; }
  .tabel .minibar { display: none; }
  .tabel td.lys .prik { display: none; }        /* navnet står der; prikken koster bredde */
}

/* Streamlits egne knapper (Fork, GitHub, menu) skjules, så appen fremstår som et færdigt produkt.
   Udvid-knappen til navigationen på mobil bevares. */
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"] { display: none !important; }
.prik { width: .6rem; height: .6rem; border-radius: 50%; display: inline-block; vertical-align: .05em; margin-right: .35rem; }

/* Nøgletal (bruges på andre sider) */
.kort { background: #FFFFFF; border-top: 1px solid #0B2230; padding: .8rem 0 .4rem; height: 100%; }
.kort .hoved { display: flex; align-items: center; gap: .4rem; color: #5B6B78; }
.kort .etiket { font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .1em; }
.kort .tal { font-family: 'Source Serif 4', serif; font-size: 2rem; font-weight: 600; color: #0B2230; line-height: 1.1; margin-top: .3rem; font-variant-numeric: tabular-nums; }
.kort .note { font-size: .8rem; color: #6B7A86; margin-top: .15rem; }
.kort .bar { height: 3px; background: #EDF1F4; margin-top: .55rem; }
.kort .bar i { display: block; height: 100%; }

/* Info-bobler: et lille i ved nøgletal og kolonner (eller en prikket understregning under et tal).
   Forklaringen vises ved hover og ved tryk, fordi ikonet kan få fokus. På mobil står boblen fast nederst
   på skærmen, så den hverken går ud over kanten eller klippes af en tabel, der kan rulles. */
.info { position: relative; display: inline-flex; align-items: center; cursor: help; outline: none; vertical-align: middle; }
.info > .ikon { font-size: 15px; color: #8A99A6; margin-left: .2rem; transition: color .15s; }
.info:hover > .ikon, .info:focus > .ikon { color: #6F7D3C; }
.info:focus-visible { box-shadow: 0 0 0 2px rgba(111,125,60,.45); border-radius: 4px; }
.info.forklar { border-bottom: 1px dotted currentColor; }
.info-boble { position: absolute; top: calc(100% + 8px); left: -10px; z-index: 60; width: max-content; max-width: 280px;
  background: #0B2230; color: #E8EEF2; font: 400 .78rem/1.5 Inter, sans-serif; letter-spacing: normal; text-transform: none;
  text-align: left; white-space: normal; padding: .6rem .8rem; border-radius: 6px; box-shadow: 0 10px 28px rgba(11,34,48,.25);
  opacity: 0; visibility: hidden; transform: translateY(-4px); pointer-events: none;
  transition: opacity .15s ease, transform .15s ease, visibility .15s; }
.info-boble::before { content: ""; position: absolute; top: -5px; left: 14px; border: 5px solid transparent; border-top: 0;
  border-bottom-color: #0B2230; }
.info-boble b { color: #FFFFFF; font-weight: 600; }
.info-boble .regnestykke { display: block; margin-top: .35rem; padding-top: .35rem; border-top: 1px solid rgba(255,255,255,.15);
  font-variant-numeric: tabular-nums; color: #FFFFFF; }
.info.hoejre .info-boble { left: auto; right: -10px; }
.info.hoejre .info-boble::before { left: auto; right: 14px; }
.info:hover .info-boble, .info:focus .info-boble { opacity: 1; visibility: visible; transform: none; }
@media (max-width: 640px) {
  .info-boble, .info.hoejre .info-boble { position: fixed; top: auto; bottom: 16px; left: 16px; right: 16px; width: auto; max-width: none;
    font-size: .84rem; padding: .8rem 1rem; }
  .info-boble::before { display: none; }
}
@media (prefers-reduced-motion: reduce) { .info-boble { transition: none; } }

.forklaring { display: flex; flex-wrap: wrap; gap: .35rem 1.2rem; font-size: .78rem; color: #5B6B78; margin: .5rem 0 .6rem; }
.forklaring span { display: inline-flex; align-items: center; gap: .1rem; }
.metode { font-size: .8rem; color: #4A5A66; line-height: 1.55; background: #F6F8FA; padding: 1rem 1.2rem; border-left: 3px solid #0B2230; margin-top: 2.4rem; }
/* About: fire korte spalter over fodnoten – hvem, data, metode, kode */
.om { margin-top: 3rem; padding: 1.4rem 1.5rem 1.2rem; background: #F6F8FA; border-radius: 10px; }
.om-hoved { font-family: 'Source Serif 4', serif; font-size: 1.15rem; font-weight: 600; color: #0B2230; margin-bottom: .8rem; }
.om-gitter { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.2rem 1.6rem; }
.om-gitter div { font-size: .8rem; line-height: 1.55; color: #4A5A66; }
.om-gitter b { display: block; font-size: .68rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
  color: #5B6B78; margin-bottom: .3rem; }
.om a { color: #55602B; font-weight: 600; }
@media (max-width: 900px) { .om-gitter { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .om-gitter { grid-template-columns: 1fr; } .om { padding: 1.1rem 1rem; } }

/* Afsnit: deler en side i to dele (fx prognosen for alle og evalueringen for fagfolk) */
.afsnit { margin: 3.4rem 0 1.2rem; padding-top: 1.4rem; border-top: 2px solid #0B2230; }
.afsnit .overlinje { font-size: .72rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; color: #5B6B78; }
.afsnit h2 { font-size: clamp(1.35rem, 2.4vw, 1.75rem) !important; line-height: 1.2; margin: .45rem 0 .5rem; padding: 0; max-width: 30em; }
.afsnit p { color: #4A5A66; font-size: .95rem; max-width: 52em; margin: 0; line-height: 1.55; }

.fodnote { font-size: .74rem; color: #6B7A86; border-top: 1px solid #E1E6EA; padding-top: .8rem; margin-top: 2rem; }
.fodnote a { color: #1D4E6B; }
.fodnote .afsender { font-size: .82rem; color: #1B2B36; margin-bottom: .45rem; }
.fodnote .afsender a { font-weight: 600; }
.fodnote .opdateret { color: #1B2B36; margin-bottom: .45rem; }
</style>
"""


# --- 3. HTML-byggeklodser ----------------------------------------------------------------------

def ikon(navn: str, farve: str = "inherit", titel: str = "") -> str:
    """Material Symbols-ikon (outlined), fx 'thermostat', 'trending_up', 'warning'."""
    return f'<span class="ikon" style="color:{farve}" title="{titel}" aria-hidden="{str(not titel).lower()}">{navn}</span>'


def sidehoved(overlinje: str, titel: str, under: str, chips: list[tuple[str, str]] = ()) -> str:
    # Ikonet "live" giver en grøn, pulserende prik – bruges til opdateringslinjen, så det ses, at data er friske.
    chip_html = "".join(f'<span class="chip live"><i class="live-prik"></i>{t}</span>' if i == "live"
                        else f'<span class="chip">{ikon(i)} {t}</span>' for i, t in chips)
    return (
        f'<div class="sidehoved"><div class="overlinje">{overlinje}</div><h1>{titel}</h1>'
        f'<p class="under">{under}</p><div class="chips">{chip_html}</div></div>'
    )


def afsnit(overlinje: str, titel: str, under: str) -> str:
    """Overskrift for en ny del af en side – mindre end sidehovedet, med en tyk linje over."""
    return f'<div class="afsnit"><div class="overlinje">{overlinje}</div><h2>{titel}</h2><p>{under}</p></div>'


def resume(punkter: list[tuple]) -> str:
    """Executive summary: [(stort tal, forklarende tekst[, info-tekst om beregningen[, minigraf]]), ...]."""
    # Boblen i sidste kolonne åbner mod venstre, så den ikke går ud over sidens højre kant.
    felter = "".join(
        f'<div><div class="nr">{i:02d}</div><div class="stor">{p[0]}{info(p[2], "hoejre" if i == len(punkter) else "venstre") if len(p) > 2 and p[2] else ""}</div>'
        f'{p[3] if len(p) > 3 and p[3] else ""}<div class="tekst">{p[1]}</div></div>'
        for i, p in enumerate(punkter, 1)
    )
    return f'<div class="resume">{felter}</div>'


def figur(nr: int, titel: str, undertitel: str) -> str:
    return (f'<div class="figur"><div class="label">Exhibit {nr}</div>'
            f'<div class="titel">{titel}</div><div class="undertitel">{undertitel}</div></div>')


def info(tekst: str, side: str = "venstre") -> str:
    """Info-ikon med en forklaring i en boble (HTML tilladt). side="hoejre" til højrestillede kolonner."""
    return (f'<span class="info {side}" tabindex="0" role="button" aria-label="How this is calculated">'
            f'<span class="ikon" aria-hidden="true">info</span><span class="info-boble" role="tooltip">{tekst}</span></span>')


def forklar(vis: str, tekst: str, side: str = "hoejre") -> str:
    """Et tal med prikket understregning, der forklarer sig selv i en boble (fx hvordan en ændring er regnet)."""
    return (f'<span class="info forklar {side}" tabindex="0">{vis}'
            f'<span class="info-boble" role="tooltip">{tekst}</span></span>')


def kilde(tekst: str = "") -> str:
    return f'<div class="kilde">Source: BarentsWatch / Mattilsynet (NLOD); own analysis.{" " + tekst if tekst else ""}</div>'


def kort(etiket: str, tal: str, note: str = "", ikon_navn: str = "", bar: tuple[float, str] | None = None) -> str:
    hoved = f'<div class="hoved">{ikon(ikon_navn) if ikon_navn else ""}<span class="etiket">{etiket}</span></div>'
    bjaelke = f'<div class="bar"><i style="width:{min(bar[0], 1):.0%};background:{bar[1]}"></i></div>' if bar else ""
    return f'<div class="kort">{hoved}<div class="tal">{tal}</div><div class="note">{note}</div>{bjaelke}</div>'


# --- 3b. Minigrafer -------------------------------------------------------------------------
# Små, rene SVG-grafer, der giver nøgletallene et billede. De skalerer med bredden (viewBox) og bruger
# designsystemets farver; tallene står stadig i teksten, så graferne er pynt med mening – ikke eneste kilde.

def _sti(vaerdier: list[float], x, y) -> str:
    """SVG-sti gennem punkterne; manglende værdier (NaN) giver et hul i linjen."""
    sti, ny = [], True
    for i, v in enumerate(vaerdier):
        if pd.isna(v):
            ny = True
            continue
        sti.append(f"{'M' if ny else 'L'}{x(i):.1f},{y(v):.1f}")
        ny = False
    return " ".join(sti)


def kurve(vaerdier: list[float], sammenlign: list[float] | None = None, graense: float | None = None,
          note: str = "", bredde: int = 180, hoejde: int = 38) -> str:
    """Lille kurve over de seneste uger: navy linje, stiplet grå sammenligning og grænsen som rød prikket linje."""
    alle = [v for v in [*vaerdier, *(sammenlign or []), graense or 0] if pd.notna(v)]
    top = max(alle + [0.05]) * 1.1
    n = max(len(vaerdier) - 1, 1)
    x = lambda i: 3 + i * (bredde - 6) / n
    y = lambda v: hoejde - 3 - min(v, top) / top * (hoejde - 6)
    dele = []
    if graense:
        dele.append(f'<line x1="0" x2="{bredde}" y1="{y(graense):.1f}" y2="{y(graense):.1f}" stroke="#D64545" '
                    'stroke-width="1" stroke-dasharray="2 3" opacity=".8"/>')
    if sammenlign:
        dele.append(f'<path d="{_sti(sammenlign, x, y)}" fill="none" stroke="#8A99A6" stroke-width="1.3" stroke-dasharray="3 2"/>')
    dele.append(f'<path d="{_sti(vaerdier, x, y)}" fill="none" stroke="#0B2230" stroke-width="1.8" stroke-linejoin="round"/>')
    sidste = [(i, v) for i, v in enumerate(vaerdier) if pd.notna(v)]
    if sidste:
        i, v = sidste[-1]
        dele.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="3" fill="#0B2230" stroke="#FFFFFF" stroke-width="1.2"/>')
    return (f'<div class="mini"><svg viewBox="0 0 {bredde} {hoejde}" role="img" '
            f'aria-label="{note}">{"".join(dele)}</svg><div class="mini-note">{note}</div></div>')


def andelsbjaelke(andel: float, note: str = "") -> str:
    """Vandret bjælke med andelen i rødt (mindst et par pixel, så en lille andel stadig ses)."""
    return (f'<div class="mini"><div class="andel"><i style="width:max(3px, {andel:.1%})"></i></div>'
            f'<div class="mini-note">{note}</div></div>')


def prikker(punkter: list[tuple[str, str, bool]], note: str = "") -> str:
    """Række af prikker: (farve, etiket til tooltip, fremhævet). Fx de 13 områders trafiklys."""
    p = "".join(f'<i class="{"valgt" if valgt else ""}" style="background:{farve}" title="{etiket}"></i>'
                for farve, etiket, valgt in punkter)
    return f'<div class="mini"><div class="prikrad">{p}</div><div class="mini-note">{note}</div></div>'


def strimmel(vaerdier: list[float], markeret: float | None, graense: float | None = None, note: str = "",
             bredde: int = 180, hoejde: int = 26) -> str:
    """Alle anlæg i et område som prikker langs en akse; det valgte anlæg står stort og mørkt omkranset."""
    # Aksen kappes ved 1,2 (eller 2 × grænsen), så ét ekstremt anlæg ikke klemmer resten sammen i venstre side;
    # anlæg over kappet står ved højre kant.
    top = min(max([*vaerdier, markeret or 0, graense or 0, 0.05]) * 1.05, max(1.2, 2 * (graense or 0)))
    x = lambda v: 4 + min(v, top) / top * (bredde - 8)
    dele = []
    if graense:
        dele.append(f'<line x1="{x(graense):.1f}" x2="{x(graense):.1f}" y1="2" y2="{hoejde - 2}" stroke="#D64545" '
                    'stroke-width="1" stroke-dasharray="2 2"/>')
    dele += [f'<circle cx="{x(v):.1f}" cy="{hoejde / 2}" r="2.6" fill="{LUS_FARVER[lus_niveau(v)]}" opacity=".45"/>'
             for v in vaerdier if pd.notna(v)]
    if markeret is not None and pd.notna(markeret):
        dele.append(f'<circle cx="{x(markeret):.1f}" cy="{hoejde / 2}" r="5.5" fill="{LUS_FARVER[lus_niveau(markeret)]}" '
                    'stroke="#0B2230" stroke-width="2"/>')
    return (f'<div class="mini"><svg viewBox="0 0 {bredde} {hoejde}" role="img" aria-label="{note}">{"".join(dele)}</svg>'
            f'<div class="mini-note">{note}</div></div>')


# --- 4. Lusetal i tekst ---------------------------------------------------------------------

def lus_niveau(v: float) -> str:
    return "lav" if v < 0.2 else ("mellem" if v <= 0.5 else "hoej")


LAVT_NIVEAU = 0.05  # under dette niveau vises ændringer i lus pr. fisk, ikke i procent


def trend(nu: float, foer: float) -> tuple[str, str, str]:
    """Ikon, farve og tekst for udviklingen siden de 4 foregående uger."""
    if pd.isna(foer) or foer == 0:
        return "trending_flat", "#6B7A86", "no comparison"
    if max(nu, foer) < LAVT_NIVEAU:  # procenter af næsten ingenting ser dramatiske ud – vis ikke en alarm
        return "trending_flat", "#6B7A86", f"low level ({nu - foer:+.2f} lice per fish vs. previous 4 weeks)"
    rel = nu / foer - 1
    if rel > 0.15:
        return "trending_up", "#D64545", f"rising ({rel:+.0%} vs. previous 4 weeks)"
    if rel < -0.15:
        return "trending_down", "#1F7A8C", f"falling ({rel:+.0%} vs. previous 4 weeks)"
    return "trending_flat", "#6B7A86", f"stable ({rel:+.0%} vs. previous 4 weeks)"


# --- 5. Altair-tema ---------------------------------------------------------------------------

@alt.theme.register("konsulent", enable=True)
def _altair_tema() -> alt.theme.ThemeConfig:
    """Fælles grafstil: ingen ramme, diskrete gitterlinjer, Inter i akser, serif i titler."""
    return {
        "config": {
            "background": "#FFFFFF",
            "font": SANS,
            "view": {"stroke": None},
            "axis": {"labelColor": "#5B6B78", "titleColor": "#5B6B78", "labelFontSize": 11, "titleFontSize": 11,
                     "titleFontWeight": 500, "gridColor": "#EDF1F4", "domainColor": "#AEBBC5", "tickColor": "#AEBBC5"},
            "axisY": {"domain": False, "ticks": False},
            "legend": {"labelColor": "#2A3A46", "titleColor": "#5B6B78", "labelFontSize": 11, "titleFontSize": 11,
                       "titleFontWeight": 500, "symbolType": "circle"},
            "header": {"labelFont": SANS, "labelFontSize": 11, "labelColor": "#0B2230", "labelFontWeight": 600,
                       "labelAnchor": "start", "title": None},
            "title": {"font": SERIF, "color": "#0B2230", "anchor": "start", "fontWeight": 600},
        }
    }
