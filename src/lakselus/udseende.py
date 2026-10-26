"""Designsystem i konsulentstil.

Hvid flade, dyb havblå tekst, én laksefarvet accent. Serif-handlingstitler (konklusionen står i titlen),
nummererede figurer med enhed og kildeangivelse, minimalistiske tabeller og små multipler.
"""

import altair as alt
import pandas as pd

FARVER = {
    "blaek": "#0B2230",      # dyb havblå – titler, primære dataserier
    "hav": "#1D4E6B",        # sekundær blå
    "skifer": "#5B6B78",     # brødtekst, akser
    "taage": "#AEBBC5",      # sekundære dataserier, bånd
    "linje": "#E1E6EA",      # kanter og gitter
    "flade": "#FFFFFF",
    "baggrund": "#FFFFFF",
    "laks": "#E8603C",       # eneste accent
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

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

html, body, [class*="css"], .stMarkdown, p, li, td, th, label, button, input { font-family: Inter, sans-serif; }
.stMarkdown p, .stMarkdown li { color: #2A3A46; }
h1, h2, h3 { font-family: 'Source Serif 4', Georgia, serif !important; font-weight: 600 !important; color: #0B2230; letter-spacing: -0.01em; }
.block-container { padding-top: 3.4rem; max-width: 1160px; }
header[data-testid="stHeader"] { background: rgba(255,255,255,.94); backdrop-filter: blur(8px); border-bottom: 1px solid #E1E6EA; }
[data-testid="stCaptionContainer"] { color: #6B7A86; }
hr { border-color: #E1E6EA; }

.ikon { font-family: 'Material Symbols Outlined'; font-weight: normal; font-style: normal; line-height: 1;
        display: inline-block; vertical-align: -0.2em; font-size: 1.15em; -webkit-font-smoothing: antialiased; }

/* Forside / sidehoved */
.sidehoved { border-top: 6px solid #0B2230; padding: 1.3rem 0 1.2rem; margin-bottom: 1.6rem; border-bottom: 1px solid #E1E6EA; }
.sidehoved .overlinje { font-size: .72rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; color: #E8603C; }
.sidehoved h1 { font-size: clamp(1.7rem, 3.4vw, 2.5rem) !important; line-height: 1.15; margin: .5rem 0 .6rem; padding: 0; max-width: 24em; }
.sidehoved .under { color: #4A5A66; font-size: 1rem; max-width: 52em; margin: 0; line-height: 1.55; }
.sidehoved .chips { display: flex; gap: 1.4rem; flex-wrap: wrap; margin-top: 1rem; }
.chip { display: inline-flex; align-items: center; gap: .35rem; font-size: .78rem; color: #5B6B78; }

/* Executive summary */
.resume { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; border-top: 1px solid #0B2230; border-bottom: 1px solid #E1E6EA; margin: .4rem 0 2rem; }
.resume > div { padding: 1rem 1.2rem 1.1rem 0; }
.resume > div + div { padding-left: 1.2rem; border-left: 1px solid #E1E6EA; }
.resume .nr { font-family: 'Source Serif 4', serif; font-size: .9rem; color: #E8603C; font-weight: 600; }
.resume .stor { font-family: 'Source Serif 4', serif; font-size: 2.3rem; font-weight: 600; color: #0B2230; line-height: 1.05;
                margin: .3rem 0 .35rem; font-variant-numeric: tabular-nums; }
.resume .tekst { font-size: .9rem; color: #2A3A46; line-height: 1.45; }
@media (max-width: 760px) { .resume { grid-template-columns: 1fr; } .resume > div + div { padding-left: 0; border-left: 0; border-top: 1px solid #E1E6EA; } }

/* Figurer */
.figur { margin: 2.2rem 0 .5rem; }
.figur .label { font-size: .72rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: #E8603C; }
.figur .titel { font-family: 'Source Serif 4', serif; font-size: 1.35rem; font-weight: 600; color: #0B2230; line-height: 1.25; margin: .25rem 0 .2rem; }
.figur .undertitel { font-size: .85rem; color: #5B6B78; }
.kilde { font-size: .74rem; color: #6B7A86; border-top: 1px solid #E1E6EA; padding-top: .4rem; margin-top: .3rem; }

/* Tabel */
table.tabel { width: 100%; border-collapse: collapse; font-size: .84rem; font-variant-numeric: tabular-nums; }
.tabel th { text-align: left; font-size: .68rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #6B7A86;
            border-bottom: 1px solid #0B2230; padding: .45rem .5rem; white-space: nowrap; }
.tabel td { border-bottom: 1px solid #EDF1F4; padding: .42rem .5rem; color: #1B2B36; vertical-align: middle; }
.tabel td.tal, .tabel th.tal { text-align: right; white-space: nowrap; }
.tabel tr:hover td { background: #F6F8FA; }
.tabel .navn { font-weight: 500; }
.tabel .po { color: #6B7A86; width: 2.2rem; }
.tabel .minibar { display: inline-block; height: 6px; border-radius: 1px; vertical-align: middle; margin-left: .45rem; }
/* Brede tabeller og små multipler scrolles vandret på mobil i stedet for at blive skåret af */
[data-testid="stMarkdownContainer"]:has(table.tabel), [data-testid="stFullScreenFrame"]:has([data-testid="stVegaLiteChart"]) { overflow-x: auto; }
.prik { width: .6rem; height: .6rem; border-radius: 50%; display: inline-block; vertical-align: .05em; margin-right: .35rem; }

/* Nøgletal (bruges på andre sider) */
.kort { background: #FFFFFF; border-top: 1px solid #0B2230; padding: .8rem 0 .4rem; height: 100%; }
.kort .hoved { display: flex; align-items: center; gap: .4rem; color: #5B6B78; }
.kort .etiket { font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .1em; }
.kort .tal { font-family: 'Source Serif 4', serif; font-size: 2rem; font-weight: 600; color: #0B2230; line-height: 1.1; margin-top: .3rem; font-variant-numeric: tabular-nums; }
.kort .note { font-size: .8rem; color: #6B7A86; margin-top: .15rem; }
.kort .bar { height: 3px; background: #EDF1F4; margin-top: .55rem; }
.kort .bar i { display: block; height: 100%; }

.forklaring { display: flex; flex-wrap: wrap; gap: .35rem 1.2rem; font-size: .78rem; color: #5B6B78; margin: .5rem 0 .6rem; }
.forklaring span { display: inline-flex; align-items: center; gap: .1rem; }
.metode { font-size: .8rem; color: #4A5A66; line-height: 1.55; background: #F6F8FA; padding: 1rem 1.2rem; border-left: 3px solid #0B2230; margin-top: 2.4rem; }
.fodnote { font-size: .74rem; color: #6B7A86; border-top: 1px solid #E1E6EA; padding-top: .8rem; margin-top: 2rem; }
.fodnote a { color: #1D4E6B; }
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


def resume(punkter: list[tuple[str, str]]) -> str:
    """Executive summary: [(stort tal, forklarende tekst), ...]."""
    felter = "".join(
        f'<div><div class="nr">{i:02d}</div><div class="stor">{stor}</div><div class="tekst">{tekst}</div></div>'
        for i, (stor, tekst) in enumerate(punkter, 1)
    )
    return f'<div class="resume">{felter}</div>'


def figur(nr: int, titel: str, undertitel: str) -> str:
    return (f'<div class="figur"><div class="label">Exhibit {nr}</div>'
            f'<div class="titel">{titel}</div><div class="undertitel">{undertitel}</div></div>')


def kilde(tekst: str = "") -> str:
    return f'<div class="kilde">Source: BarentsWatch / Mattilsynet (NLOD); own analysis.{" " + tekst if tekst else ""}</div>'


def kort(etiket: str, tal: str, note: str = "", ikon_navn: str = "", bar: tuple[float, str] | None = None) -> str:
    hoved = f'<div class="hoved">{ikon(ikon_navn) if ikon_navn else ""}<span class="etiket">{etiket}</span></div>'
    bjaelke = f'<div class="bar"><i style="width:{min(bar[0], 1):.0%};background:{bar[1]}"></i></div>' if bar else ""
    return f'<div class="kort">{hoved}<div class="tal">{tal}</div><div class="note">{note}</div>{bjaelke}</div>'


def lus_niveau(v: float) -> str:
    return "lav" if v < 0.2 else ("mellem" if v <= 0.5 else "hoej")


def trend(nu: float, foer: float) -> tuple[str, str, str]:
    """Ikon, farve og tekst for udviklingen siden de 4 foregående uger."""
    if pd.isna(foer) or foer == 0:
        return "trending_flat", "#6B7A86", "no comparison"
    rel = nu / foer - 1
    if rel > 0.15:
        return "trending_up", "#D64545", f"rising ({rel:+.0%} vs. previous 4 weeks)"
    if rel < -0.15:
        return "trending_down", "#1F7A8C", f"falling ({rel:+.0%} vs. previous 4 weeks)"
    return "trending_flat", "#6B7A86", f"stable ({rel:+.0%} vs. previous 4 weeks)"


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
