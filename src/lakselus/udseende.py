"""Udseende til Streamlit-siden: farver, CSS og hero-illustration (fjeld, fjord og springende laks)."""

import re

FARVER = {
    "laks": "#D9643A",
    "rav": "#E9A23B",
    "fjord": "#2F4B6E",
    "lyng": "#7A5C8E",
    "graa": "#8C7F78",
    "creme": "#FBF4EA",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;600&display=swap');
html, body, [class*="css"], .stMarkdown, p, li, td, th, label { font-family: 'Inter', sans-serif; }
h1, h2, h3, .hero-titel { font-family: 'Fraunces', serif !important; letter-spacing: -0.01em; }
.block-container { padding-top: 1.2rem; max-width: 1150px; }
header[data-testid="stHeader"] { background: transparent; }

.hero { position: relative; border-radius: 22px; overflow: hidden;
        box-shadow: 0 18px 40px -18px rgba(90, 40, 20, .45); margin-bottom: 1.6rem; }
.hero svg { display: block; width: 100%; height: auto; }
.hero-tekst { position: absolute; left: 4%; top: 9%; color: #FFF8EE; max-width: 60%;
              text-shadow: 0 2px 14px rgba(60, 20, 30, .45); }
.hero-titel { font-size: clamp(2rem, 5vw, 3.6rem) !important; font-weight: 700; line-height: 1.02; margin: 0; }
.hero-under { font-size: clamp(.9rem, 1.6vw, 1.15rem) !important; margin-top: .7rem; opacity: .95; max-width: 30em; }

.laks-hop  { animation: hop 5.5s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
.laks-hop2 { animation: hop 7s ease-in-out 2.4s infinite; transform-box: fill-box; transform-origin: center; }
@keyframes hop {
  0%   { transform: translate(0px, 70px) rotate(-38deg); opacity: 0; }
  12%  { opacity: 1; }
  50%  { transform: translate(85px, -25px) rotate(0deg); }
  88%  { opacity: 1; }
  100% { transform: translate(170px, 70px) rotate(38deg); opacity: 0; }
}
.plask  { animation: plask 5.5s ease-out infinite; transform-box: fill-box; transform-origin: center; }
.plask2 { animation: plask 7s ease-out 2.4s infinite; transform-box: fill-box; transform-origin: center; }
@keyframes plask {
  0%, 8% { transform: scale(.2); opacity: .9; }
  30%    { transform: scale(1.4); opacity: 0; }
  100%   { opacity: 0; }
}
.glimt { animation: glimt 4s ease-in-out infinite alternate; }
@keyframes glimt { from { opacity: .25; } to { opacity: .7; } }
@media (prefers-reduced-motion: reduce) {
  .laks-hop, .laks-hop2, .plask, .plask2, .glimt { animation: none; }
}

.kort { background: #FFFBF5; border: 1px solid #EAD7BF; border-radius: 16px; padding: 1rem 1.1rem;
        box-shadow: 0 6px 18px -12px rgba(120, 60, 20, .35); height: 100%; }
.kort .etiket { font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; color: #8C7F78; }
.kort .tal { font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 700; color: #2E2633; line-height: 1.15; }
.kort .note { font-size: .82rem; color: #8C7F78; }
.fodnote { font-size: .8rem; color: #8C7F78; border-top: 1px solid #EAD7BF; padding-top: .8rem; margin-top: 2rem; }
</style>
"""

_LAKS = """
<symbol id="laks" viewBox="-30 -22 130 44">
  <path d="M-24,-15 L-6,-1 L-24,14 L-18,0 Z" fill="url(#laksfarve)"/>
  <path d="M-8,0 C10,-17 55,-19 84,-6 C93,-2 94,3 85,7 C55,19 10,16 -8,0 Z" fill="url(#laksfarve)"/>
  <path d="M30,-13 L40,-21 L48,-12 Z" fill="#B9707A"/>
  <path d="M-4,1 C20,9 55,11 84,5" stroke="#F7C9B6" stroke-width="1.4" fill="none" opacity=".8"/>
  <circle cx="76" cy="-2" r="2.3" fill="#2E2633"/>
  <circle cx="25" cy="-8" r="1.3" fill="#5B4A5E"/><circle cx="38" cy="-10" r="1.2" fill="#5B4A5E"/>
  <circle cx="50" cy="-9" r="1.3" fill="#5B4A5E"/><circle cx="31" cy="-3" r="1.1" fill="#5B4A5E"/>
</symbol>
"""

HERO = f"""
<div class="hero">
<svg viewBox="0 0 1200 420" preserveAspectRatio="xMidYMid slice" role="img"
     aria-label="Solnedgang over norske fjelde og en fjord, hvor laks springer">
  <defs>
    <linearGradient id="himmel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5B3F78"/><stop offset=".38" stop-color="#C8566A"/>
      <stop offset=".7" stop-color="#F09A52"/><stop offset="1" stop-color="#FCD38B"/>
    </linearGradient>
    <linearGradient id="vand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#E88E5A"/><stop offset=".25" stop-color="#9C5C70"/>
      <stop offset="1" stop-color="#2F3557"/>
    </linearGradient>
    <linearGradient id="laksfarve" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#6E7C93"/><stop offset=".45" stop-color="#D9DEE6"/>
      <stop offset="1" stop-color="#F2B8A2"/>
    </linearGradient>
    <radialGradient id="sol" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#FFF4D2"/><stop offset=".55" stop-color="#FFD58A"/>
      <stop offset="1" stop-color="#FFB86B" stop-opacity="0"/>
    </radialGradient>
    {_LAKS}
  </defs>

  <rect width="1200" height="420" fill="url(#himmel)"/>
  <circle cx="820" cy="250" r="150" fill="url(#sol)"/>
  <circle cx="820" cy="250" r="58" fill="#FFF1C9"/>

  <!-- fjerne fjelde -->
  <path d="M0,250 L90,190 L170,225 L260,150 L340,205 L430,170 L520,215 L600,160 L690,210 L770,185
           L860,230 L950,165 L1040,205 L1120,175 L1200,215 L1200,290 L0,290 Z" fill="#B0607A" opacity=".55"/>
  <!-- mellemste fjelde med sne -->
  <path d="M0,290 L120,175 L210,240 L330,120 L440,250 L520,200 L600,265 L1200,265 L1200,300 L0,300 Z" fill="#7A4A6E"/>
  <path d="M300,148 L330,120 L362,152 L345,146 L330,158 L316,146 Z" fill="#F7DCD0" opacity=".85"/>
  <path d="M100,193 L120,175 L142,196 L128,192 L118,200 Z" fill="#F7DCD0" opacity=".75"/>
  <!-- nære fjelde højre -->
  <path d="M640,300 L760,215 L840,262 L960,140 L1060,230 L1120,200 L1200,245 L1200,300 Z" fill="#4E3A62"/>
  <path d="M930,168 L960,140 L992,172 L974,166 L960,178 L946,166 Z" fill="#F7DCD0" opacity=".85"/>
  <!-- forreste skrænt venstre -->
  <path d="M0,300 L0,205 L60,230 L150,262 L240,290 L300,300 Z" fill="#3A2C4E"/>

  <!-- fjord -->
  <rect y="298" width="1200" height="122" fill="url(#vand)"/>
  <g class="glimt" fill="#FFE2A8">
    <rect x="770" y="306" width="100" height="3" rx="1.5"/><rect x="745" y="318" width="150" height="3" rx="1.5"/>
    <rect x="785" y="332" width="70" height="2.5" rx="1.2"/><rect x="760" y="348" width="120" height="2.5" rx="1.2"/>
    <rect x="800" y="366" width="45" height="2" rx="1"/>
  </g>

  <!-- springende laks -->
  <g transform="translate(470,300)">
    <ellipse class="plask" cx="10" cy="4" rx="34" ry="6" fill="none" stroke="#FFE9C9" stroke-width="2"/>
    <g class="laks-hop"><use href="#laks" x="-25" y="-90" width="120" height="42"/></g>
    <ellipse class="plask" cx="180" cy="4" rx="34" ry="6" fill="none" stroke="#FFE9C9" stroke-width="2" style="animation-delay:4.4s"/>
  </g>
  <g transform="translate(1000,330) scale(.6)">
    <ellipse class="plask2" cx="10" cy="4" rx="34" ry="6" fill="none" stroke="#FFE9C9" stroke-width="2.5"/>
    <g class="laks-hop2"><use href="#laks" x="-25" y="-90" width="120" height="42"/></g>
  </g>
</svg>
<div class="hero-tekst">
  <div class="hero-titel">Lakselus langs<br>norskekysten</div>
  <div class="hero-under">Ugentlige lusetal fra norske havbrug – og et ærligt forsøg på at se 1–4 uger frem.</div>
</div>
</div>
"""


# Streamlit-markdown afbryder HTML ved tomme linjer, så HERO pakkes til én blok uden kommentarer.
HERO = "\n".join(
    linje for linje in re.sub(r"<!--.*?-->", "", HERO).splitlines() if linje.strip()
)


def kort(etiket: str, tal: str, note: str = "") -> str:
    return f'<div class="kort"><div class="etiket">{etiket}</div><div class="tal">{tal}</div><div class="note">{note}</div></div>'
