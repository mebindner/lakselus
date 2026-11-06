"""Lakselusens livscyklus som illustration til siden Havstrømme (engelsk UI).

Fire trin fra larve i vandet til den voksne hunlus, der tælles mod grænsen, med ugens egne tal sat ind:
vandets fart ved anlæggene, de tre talte stadier (fastsiddende, bevægelige, voksne hunlus) og havtemperaturen.
Pointen er, at de unge lus i dag er de voksne hunlus om nogle uger.

Fakta (varigheder og stadier) er fra Marine Institute (Irland), "Life cycle of the Salmon Louse", og
Hamre m.fl. 2013, PLOS ONE 8(9): e73539 (to chalimus-stadier). Lusene er tegnet stiliseret i SVG.

Indhold
1. Tegninger – larver, fastsiddende lus, bevægelig lus og voksen hunlus med æggestrenge
2. HTML      – de fire trin, fodnoten og stilarket
"""

import math

from lakselus.udseende import FARVER, LUS_FARVER, lus_niveau

BLAEK, SKIFER, TAAGE, LINJE = FARVER["blaek"], FARVER["skifer"], FARVER["taage"], FARVER["linje"]
VAND, VAND_LYS = "#5B92BA", "#EAF2F8"

# --- 1. Tegninger ---------------------------------------------------------------------------------
# Alle tegninger bruger viewBox 0 0 160 110. Trin 2–4 ses ovenfra på laksens skællede hud; trin 1 er i vandet.
# Lusene er bygget af samme krop: skjold (cephalothorax) med to lunuler foran, kønssegment og en kort bagkrop.

DEFS = (
    "<defs>"
    '<radialGradient id="lc-krop" cx=".45" cy=".3" r=".8"><stop offset="0" stop-color="#3C6A88"/>'
    f'<stop offset=".55" stop-color="#1A3F57"/><stop offset="1" stop-color="{BLAEK}"/></radialGradient>'
    '<linearGradient id="lc-hud" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E3EAF0"/>'
    '<stop offset=".5" stop-color="#F7F9FB"/><stop offset="1" stop-color="#D9E3EA"/></linearGradient>'
    '<linearGradient id="lc-vand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EEF5FA"/>'
    '<stop offset="1" stop-color="#CFE0EC"/></linearGradient>'
    '<pattern id="lc-skael" width="16" height="12" patternUnits="userSpaceOnUse">'
    '<path d="M0 12 a8 7 0 0 1 16 0M-8 6 a8 7 0 0 1 16 0M8 6 a8 7 0 0 1 16 0" fill="none" stroke="#BFCCD6" stroke-width=".8"/></pattern>'
    '<filter id="lc-skygge" x="-30%" y="-30%" width="160%" height="160%">'
    '<feDropShadow dx="0" dy="1.6" stdDeviation="1.6" flood-color="#0B2230" flood-opacity=".28"/></filter>'
    '<linearGradient id="lc-hav" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F2F8FC"/>'
    '<stop offset=".6" stop-color="#D7E7F2"/><stop offset="1" stop-color="#B9D1E2"/></linearGradient>'
    '<linearGradient id="lc-laks" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3F6079"/>'
    '<stop offset=".38" stop-color="#8FA9BB"/><stop offset=".55" stop-color="#D6E1E9"/><stop offset="1" stop-color="#F7F9FB"/></linearGradient>'
    "</defs>"
)
HUD = '<rect width="160" height="110" fill="url(#lc-hud)"/><rect width="160" height="110" fill="url(#lc-skael)" opacity=".9"/>'
LYS = 'fill="#FFFFFF" fill-opacity=".22"'


def _skjold(s: float = 1.0) -> str:
    """Skjoldet med lunuler, øjne og en svag ryglinje – fælles for alle stadier på fisken."""
    return (f'<g transform="scale({s})">'
            '<path d="M0 -24C10 -24 16 -21 19 -14C22 -7 22 4 19 10L14 13C10 10 6 10 4 12L-4 12C-6 10 -10 10 -14 13'
            'L-19 10C-22 4 -22 -7 -19 -14C-16 -21 -10 -24 0 -24Z" fill="url(#lc-krop)"/>'
            f'<circle cx="-6" cy="-20.5" r="1.7" {LYS}/><circle cx="6" cy="-20.5" r="1.7" {LYS}/>'
            f'<circle cx="0" cy="-12" r="1.3" {LYS}/>'
            '<path d="M-8 -17C-11 -8 -11 2 -7 9M8 -17C11 -8 11 2 7 9" fill="none" stroke="#FFFFFF" stroke-opacity=".14" stroke-width="1"/>'
            # Svømmeben, der stikker ud under skjoldets bagkant
            f'<path d="M-18 8l-6 4M-15 11l-5 6M18 8l6 4M15 11l5 6" stroke="{BLAEK}" stroke-width="1.5" stroke-linecap="round"/>'
            "</g>")


def _aeggestreng(x0: float, y0: float, retning: int, n: int = 11) -> str:
    """En æggestreng som en række perler, der svinger let ud til siden."""
    perler = []
    for i in range(n):
        t = i / (n - 1)
        x = x0 + retning * (t * 13 + 2 * math.sin(t * math.pi))
        y = y0 + i * 4.7
        perler.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.3" fill="#EEF2F5" stroke="{BLAEK}" stroke-width=".9"/>')
    return "".join(perler)


def larver() -> str:
    # Vandet med strømlinjer, larver der driver mod højre (animeret i CSS) og en laks som mål.
    linjer = "".join(f'<path d="M-10 {y} C30 {y - 8} 60 {y + 8} 100 {y} S150 {y - 8} 175 {y}" fill="none" '
                     f'stroke="{VAND}" stroke-opacity=".4" stroke-width="1.1" stroke-dasharray="2 5"/>' for y in (22, 50, 78, 100))
    # Nauplius: dråbeformet med tre par fjerede lemmer. Copepodit: aflang krop, tynd bagkrop og antenner.
    naup = (f'<ellipse rx="4.6" ry="3.4" fill="url(#lc-krop)"/>'
            f'<path d="M-3 -2.5l-4 -4M-4 0l-5 -1M-3 2.5l-4 4M3 -2.5l4 -4M4 0l5 -1M3 2.5l4 4" stroke="{BLAEK}" stroke-width=".8" stroke-linecap="round"/>')
    cope = (f'<g transform="rotate(-8)"><ellipse cx="2" rx="7" ry="3.6" fill="url(#lc-krop)"/>'
            f'<path d="M-5 0h-7" stroke="{BLAEK}" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="M8 -1.5q5 -5 8 -3M8 1.5q5 5 8 3" fill="none" stroke="{BLAEK}" stroke-width=".9" stroke-linecap="round"/></g>')
    drivere = "".join(f'<g class="lc-drift" style="animation-delay:{f}s"><g transform="translate({x} {y}) scale({k})">{form}</g></g>'
                      for x, y, form, f, k in ((20, 34, naup, 0, 1), (58, 66, cope, -2.4, 1.1), (96, 30, naup, -4.6, .9),
                                               (30, 92, cope, -6.1, .9), (84, 88, naup, -1.5, .8), (108, 58, cope, -3.3, 1.2)))
    laks = ('<g opacity=".9"><path d="M171 58C160 46 142 44 128 54C123 58 123 62 128 66C142 76 160 74 171 62Z" fill="#9FB4C4"/>'
            '<path d="M128 54C134 58 134 62 128 66" fill="none" stroke="#7F98AB" stroke-width="1"/>'
            '<circle cx="132" cy="58" r="1.4" fill="#0B2230"/><path d="M146 50l6 -6 2 7Z" fill="#8CA3B5"/></g>')
    return f'<rect width="160" height="110" fill="url(#lc-vand)"/>{linjer}{laks}{drivere}'


def fastsiddende() -> str:
    # Chalimus 1 og 2: aflange, fæstnet til huden med en tråd (frontalfilament) – anker og tråd vises tydeligt.
    def chalimus(x: float, y: float, s: float, vinkel: float) -> str:
        return (f'<g transform="translate({x} {y}) rotate({vinkel}) scale({s})">'
                f'<circle cx="0" cy="-30" r="1.8" fill="{BLAEK}"/><path d="M0 -30C2 -25 -2 -21 0 -16" fill="none" stroke="{BLAEK}" stroke-width="1"/>'
                '<ellipse cx="0" cy="-5" rx="9" ry="12" fill="url(#lc-krop)" filter="url(#lc-skygge)"/>'
                f'<circle cx="0" cy="-11" r="1.1" {LYS}/>'
                '<ellipse cx="0" cy="11" rx="4.5" ry="6" fill="url(#lc-krop)"/><rect x="-1.6" y="16" width="3.2" height="5" rx="1.5" fill="#1A3F57"/>'
                f'<path d="M-8 -2l-5 3M-8 3l-4 4M8 -2l5 3M8 3l4 4" stroke="{BLAEK}" stroke-width="1.2" stroke-linecap="round"/></g>')
    return HUD + chalimus(52, 62, .8, -14) + chalimus(104, 58, 1.15, 10)


def bevaegelig() -> str:
    # Preadult og voksen han: fri på huden. En stiplet bane viser, at den flytter sig.
    return (HUD + '<path d="M22 100C40 88 46 96 62 84S80 72 84 68" fill="none" stroke="#8FA4B4" stroke-width="1.2" stroke-dasharray="2 4"/>'
            '<g transform="translate(96 56) rotate(24)" filter="url(#lc-skygge)">' + _skjold(1.25)
            + '<ellipse cx="0" cy="19" rx="6" ry="7.5" fill="url(#lc-krop)"/><rect x="-2.2" y="25" width="4.4" height="8" rx="2" fill="#1A3F57"/></g>'
            '<g transform="translate(34 86) rotate(-30)" opacity=".75" filter="url(#lc-skygge)">' + _skjold(.62)
            + '<ellipse cx="0" cy="10" rx="3.5" ry="4.5" fill="url(#lc-krop)"/></g>')


def hunlus() -> str:
    # Voksen hunlus: stort skjold, et stort kønssegment og to lange æggestrenge, der slæber efter.
    return (HUD + '<g transform="translate(80 34)" filter="url(#lc-skygge)">' + _skjold(1.25)
            + '<path d="M-9 17C-14 18 -14 26 -13 34C-12 41 -7 44 0 44C7 44 12 41 13 34C14 26 14 18 9 17Z" fill="url(#lc-krop)"/>'
            
            '<rect x="-3" y="43" width="6" height="9" rx="2.5" fill="#1A3F57"/></g>'
            + _aeggestreng(74, 74, -1) + _aeggestreng(86, 74, 1))


# --- 1b. Scenen ----------------------------------------------------------------------------------
# Én animeret scene over hele bredden: strømmen flyder mod højre, larver klækkes fra hunlusens æggestrenge, driver
# ud i vandet, bliver smittende og svømmer tilbage til laksen. På laksens side sidder de tre talte stadier.
# Animationen er CSS (offset-path og stroke-dashoffset), så den kan slås fra med prefers-reduced-motion.

LARVE_BANE = ("M884 214C940 262 900 316 770 318C590 322 300 330 150 298C40 274 34 176 140 150"
              "C250 124 380 150 500 176")
LAKS = ("M470 176C492 140 562 118 652 114C762 110 862 128 917 160L962 126C956 150 953 172 962 208L917 180"
        "C862 214 762 234 652 232C562 230 494 213 470 176Z")


def _fisk_lus(x: float, y: float, s: float, krop: str) -> str:
    """En lus på laksens side, med hovedet frem mod laksens hoved (venstre)."""
    return f'<g transform="translate({x} {y}) rotate(-90) scale({s})" filter="url(#lc-skygge)">{krop}</g>'


def _maerke(nr: int, x: float, y: float, tx: float, ty: float, titel: str = "", under: str = "", anker: str = "start",
            stor: bool = False) -> str:
    """Nummereret mærke med en tynd linje ind til stedet på scenen og en kort etiket (ingen etiket i den store udgave)."""
    r, skrift, dx = (19, 20, 0) if stor else (11, 13, 14 if anker == "start" else -14)
    etiket = ("" if stor else
              f'<text x="{x + dx}" y="{y - 1}" text-anchor="{anker}" class="lc-et1">{titel}</text>'
              f'<text x="{x + dx}" y="{y + 14}" text-anchor="{anker}" class="lc-et2">{under}</text>')
    return (f'<g class="lc-m lc-m{nr}">'
            f'<line x1="{x}" y1="{y}" x2="{tx}" y2="{ty}" stroke="{BLAEK}" stroke-opacity=".45" stroke-width="{1.6 if stor else 1}"/>'
            f'<circle cx="{tx}" cy="{ty}" r="{4 if stor else 2.5}" fill="{BLAEK}"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFFFFF" stroke="{BLAEK}" stroke-width="1.6"/>'
            f'<text x="{x}" y="{y + skrift * .34:.1f}" text-anchor="middle" class="lc-nr" style="font-size:{skrift}px">{nr}</text>'
            f'{etiket}</g>')


def scene(km_dag: float) -> str:
    straale = "".join(f'<polygon points="{x},0 {x + 46},0 {x - 60},340 {x - 130},340" fill="#FFFFFF" opacity=".22" class="lc-straale" '
                      f'style="animation-delay:{-i * 2.3}s"/>' for i, x in enumerate((170, 420, 690, 930)))
    stroem = "".join(f'<path d="M-20 {y}C150 {y - 14} 300 {y + 14} 480 {y}S800 {y - 14} 1020 {y}" class="lc-stroem" '
                     f'style="animation-duration:{d}s"/>' for y, d in ((48, 7), (96, 9), (262, 8), (300, 6.5), (328, 10)))
    pletter = "".join(f'<path d="M{x - 3} {y - 3}l6 6M{x + 3} {y - 3}l-6 6" stroke="#2D4A5E" stroke-opacity=".4" stroke-width="1.4" stroke-linecap="round"/>'
                      for x, y in ((560, 134), (598, 128), (632, 140), (676, 126), (700, 142), (742, 130), (786, 140),
                                   (812, 132), (850, 144), (588, 150), (760, 152)))
    laks = (f'<path d="{LAKS}" fill="url(#lc-laks)"/>'
            '<path d="M640 116C660 80 692 78 714 113Z" fill="#4C6A80"/><path d="M842 124C852 110 864 110 870 128Z" fill="#4C6A80"/>'
            '<path d="M566 208C580 234 604 242 616 224Z" fill="#8FA6B6"/><path d="M722 230C732 250 750 254 758 232Z" fill="#8FA6B6"/>'
            '<path d="M822 222C834 242 852 244 862 216Z" fill="#8FA6B6"/>'
            f'<path d="M546 140C534 166 538 196 553 215" fill="none" stroke="#5E7A8E" stroke-width="1.6"/>'
            f'<path d="M553 172C650 166 800 166 917 171" fill="none" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="1.2"/>'
            f'<circle cx="506" cy="164" r="6.5" fill="#F4F7F9"/><circle cx="507" cy="164" r="3.8" fill="{BLAEK}"/>'
            '<circle cx="508.5" cy="162.5" r="1.2" fill="#FFFFFF"/>'
            '<path d="M472 178C482 182 494 184 506 183" fill="none" stroke="#5E7A8E" stroke-width="1.2"/>' + pletter)
    chalimus = ('<circle cx="0" cy="-24" r="1.8" fill="#0B2230"/><path d="M0 -24C2 -20 -2 -17 0 -13" fill="none" stroke="#0B2230" stroke-width="1"/>'
                '<ellipse cx="0" cy="-3" rx="8" ry="11" fill="url(#lc-krop)"/><ellipse cx="0" cy="11" rx="4" ry="5.5" fill="url(#lc-krop)"/>')
    mobil = _skjold(1.0) + '<ellipse cx="0" cy="16" rx="5" ry="6.5" fill="url(#lc-krop)"/><rect x="-2" y="21" width="4" height="7" rx="2" fill="#1A3F57"/>'
    hun = (_skjold(1.15) + '<path d="M-9 16C-13 17 -13 25 -12 32C-11 39 -6 41 0 41C6 41 11 39 12 32C13 25 13 17 9 16Z" fill="url(#lc-krop)"/>'
           '<rect x="-3" y="40" width="6" height="8" rx="2.5" fill="#1A3F57"/>'
           + _aeggestreng(-6, 46, -1, 13) + _aeggestreng(6, 46, 1, 13))
    lus = (_fisk_lus(604, 190, 1.0, chalimus) + _fisk_lus(712, 192, .95, mobil) + _fisk_lus(808, 190, .95, hun))
    # Larverne: hver er en nauplius, der skifter til en copepodit halvvejs (to former, der toner over i hinanden).
    naup = (f'<ellipse rx="4.4" ry="3.3" fill="url(#lc-krop)"/>'
            f'<path d="M-3 -2.5l-4 -4M-4 0l-5 -1M-3 2.5l-4 4M3 -2.5l4 -4M4 0l5 -1M3 2.5l4 4" stroke="{BLAEK}" stroke-width=".8" stroke-linecap="round"/>')
    cope = (f'<ellipse cx="2" rx="7" ry="3.4" fill="url(#lc-krop)"/><path d="M-5 0h-7" stroke="{BLAEK}" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="M8 -1.5q5 -5 8 -3M8 1.5q5 5 8 3" fill="none" stroke="{BLAEK}" stroke-width=".9" stroke-linecap="round"/>')
    n = 10
    larver_ = "".join(f'<g class="lc-larve" style="animation-delay:{-i * 18 / n:.2f}s"><g class="lc-n">{naup}</g><g class="lc-c">{cope}</g></g>'
                      for i in range(n))
    maerker = (_maerke(1, 60, 216, 140, 290, "Larvae drift with the current", f"2–14 days · water moved ≈ {km_dag:.0f} km a day")
               + _maerke(2, 560, 66, 600, 180, "Attached", "chalimus, held by a thread")
               + _maerke(3, 712, 44, 712, 172, "Mobile", "pre-adults and adult males")
               + _maerke(4, 690, 278, 828, 214, "Adult female", "egg strings hatch new larvae", "end"))
    # Mobil: beskåret omkring laksen, større mærker og ingen etiketter – trinkortene nedenunder har teksten.
    maerker_m = (_maerke(1, 404, 290, 444, 322, stor=True) + _maerke(2, 560, 62, 600, 180, stor=True)
                 + _maerke(3, 712, 50, 712, 172, stor=True) + _maerke(4, 900, 300, 836, 212, stor=True))
    tekst = ('Animation of the salmon louse life cycle: larvae hatch from the egg strings, drift with the current, '
             'attach to a salmon and grow into adult lice.')
    indhold = (f'<rect width="1000" height="340" fill="url(#lc-hav)"/>{straale}{stroem}'
               f'<g class="lc-svoem">{laks}{lus}</g>{larver_}')
    return (f'<div class="lc-scene lc-scene-d"><svg viewBox="0 0 1000 340" role="img" aria-label="{tekst}">{indhold}{maerker}</svg></div>'
            f'<div class="lc-scene lc-scene-m"><svg viewBox="360 20 640 320" role="img" aria-label="{tekst}">{indhold}{maerker_m}</svg></div>')


# --- 2. HTML --------------------------------------------------------------------------------------

def _trin(nr: int, sted: str, navn: str, stadier: str, tegning: str, tekst: str, tal: str = "") -> str:
    return (f'<div class="lc-trin"><div class="lc-sted">{nr:02d} · {sted}</div>'
            f'<svg viewBox="0 0 160 110" role="img" aria-label="{navn}">{tegning}</svg>'
            f'<div class="lc-navn">{navn}</div><div class="lc-stadier">{stadier}</div>'
            f'<div class="lc-tekst">{tekst}</div>{tal}</div>')


def _tal(v: float, hvad: str, farve: str = BLAEK) -> str:
    return f'<div class="lc-tal"><b style="color:{farve}">{v:.2f}</b> {hvad}</div>'


CSS = f"""<style>
.lc {{ margin: 2.6rem 0 2.2rem; }}
.lc .lc-over {{ font-size: .72rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; color: {SKIFER}; }}
.lc h3 {{ font-size: 1.45rem !important; margin: .35rem 0 .3rem !important; padding: 0 !important; }}
.lc .lc-intro {{ color: #4A5A66; max-width: 52em; margin: 0 0 1rem; line-height: 1.55; }}
.lc-raekke {{ display: grid; grid-template-columns: repeat(4, 1fr); border-top: 1px solid {BLAEK}; border-bottom: 1px solid {LINJE}; }}
.lc-trin {{ position: relative; padding: 1rem 1.1rem 1.1rem; }}
.lc-trin + .lc-trin {{ border-left: 1px solid {LINJE}; }}
.lc-trin + .lc-trin::before {{ content: "→"; position: absolute; left: -.6rem; top: 5.2rem; width: 1.2rem; height: 1.2rem;
  line-height: 1.15rem; text-align: center; font-size: .8rem; color: {SKIFER}; background: #fff; border: 1px solid {LINJE}; border-radius: 50%; }}
.lc-trin svg {{ display: block; width: 100%; height: auto; border-radius: 6px; margin: .55rem 0 .7rem; background: #fff; box-shadow: inset 0 0 0 1px {LINJE}; }}
.lc-sted {{ font-family: 'Source Serif 4', serif; font-size: .85rem; font-weight: 600; color: {SKIFER}; }}
.lc-navn {{ font-family: 'Source Serif 4', serif; font-size: 1.15rem; font-weight: 600; color: {BLAEK}; line-height: 1.2; }}
.lc-stadier {{ font-size: .78rem; color: {SKIFER}; margin: .15rem 0 .45rem; }}
.lc-tekst {{ font-size: .88rem; color: #2A3A46; line-height: 1.5; }}
.lc-tal {{ margin-top: .6rem; font-size: .82rem; color: {SKIFER}; }}
.lc-tal b {{ font-family: 'Source Serif 4', serif; font-size: 1.35rem; font-weight: 600; margin-right: .15rem; }}
.lc-bund {{ display: flex; gap: .6rem; align-items: flex-start; margin-top: .9rem; font-size: .9rem; color: #2A3A46; line-height: 1.5; max-width: 60em; }}
.lc-bund .ikon {{ color: {VAND}; font-size: 1.25rem; }}
.lc-kilde {{ margin-top: .5rem; font-size: .75rem; color: {SKIFER}; }}
.lc-scene {{ margin: .2rem 0 1.2rem; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 0 {LINJE}, 0 10px 30px rgba(11,34,48,.08); }}
.lc-scene svg {{ display: block; width: 100%; height: auto; }}
.lc-nr {{ font: 600 13px Inter, sans-serif; fill: {BLAEK}; }}
.lc-et1 {{ font: 600 15px 'Source Serif 4', serif; fill: {BLAEK}; }}
.lc-et2 {{ font: 500 11.5px Inter, sans-serif; fill: #3A4C59; }}
.lc-stroem {{ fill: none; stroke: #FFFFFF; stroke-opacity: .75; stroke-width: 1.3; stroke-dasharray: 3 16; animation: lc-flyd 8s linear infinite; }}
@keyframes lc-flyd {{ to {{ stroke-dashoffset: -190; }} }}
.lc-straale {{ animation: lc-lys 9s ease-in-out infinite; }}
@keyframes lc-lys {{ 0%, 100% {{ opacity: .1; }} 50% {{ opacity: .3; }} }}
.lc-svoem {{ animation: lc-svoem 6s ease-in-out infinite; }}
@keyframes lc-svoem {{ 0%, 100% {{ transform: translate(0, 0); }} 50% {{ transform: translate(-3px, -4px); }} }}
.lc-larve {{ offset-path: path("{LARVE_BANE}"); offset-rotate: auto; animation: lc-rejse 18s linear infinite; opacity: 0; }}
@keyframes lc-rejse {{ 0% {{ offset-distance: 0%; opacity: 0; transform: scale(.6); }} 6% {{ opacity: 1; }}
  60% {{ transform: scale(1); }} 90% {{ opacity: 1; transform: scale(1.15); }} 100% {{ offset-distance: 100%; opacity: 0; transform: scale(.9); }} }}
.lc-n {{ animation: lc-ud 18s linear infinite; animation-delay: inherit; }}
.lc-c {{ animation: lc-ind 18s linear infinite; animation-delay: inherit; opacity: 0; }}
@keyframes lc-ud {{ 0%, 38% {{ opacity: 1; }} 48%, 100% {{ opacity: 0; }} }}
@keyframes lc-ind {{ 0%, 38% {{ opacity: 0; }} 48%, 100% {{ opacity: 1; }} }}
.lc-scene-m {{ display: none; }}
@media (max-width: 640px) {{ .lc-scene-d {{ display: none; }} .lc-scene-m {{ display: block; }} }}
/* Mærkerne kommer frem ét ad gangen, mens scenen rulles ind (scroll-drevet animation, kun CSS). Browsere uden
   understøttelse viser dem bare med det samme. */
@supports (animation-timeline: view()) {{
  .lc-scene {{ view-timeline: --lc-scene block; }}
  .lc-m {{ animation: lc-frem linear both; animation-timeline: --lc-scene; }}
  .lc-m1 {{ animation-range: cover 12% cover 26%; }} .lc-m2 {{ animation-range: cover 18% cover 32%; }}
  .lc-m3 {{ animation-range: cover 24% cover 38%; }} .lc-m4 {{ animation-range: cover 30% cover 44%; }}
}}
@keyframes lc-frem {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
@media (prefers-reduced-motion: reduce) {{ .lc-stroem, .lc-straale, .lc-svoem, .lc-n, .lc-c, .lc-m {{ animation: none; }}
  .lc-larve {{ animation: none; opacity: 1; offset-distance: 55%; }} .lc-c {{ opacity: 1; }} .lc-n {{ opacity: 0; }} }}
.lc-drift {{ animation: lc-driv 9s linear infinite; }}
@keyframes lc-driv {{ 0% {{ transform: translate(-18px, 0); opacity: 0; }} 12% {{ opacity: 1; }} 50% {{ transform: translate(4px, -3px); }}
  88% {{ opacity: 1; }} 100% {{ transform: translate(26px, 0); opacity: 0; }} }}
@media (max-width: 900px) {{ .lc-raekke {{ grid-template-columns: repeat(2, 1fr); }}
  .lc-trin:nth-child(3) {{ border-left: 0; }} .lc-trin:nth-child(n+3) {{ border-top: 1px solid {LINJE}; }}
  .lc-trin:nth-child(3)::before {{ display: none; }} }}
@media (max-width: 560px) {{ .lc-raekke {{ grid-template-columns: 1fr; }} .lc-trin + .lc-trin {{ border-left: 0; border-top: 1px solid {LINJE}; }}
  .lc-trin + .lc-trin::before {{ content: "↓"; left: 50%; top: -.6rem; margin-left: -.6rem; display: block; }}
  .lc-trin svg {{ max-width: 320px; }} }}
@media (prefers-reduced-motion: reduce) {{ .lc-drift {{ animation: none; }} }}
</style>"""


def html(uge: int, km_dag: float, fast: float, mob: float, hun: float, temp: float, graense: float = 0.5) -> str:
    """Hele illustrationen. Tallene er fra samme uge som strømmene: vandets fart (km/døgn), gennemsnit pr. fisk af de
    tre talte stadier og havtemperaturen ved anlæggene."""
    # Fem døgn i vandet – midt i intervallet 2–14 døgn. Regnet på det afrundede tal, så teksten går op.
    drift = 5 * round(km_dag)
    trin = [
        _trin(1, "In the water", "Larvae drift with the current", "Nauplius 1–2 · copepodid", larver(),
              "Larvae hatch from the egg strings and drift for days. They cannot feed, so they live on fat reserves "
              f"until they reach the infective stage – 2 to 14 days, depending on temperature. Five days at week {uge}'s "
              f"{km_dag:.0f} km a day is about {drift:.0f} km – far enough to reach other farms."),
        _trin(2, "On the salmon", "Attached", "Chalimus 1–2", fastsiddende(),
              "The infective larva finds a salmon and fastens itself to the skin with a thread. "
              "Counted as <i>attached lice</i>.", _tal(fast, f"per fish in week {uge}")),
        _trin(3, "On the salmon", "Mobile", "Pre-adult 1–2 · adult males", bevaegelig(),
              "Free of the thread, the louse moves over the fish and grazes on skin and mucus. "
              "Counted as <i>mobile lice</i>.", _tal(mob, f"per fish in week {uge}")),
        _trin(4, "On the salmon", "Adult female", "With egg strings", hunlus(),
              f"The only stage the lice limit applies to: {graense:.1f} adult females per fish (0.2 in the spring weeks). "
              "Her egg strings "
              "hatch new larvae, and the cycle starts again.", _tal(hun, f"per fish in week {uge}", LUS_FARVER[lus_niveau(hun)])),
    ]
    # Alle forløb og mønstre står én gang i en usynlig SVG, som alle tegningerne henviser til. De må ikke ligge inde
    # i en scene, der er skjult med display: none (desktop- eller mobiludgaven), for så tegnes de ikke.
    faelles = f'<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">{DEFS}</svg>'
    return (CSS + '<div class="lc">' + faelles + '<div class="lc-over">Why the currents matter</div>'
            "<h3>From drifting larva to the lice that are counted</h3>"
            '<p class="lc-intro">A salmon louse spends its first days as a larva in the water and the rest of its life on a fish. '
            "Farms count three of the stages on the salmon every week – the numbers below are the average per fish "
            f"across the farms that counted in week {uge}, the same week as the currents.</p>" + scene(km_dag) +
            f'<div class="lc-raekke">{"".join(trin)}</div>'
            f'<div class="lc-bund"><span class="ikon" aria-hidden="true">thermostat</span><div>One generation takes about '
            f"8–9 weeks at 6 °C, 6 weeks at 9 °C and 4 weeks at 18 °C. The farms measured the sea at about {temp:.0f} °C in week {uge}. "
            "<b>The attached and mobile lice counted now are the adult females of the coming weeks</b> – which is why the young stages "
            "help forecast the level ahead.</div></div>"
            '<div class="lc-kilde">Life cycle: Marine Institute (Ireland), <i>Life cycle of the salmon louse</i>; Hamre et al. (2013), '
            "PLOS ONE 8(9): e73539. Lice counts and sea temperature: BarentsWatch / Mattilsynet (NLOD). Drawings are stylised.</div></div>")
