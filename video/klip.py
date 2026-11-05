"""Klipper rundturen i appen: 1080x1350, 30 fps, ca. 45 sek. Appen står i vinduet fra første billede.

Optagelsen (frames4/ + log4.json fra optag.py) vises i et browservindue. Et "kamera" glider og zoomer mod det,
der sker; musen tegnes ovenpå med klik-ringe; teksterne animeres ind ord for ord. Hvert billede tegnes som HTML
og fotograferes, og ffmpeg samler billederne til mp4.
"""

import bisect
import json
import math
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

MAPPE = Path(__file__).parent
UD = MAPPE / "ud4"
FPS = 30
L = json.loads((MAPPE / "log4.json").read_text())
TS, M = L["billeder"], L["mark"]
MUS = L["mus"]
KLIK = L["klik"]
LOGO = (MAPPE.parent / "assets" / "logo.svg").read_text()
MAERKE = LOGO.split("<text")[0].replace('viewBox="0 0 236 40" width="236" height="40"', 'viewBox="0 0 40 40"') + "</svg>"

# Vindue og scene (px i det færdige billede)
VB, BAR = 1000, 46                     # vinduets bredde og adresselinjens højde
S0 = VB / 1280                          # optagelsen er 1280x800 css px
VH = BAR + 800 * S0                     # vinduets højde (671)
SCENE_Y0, SCENE_Y1 = 448, 1288         # kameraets område
CX, CY = 540, (SCENE_Y0 + SCENE_Y1) / 2
MIDT = (640, 371)                       # indholdspunkt, der centrerer vinduet

U = "lakselus.streamlit.app"
# Fortællingen: krog (strømkortet) → status nu → prognosen → behandlinger → er i år værre? → strømmene → dokumentation.
# Tallene er fra uge 44, 2026, og skal tjekkes mod appen, når data er opdateret (se README).
# Kapitler: (kapitel, titel, undertitel, kildevinduer [(fra, til, url)], kamera [(andel, cx, cy, zoom)], stilstand, fart)
B = L["bokse"]
kort = B["c0_ramme"]; kx, ky = kort["x"] + kort["width"] / 2, kort["y"] + kort["height"] / 2
felt = B["l1_felt"]; sx, sy = felt["x"] + 300, felt["y"] + 40
fg = B["f1_graf"]; fgy = fg["y"] + fg["height"] / 2
hg = B["h1_graf"]; hgy = hg["y"] + hg["height"] / 2
KAPITLER = [
    ("BRAND", "Every Norwegian salmon farm, every week", "Lice counts, forecasts and ocean currents – from open data",
     [(M["c0_start"], M["c0_slut"], U + "/currents")],
     [(0, kx, ky, 1.25), (1.0, kx - 80, ky - 10, 1.5)], 1.2, 1.0),
    ("Latest week", "From the whole coast to one farm", "569 farms reported in week 44 – search any of 876",
     [(M["l1_start"] + 0.4, M["l1_venter"] + 0.15, U), (M["l1_efter"] - 0.4, M["l1_slut"], U + "/?site=25896")],
     [(0, *MIDT, 1.0), (0.3, sx, sy + 40, 1.45), (0.62, sx, sy + 40, 1.45), (0.74, 600, 300, 1.2), (1.0, 640, 330, 1.15)],
     0.8, 1.6),
    ("The forecast", "A 4-week forecast for every area", "29% lower error than naive – tested on seasons the model never saw",
     [(M["f1_start"] + 0.3, M["f1_slut"], U + "/forecast")],
     [(0, *MIDT, 1.0), (0.45, 700, fgy, 1.2), (1.0, 820, fgy, 1.32)], 0.8, 1.5),
    ("Treatments", "What treatments actually do", "Thermal: 87% fewer lice than similar untreated farms within a week",
     [(M["f2_start"], M["f2_slut"], U + "/forecast")],
     [(0, 640, 380, 1.05), (1.0, 380, 360, 1.35)], 0.8, 1.2),
    ("History", "Is this year worse than usual?", "2026 is still rising in week 44 – later than the usual peak",
     [(M["h1_start"], M["h1_slut"], U + "/history")],
     [(0, 640, hgy, 1.08), (1.0, 760, hgy, 1.28)], 0.8, 1.3),
    ("Currents", "Lice larvae drift with the water", "Near the farms, the surface moved about 7 km a day",
     [(M["c2_start"], M["c2_slut"], U + "/currents")],
     [(0, kx, ky, 1.1), (0.5, kx - 120, ky + 60, 1.3), (1.0, kx - 160, ky + 90, 1.42)], 0.8, 1.0),
    ("Documented", "Every method and every change on the record", "Open data · tested models · changelog",
     [(M["a1_start"] + 0.2, M["a1_slut"], U + "/about")],
     [(0, *MIDT, 1.0), (1.0, 640, 380, 1.1)], 0.6, 1.5),
]
INTRO_SLUT, OUTRO_LAENGDE = 0.0, 3.4
SCENER, t0 = [], INTRO_SLUT
for kapitel, titel, under, kilder, kam, hold, fart in KAPITLER:
    laengde = sum(b - a for a, b, _ in kilder) / fart
    SCENER.append((t0, t0 + hold + laengde, kapitel, titel, under, kilder, kam, hold))
    t0 += hold + laengde
OUTRO_START = t0
VARIGHED = round(OUTRO_START + OUTRO_LAENGDE, 2)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def kilde(scene, t):
    """Kildetid og url for et tidspunkt i scenen: kildevinduerne afspilles i træk, strakt til scenens længde."""
    start, slut, *_, vinduer, _, hold = scene
    laengder = [b - a for a, b, _ in vinduer]
    s = max(0, t - start - hold) / (slut - start - hold) * sum(laengder)
    for (a, b, url), lgd in zip(vinduer, laengder):
        if s <= lgd:
            return a + s, url
        s -= lgd
    a, b, url = vinduer[-1]
    return b, url


# Under genindlæsningen efter klikket på naboen står det sidste billede før klikket (siden er blank imens)
FRYS = []


def billede(ts):
    ts = next((a for a, b in FRYS if a <= ts < b), ts)
    i = max(0, bisect.bisect_right(TS, ts) - 1)
    return f"../frames4/b{i:05d}.jpg"


def kamera_i(scene, t):
    start, slut, *_, kam, hold = scene
    a = max(0, t - start - hold) / (slut - start - hold)
    for (a0, *k0), (a1, *k1) in zip(kam, kam[1:]):
        if a <= a1:
            e = ease((a - a0) / (a1 - a0) if a1 > a0 else 1)
            return [k0[i] + (k1[i] - k0[i]) * e for i in range(3)]
    return list(kam[-1][1:])


def kamera(t):
    """Kameraet for tidspunktet; ved et sceneskift glider det fra forrige scenes slutposition over 0,45 sek."""
    for i, sc in enumerate(SCENER):
        if sc[0] <= t < sc[1]:
            k = kamera_i(sc, t)
            if i and t - sc[0] < 0.9:
                k0 = kamera_i(SCENER[i - 1], SCENER[i - 1][1])
                e = ease((t - sc[0]) / 0.9)
                k = [k0[j] + (k[j] - k0[j]) * e for j in range(3)]
            return k
    return [*MIDT, 1.0]


def transform(cx, cy, z):
    """Vinduets placering: indholdspunktet (cx, cy) i midten, men vinduet dækker scenen, når det er zoomet ind."""
    fx, fy = cx * S0, BAR + cy * S0
    tx, ty = CX - z * fx, CY - z * fy
    w, h = VB * z, VH * z
    if w >= 1080:
        tx = min(0, max(1080 - w, tx))
    else:
        tx = (1080 - w) / 2
    if h >= SCENE_Y1 - SCENE_Y0:
        ty = min(SCENE_Y0, max(SCENE_Y1 - h, ty))
    else:
        ty = CY - h / 2  # lodret centreret, når det ikke fylder scenen
    return tx, ty


def mus_ved(ts):
    tider = [m[0] for m in MUS]
    i = bisect.bisect_right(tider, ts)
    if i == 0:
        return [1100, 700]
    return MUS[i - 1][1:]


def tilstand(t):
    st = {"t": t, "outro": 0, "vindue": 1, "tilt": 0, "loeft": 0, "slor": 0}
    # Outro: vinduet trækker sig tilbage, slutkortet kommer frem
    ud = ease((t - OUTRO_START) / 0.6)
    st["outro"] = ease((t - OUTRO_START - 0.3) / 0.6)
    if t >= OUTRO_START:
        st["vindue"] = 1 - ud
        st["loeft"] = -ud * 120
    # Scene, kilde og kamera
    idx = next((i for i, sc in enumerate(SCENER) if sc[0] <= t < sc[1]), 0 if t < SCENER[0][0] else len(SCENER) - 1)
    sc = SCENER[idx]
    tt = min(max(t, sc[0]), sc[1] - 1e-6)
    ts, url = kilde(sc, tt)
    st["img"] = billede(ts)
    # Kort krydstoning af indholdet ved sceneskift
    st["img2"], st["blend"] = None, 0
    if idx and t - sc[0] < 0.5:
        ts0, _ = kilde(SCENER[idx - 1], SCENER[idx - 1][1] - 1e-6)
        st["img2"], st["blend"] = billede(ts0), 1 - ease((t - sc[0]) / 0.5)
    st["url"] = url
    cx, cy, z = kamera(min(max(t, SCENER[0][0]), SCENER[-1][1] - 1e-6))
    st["z"] = z
    st["tx"], st["ty"] = transform(cx, cy, z)
    mx, my = mus_ved(ts)
    st["mx"], st["my"] = mx * S0, BAR + my * S0
    st["ringe"] = [[(ts - k[0]) / 0.45, k[1] * S0, BAR + k[2] * S0] for k in KLIK if 0 <= ts - k[0] < 0.45]
    # Tekster: aktiv scene og hvor langt animationen er
    st["scene"] = idx if SCENER[0][0] <= t < SCENER[-1][1] else -1
    st["ind"] = (9 if idx == 0 else t - sc[0]) if st["scene"] >= 0 else 0
    st["ud"] = (sc[1] - t) if st["scene"] >= 0 else 0
    return st


def ordspans(tekst, klasse):
    return f'<div class="{klasse}">' + " ".join(f'<span class="o"><span>{w}</span></span>' for w in tekst.split()) + "</div>"


tekster = "".join(
    f'<div class="tekst" id="tekst{i}"><div class="nr">{kapitel}</div>{ordspans(titel, "titel")}{ordspans(under, "under")}</div>'
    for i, (_, _, kapitel, titel, under, *_r) in enumerate(SCENER))
tekster = tekster.replace('<div class="nr">BRAND</div>',
                          '<div class="nr merke">' + LOGO + '<span class="live"><i></i>Live app</span></div>')
prikker = "".join(f'<i id="p{i}"></i>' for i in range(len(SCENER)))

HTML = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=block" rel="stylesheet">
<style>
* { margin: 0; box-sizing: border-box; }
body { width: 1080px; height: 1350px; overflow: hidden; font-family: Inter, sans-serif; color: #fff;
  background: radial-gradient(90% 55% at 50% 62%, #17405A 0%, #0D2737 48%, #081A25 100%); }
.glod { position: absolute; width: 900px; height: 900px; left: 90px; top: 380px; border-radius: 50%;
  background: radial-gradient(circle, rgba(183,196,126,.13), rgba(183,196,126,0) 60%); filter: blur(10px); }
.scene { position: absolute; left: 0; top: SCENE_Y0px; width: 1080px; height: SCENE_Hpx; overflow: hidden; perspective: 1400px; }
.vindue { position: absolute; left: 0; top: 0; width: VBpx; height: VHpx; transform-origin: 0 0; border-radius: 14px;
  overflow: hidden; background: #fff; box-shadow: 0 40px 90px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.08); }
.bar { height: BARpx; background: #E9EDF0; display: flex; align-items: center; padding: 0 16px; gap: 8px; }
.bar b { width: 12px; height: 12px; border-radius: 50%; display: block; }
.url { margin-left: 18px; flex: 1; height: 28px; border-radius: 14px; background: #fff; color: #4A5A66; font: 500 15px Inter;
  display: flex; align-items: center; padding: 0 14px; gap: 7px; }
.url svg { width: 12px; height: 12px; }
.indhold { position: absolute; left: 0; top: BARpx; width: VBpx; height: calc(VHpx - BARpx); }
.indhold img { position: absolute; inset: 0; width: 100%; height: 100%; }
#mus { position: absolute; width: 26px; height: 34px; margin: -2px 0 0 -3px; transform-origin: 3px 2px; z-index: 5;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
.ring { position: absolute; border-radius: 50%; border: 3px solid #6F7D3C; z-index: 4; }
.tekst { position: absolute; left: 56px; right: 56px; top: 92px; opacity: 0; }
.nr { font: 600 30px Inter; letter-spacing: .14em; text-transform: uppercase; color: #B7C47E; margin-bottom: 14px; }
.nr i { font-style: normal; color: #5F7484; }
.titel { font: 700 66px/1.05 'Source Serif 4', serif; letter-spacing: -.012em; }
.under { margin-top: 14px; font: 500 38px/1.3 Inter; color: #C9D4DC; }
.o { display: inline-block; overflow: hidden; vertical-align: top; padding-bottom: .08em; }
.o span { display: inline-block; }
.bund { position: absolute; left: 60px; right: 60px; bottom: 30px; display: flex; align-items: center; justify-content: space-between; }
.bund .logo svg { width: 190px; height: 32px; }
.prik { display: flex; gap: 8px; }
.prik i { width: 30px; height: 4px; border-radius: 2px; background: rgba(255,255,255,.18); display: block; }
.prik i.til { background: #B7C47E; }
.kort { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 0 90px; opacity: 0; }
.kort svg { width: 150px; height: 150px; margin-bottom: 44px; }
#intro { background: radial-gradient(62% 36% at 50% 50%, rgba(8,26,37,.92) 0%, rgba(8,26,37,.6) 60%, rgba(8,26,37,0) 100%); }
.kort h2, .kort .u { text-shadow: 0 2px 28px rgba(8,26,37,.9); }
#intro h2 { font-size: 72px; }
.titel, .under, .kort h2, .kort .u { text-wrap: balance; }
.kort h2 { font: 700 86px/1.04 'Source Serif 4', serif; letter-spacing: -.015em; }
.kort .u { margin-top: 28px; font: 500 40px/1.35 Inter; color: #C9D4DC; }
.merke { display: flex; align-items: center; gap: 22px; text-transform: none; letter-spacing: 0; margin-bottom: 22px; }
.merke svg { width: 300px; height: 51px; margin-right: -46px; }
.live { display: inline-flex; align-items: center; gap: 10px; font: 600 24px Inter; color: #0B2230; background: #B7C47E;
  padding: 7px 16px 7px 14px; border-radius: 999px; letter-spacing: .02em; }
.live i { width: 11px; height: 11px; border-radius: 50%; background: #0B2230; display: block; }
#outro .logo svg { width: 460px; height: 78px; margin-bottom: 40px; }
.kort .ons { margin-top: 18px; font: 600 34px Inter; color: #B7C47E; }
.kort .link { margin-top: 56px; font: 600 40px Inter; color: #0B2230; background: #B7C47E; padding: 18px 36px; border-radius: 16px; }
.kort .lille { margin-top: 36px; font: 500 30px/1.45 Inter; color: #9FB2C0; }
</style></head><body>
<div class="glod"></div>
<div class="scene"><div class="vindue" id="vindue">
  <div class="bar"><b style="background:#FF5F57"></b><b style="background:#FEBC2E"></b><b style="background:#28C840"></b>
    <div class="url"><svg viewBox="0 0 12 12"><rect x="2" y="5" width="8" height="6" rx="1.5" fill="#8A99A6"/><path d="M4 5V3.6a2 2 0 0 1 4 0V5" stroke="#8A99A6" stroke-width="1.4" fill="none"/></svg><span id="url"></span></div></div>
  <div class="indhold"><img id="img2"><img id="img"></div>
  <svg id="mus" viewBox="0 0 26 34"><path d="M3 2 L3 26 L9 20.5 L13.2 30 L17 28.3 L12.9 19 L21 19 Z" fill="#111" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>
  <div id="ringe"></div>
</div></div>
TEKSTER
<div class="kort" id="outro"><div class="logo">LOGO</div><h2>Try it yourself</h2>
  <div class="u">Weekly lice status, 4-week forecasts and ocean currents for every Norwegian salmon farm.</div>
  <div class="ons">Free · no sign-up · updated every Wednesday</div>
  <div class="link">lakselus.streamlit.app</div>
  <div class="lille">A personal project by Martin Eckberg Bindner<br>Python · scikit-learn · Streamlit · open source on GitHub</div></div>
<div class="bund" id="bund"><div class="logo">LOGO</div><div class="prik">PRIKKER</div></div>
<script>
const e = x => { x = Math.min(Math.max(x, 0), 1); return x * x * (3 - 2 * x); };
function ordInd(el, ind, ud, forsink) {
  el.querySelectorAll('.o span').forEach((s, i) => {
    const p = e((ind - forsink - i * 0.06) / 0.65), q = e((0.45 - ud) / 0.45);
    s.style.transform = 'translateY(' + ((1 - p) * 110 - q * 60) + '%)';
    s.style.opacity = Math.min(p, 1 - q);
  });
}
function render(s) {
  const v = document.getElementById('vindue');
  v.style.transform = 'translate(' + s.tx + 'px,' + (s.ty - SCENE_Y0 + s.loeft) + 'px) scale(' + s.z + ') rotateX(' + s.tilt + 'deg)';
  v.style.opacity = s.vindue;
  v.style.filter = s.slor > 0.05 ? 'blur(' + s.slor + 'px)' : 'none';
  document.getElementById('img').src = s.img;
  const i2 = document.getElementById('img2');
  if (s.img2) { i2.src = s.img2; i2.style.opacity = 1; document.getElementById('img').style.opacity = 1 - s.blend; }
  else { i2.style.opacity = 0; document.getElementById('img').style.opacity = 1; }
  document.getElementById('url').textContent = s.url;
  const m = document.getElementById('mus');
  m.style.left = s.mx + 'px'; m.style.top = s.my + 'px';
  m.style.transform = 'scale(' + (1 / Math.sqrt(s.z)) + ')';
  m.style.opacity = s.scene >= 0 ? 1 : 0;
  document.getElementById('ringe').innerHTML = s.ringe.map(r => {
    const rad = 6 + r[0] * 30;
    return '<div class="ring" style="left:' + (r[1] - rad) + 'px;top:' + (r[2] - rad) + 'px;width:' + 2 * rad + 'px;height:' + 2 * rad + 'px;opacity:' + (1 - r[0]) + '"></div>';
  }).join('');
  document.querySelectorAll('.tekst').forEach((el, i) => {
    const aktiv = i === s.scene;
    el.style.opacity = aktiv ? 1 : 0;
    if (aktiv) { ordInd(el.querySelector('.titel'), s.ind, s.ud, 0.05); ordInd(el.querySelector('.under'), s.ind, s.ud, 0.3);
      el.querySelector('.nr').style.opacity = Math.min(e(s.ind / 0.3), e(s.ud / 0.3)); }
  });
  document.getElementById('outro').style.opacity = s.outro;
  document.getElementById('bund').style.opacity = 1 - s.outro;
  for (let i = 0; i < ANTAL; i++) document.getElementById('p' + i).className = (i <= s.scene && s.scene >= 0) || s.outro > 0 ? 'til' : '';
}
</script></body></html>"""

for k, v in {"ANTAL": len(SCENER), "SCENE_Y0": SCENE_Y0, "SCENE_H": SCENE_Y1 - SCENE_Y0, "VB": VB, "VH": round(VH), "BAR": BAR}.items():
    HTML = HTML.replace(k, str(v))
HTML = (HTML.replace("TEKSTER", tekster).replace("MAERKE", MAERKE).replace("PRIKKER", prikker)
        .replace("LOGO", LOGO))
UD.mkdir(exist_ok=True)
(UD / "demo.html").write_text(HTML)
BIL = UD / "b"
if BIL.exists():
    shutil.rmtree(BIL)
BIL.mkdir()

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    page = b.new_page(viewport={"width": 1080, "height": 1350})
    page.goto((UD / "demo.html").as_uri())
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(800)
    import sys
    tider = [float(x) for x in sys.argv[2:]] if len(sys.argv) > 1 and sys.argv[1] == "proeve" else None
    n = len(tider) if tider else int(FPS * VARIGHED)
    for i in range(n):
        st = tilstand(tider[i] if tider else i / FPS)
        page.evaluate("s => new Promise(r => { render(s); Promise.all([...document.querySelectorAll('.indhold img')]"
                      ".map(im => im.complete ? 1 : new Promise(q => { im.onload = q; im.onerror = q; })))"
                      ".then(() => requestAnimationFrame(() => r())); })", st)
        page.screenshot(path=str(BIL / f"f{i:04d}.png"))
    b.close()

if tider:
    raise SystemExit("prøvebilleder i " + str(BIL))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(BIL / "f%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow", "-movflags", "+faststart",
                str(MAPPE / "lakselus-rundtur.mp4")], check=True)
print("færdig")
