"""Designsystem for Streamlit-appen.

Inspireret af branchens egne flader (BarentsWatch Fiskehelse, Mowi, SalMar): dyb havblå og hvide
flader, én laksefarvet accent, en stram sans-serif og store tal i nøgterne statuskort.
"""

import pandas as pd

FARVER = {
    "blaek": "#0B2230",      # dyb havblå – overskrifter, mørke flader
    "hav": "#12405A",        # sekundær blå – linjer i grafer
    "skifer": "#55687A",     # brødtekst, akser
    "linje": "#DDE4E9",      # kanter og gitter
    "flade": "#FFFFFF",
    "baggrund": "#F4F6F8",
    "laks": "#F26B4F",       # eneste accent – prognoser, fremhævning
    "rav": "#E2A23B",
    # Bagudkompatible navne brugt i graferne
    "fjord": "#12405A",
    "lyng": "#55687A",
}

LYS_FARVER = {  # trafiklys: kant, baggrund, tekst
    "green": ("#2E8B57", "#E5F3EB", "#1D5C39"),
    "yellow": ("#D9A21B", "#FBF2DA", "#7A5A08"),
    "red": ("#C8403A", "#FBE4E2", "#8A231F"),
}
LUS_FARVER = {"lav": "#1F7A8C", "mellem": "#E2A23B", "hoej": "#D64545"}  # < 0,2 · 0,2–0,5 · > 0,5

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

html, body, [class*="css"], .stMarkdown, p, li, td, th, label, button, input { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; letter-spacing: -0.02em; color: #0B2230; }
h3 { font-size: 1.15rem !important; margin-top: .6rem; }
.block-container { padding-top: 3.2rem; max-width: 1180px; }
header[data-testid="stHeader"] { background: rgba(244, 246, 248, .92); backdrop-filter: blur(8px); border-bottom: 1px solid #DDE4E9; }
[data-testid="stCaptionContainer"] { color: #6B7C8A; }

.ikon { font-family: 'Material Symbols Outlined'; font-weight: normal; font-style: normal; line-height: 1;
        display: inline-block; vertical-align: -0.2em; font-size: 1.2em; -webkit-font-smoothing: antialiased; }

/* Sidehoved */
.sidehoved { background: #0B2230; color: #FFFFFF; border-radius: 10px; padding: 1.6rem 1.8rem 1.4rem;
             margin-bottom: 1.4rem; position: relative; overflow: hidden; }
.sidehoved::after { content: ""; position: absolute; inset: 0; pointer-events: none;
                    background: radial-gradient(900px 260px at 100% 0%, rgba(242,107,79,.18), transparent 60%),
                                radial-gradient(700px 300px at 0% 120%, rgba(31,122,140,.35), transparent 60%); }
.sidehoved .overlinje { font-size: .74rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: #F26B4F; }
.sidehoved h1 { color: #FFFFFF !important; font-size: clamp(1.6rem, 3.4vw, 2.3rem) !important; margin: .35rem 0 .4rem; padding: 0; line-height: 1.15; }
.sidehoved .under { color: #B9C7D2; font-size: .98rem; max-width: 46em; margin: 0; }
.sidehoved .chips { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: 1rem; position: relative; z-index: 1; }
.chip { display: inline-flex; align-items: center; gap: .35rem; font-size: .78rem; color: #DCE5EC;
        border: 1px solid rgba(255,255,255,.18); border-radius: 999px; padding: .22rem .65rem; }

/* Nøgletal */
.kort { background: #FFFFFF; border: 1px solid #DDE4E9; border-radius: 8px; padding: .95rem 1.05rem; height: 100%; }
.kort .hoved { display: flex; align-items: center; gap: .4rem; color: #55687A; }
.kort .hoved .ikon { font-size: 1.1rem; }
.kort .etiket { font-size: .76rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
.kort .tal { font-size: 2rem; font-weight: 700; color: #0B2230; line-height: 1.1; margin-top: .35rem;
             font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.kort .note { font-size: .8rem; color: #6B7C8A; margin-top: .15rem; }
.kort .bar { height: 4px; border-radius: 2px; background: #EEF2F5; margin-top: .6rem; overflow: hidden; }
.kort .bar i { display: block; height: 100%; }

/* Områdekort */
.omr-gitter { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: .75rem; }
.omr { background: #FFFFFF; border: 1px solid #DDE4E9; border-radius: 8px; padding: .8rem .95rem; border-top: 3px solid var(--lys); }
.omr .top { display: flex; justify-content: space-between; align-items: center; gap: .5rem; }
.omr .nr { font-size: .74rem; font-weight: 600; color: #6B7C8A; letter-spacing: .06em; }
.omr .navn { font-weight: 600; font-size: .98rem; color: #0B2230; line-height: 1.25; margin-top: .1rem; }
.omr .lys { font-size: .7rem; font-weight: 600; padding: .1rem .5rem; border-radius: 4px;
            background: var(--lys-bg); color: var(--lys-tekst); white-space: nowrap; display: inline-flex; align-items: center; gap: .3rem; }
.omr .lys i { width: .5rem; height: .5rem; border-radius: 50%; background: var(--lys); display: inline-block; }
.omr .hovedtal { display: flex; align-items: baseline; gap: .4rem; margin-top: .55rem; }
.omr .hovedtal b { font-size: 1.5rem; color: #0B2230; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.omr .hovedtal span { font-size: .78rem; color: #6B7C8A; }
.omr .raekke { display: flex; gap: .9rem; margin-top: .45rem; flex-wrap: wrap; font-size: .82rem; color: #55687A;
               border-top: 1px solid #EEF2F5; padding-top: .45rem; }
.omr .raekke span { display: inline-flex; align-items: center; gap: .2rem; font-variant-numeric: tabular-nums; }

.forklaring { display: flex; flex-wrap: wrap; gap: .35rem 1.2rem; font-size: .8rem; color: #55687A; margin: .2rem 0 .8rem; }
.forklaring span { display: inline-flex; align-items: center; gap: .3rem; }
.prik { width: .65rem; height: .65rem; border-radius: 50%; display: inline-block; }
.fodnote { font-size: .78rem; color: #6B7C8A; border-top: 1px solid #DDE4E9; padding-top: .8rem; margin-top: 2.2rem; }
.fodnote a { color: #12405A; }
</style>
"""


def ikon(navn: str, farve: str = "inherit", titel: str = "") -> str:
    """Material Symbols-ikon (outlined), fx 'thermostat', 'trending_up', 'warning'."""
    return f'<span class="ikon" style="color:{farve}" title="{titel}" aria-hidden="{str(not titel).lower()}">{navn}</span>'


def sidehoved(overlinje: str, titel: str, under: str, chips: list[tuple[str, str]] = ()) -> str:
    chip_html = "".join(f'<span class="chip">{ikon(i)} {t}</span>' for i, t in chips)
    return (
        f'<div class="sidehoved"><div class="overlinje">{overlinje}</div><h1>{titel}</h1>'
        f'<p class="under">{under}</p><div class="chips">{chip_html}</div></div>'
    )


def kort(etiket: str, tal: str, note: str = "", ikon_navn: str = "", bar: tuple[float, str] | None = None) -> str:
    hoved = f'<div class="hoved">{ikon(ikon_navn) if ikon_navn else ""}<span class="etiket">{etiket}</span></div>'
    bjaelke = f'<div class="bar"><i style="width:{min(bar[0], 1):.0%};background:{bar[1]}"></i></div>' if bar else ""
    return f'<div class="kort">{hoved}<div class="tal">{tal}</div><div class="note">{note}</div>{bjaelke}</div>'


def lus_niveau(v: float) -> str:
    return "lav" if v < 0.2 else ("mellem" if v <= 0.5 else "hoej")


def trend(nu: float, foer: float) -> tuple[str, str, str]:
    """Ikon, farve og tekst for udviklingen siden de 4 foregående uger."""
    if pd.isna(foer) or foer == 0:
        return "trending_flat", "#6B7C8A", "ingen sammenligning"
    rel = nu / foer - 1
    if rel > 0.15:
        return "trending_up", "#D64545", f"stigende ({rel:+.0%} mod 4 uger før)"
    if rel < -0.15:
        return "trending_down", "#1F7A8C", f"faldende ({rel:+.0%} mod 4 uger før)"
    return "trending_flat", "#6B7C8A", f"stabil ({rel:+.0%} mod 4 uger før)"
