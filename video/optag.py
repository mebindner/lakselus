"""Optager en rundtur i appen som rigtig video (Chromes screencast), mens et manuskript bevæger musen, skriver og ruller.

Rækkefølgen følger videoen: Currents (krog) → Latest week (kysten og ét anlæg) → Forecast → behandlinger → History →
Currents (finale) → About. Gemmer billeder med tidsstempel i frames4/ og log4.json med musens bane, klik, markører
og elementernes placering, som klip.py bruger til kamera og tekster.
"""

import base64
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

MAPPE = Path(__file__).parent
BILLEDER = MAPPE / "frames4"
BILLEDER.mkdir(exist_ok=True)
for gammel in BILLEDER.glob("*.jpg"):
    gammel.unlink()
URL = "http://localhost:8502"
ANLAEG = "Skorpo · PO 3 · 25896"  # det anlæg, der søges frem (højeste lusetal i uge 44)
# Hjælpebobler, Streamlits statusikon og rullebjælker skjules, så billedet er roligt.
SKJUL = """
.valghjaelp, [data-testid="stStatusWidget"], [data-testid="stDecoration"], [data-testid="stToolbar"] { display: none !important; }
* { scrollbar-width: none !important; }
"""

log = {"mus": [], "klik": [], "mark": {}, "bokse": {}, "billeder": []}
ROLIG = 1.45  # alle bevægelser (mus, rulning) tager så meget længere tid end i den hurtige udgave
mus = [1100.0, 700.0]


def nu():
    return time.time()


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)

        def billede(e):
            n = len(log["billeder"])
            (BILLEDER / f"b{n:05d}.jpg").write_bytes(base64.b64decode(e["data"]))
            log["billeder"].append(e["metadata"]["timestamp"])
            cdp.send("Page.screencastFrameAck", {"sessionId": e["sessionId"]})

        cdp.on("Page.screencastFrame", billede)

        def vent(s):
            page.wait_for_timeout(int(s * 1000))

        def mark(navn):
            log["mark"][navn] = nu()

        def boks(navn, sel, nr=0):
            bb = page.locator(sel).nth(nr).bounding_box()
            log["bokse"][navn] = bb
            return bb

        def flyt(x, y, s=0.8):
            """Musen glider (blødt ind og ud) til x, y."""
            x0, y0 = mus
            s *= ROLIG
            n = max(2, int(s * 40))
            for i in range(1, n + 1):
                f = i / n
                e = f * f * (3 - 2 * f)
                mus[:] = [x0 + (x - x0) * e, y0 + (y - y0) * e]
                page.mouse.move(*mus)
                log["mus"].append([nu(), *mus])
                page.wait_for_timeout(int(s * 1000 / n))

        def klik():
            log["klik"].append([nu(), *mus])
            page.mouse.down()
            page.wait_for_timeout(70)
            page.mouse.up()

        def rul(y, s=1.6):
            """Blød rulning af Streamlits hovedområde til y (css px)."""
            s *= ROLIG
            page.evaluate(f"""() => new Promise(r => {{
                const m = document.querySelector('[data-testid=stMain]'), y0 = m.scrollTop, y1 = {y}, t0 = performance.now();
                const f = t => {{ const p = Math.min((t - t0) / {s * 1000}, 1), e = p < .5 ? 4*p*p*p : 1 - Math.pow(-2*p + 2, 3) / 2;
                  m.scrollTop = y0 + (y1 - y0) * e; p < 1 ? requestAnimationFrame(f) : r(); }};
                requestAnimationFrame(f); }})""")

        def top_af(sel, nr=0, luft=90):
            """Rulleposition, der lægger elementet `luft` px under toppen af vinduet."""
            return page.evaluate(f"""() => {{ const m = document.querySelector('[data-testid=stMain]');
                const e = document.querySelectorAll('{sel}')[{nr}];
                return m.scrollTop + e.getBoundingClientRect().top - {luft}; }}""")

        def klar(sti, vente=6):
            page.goto(URL + sti)
            page.wait_for_selector(".sidehoved", timeout=90000)
            page.add_style_tag(content=SKJUL)
            vent(vente)

        def til_kort(navn, luft=58):
            """Ruller kortets iframe op under toppen og gemmer dens placering."""
            rul(top_af("iframe", luft=luft), 0.01)
            vent(0.6)
            return boks(navn, "iframe")

        # Strømkortet indlæses først, så partiklerne allerede flyder, når optagelsen starter.
        klar("/currents", 9)
        r = til_kort("c0_ramme")
        page.mouse.move(*mus)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 88, "maxWidth": 2560, "maxHeight": 1600,
                                          "everyNthFrame": 1})
        vent(0.5)

        # 1. Krog: kyststrømmen i bevægelse
        mark("c0_start")
        flyt(r["x"] + r["width"] * 0.42, r["y"] + r["height"] * 0.45, 2.4)
        vent(1.6)
        mark("c0_slut")

        # 2. Latest week: kystens status, derefter søgning på ét anlæg
        klar("/")
        mark("l1_start")
        vent(2.6)
        s = boks("l1_felt", ".st-key-soegning")
        flyt(s["x"] + 180, s["y"] + s["height"] / 2, 0.7)
        mark("l1_soeg")
        klik()
        vent(0.4)
        for tegn in "Skorp":
            page.keyboard.type(tegn)
            vent(0.2)
        vent(0.6)
        o = page.get_by_role("option", name=ANLAEG).bounding_box()
        flyt(o["x"] + 120, o["y"] + o["height"] / 2, 0.5)
        vent(0.2)
        klik()
        mark("l1_venter")
        page.wait_for_url("**site=25896**", timeout=60000)
        page.wait_for_selector("text=FARM BRIEF", timeout=60000)
        vent(4.0)
        mark("l1_efter")
        flyt(900, 360, 1.0)
        vent(1.4)
        mark("l1_slut")

        # 3. Forecast: prognosen for PO 3 med interval
        klar("/forecast")
        mark("f1_start")
        vent(1.6)
        rul(top_af(".figur", 0, 60), 1.4)
        g = boks("f1_graf", '[data-testid="stVegaLiteChart"]')
        flyt(g["x"] + g["width"] * 0.9, g["y"] + g["height"] * 0.5, 1.2)
        vent(1.6)
        mark("f1_slut")

        # 4. Behandlingseffekten (figur 2 på Forecast)
        rul(top_af(".figur", 1, 60), 0.01)
        vent(1.0)
        mark("f2_start")
        g = boks("f2_figur", ".figur", 1)
        flyt(g["x"] + g["width"] * 0.6, g["y"] + 100, 1.4)  # over forklaringen, ikke over graferne (ingen tooltip)
        vent(1.8)
        mark("f2_slut")

        # 5. History: én kurve pr. år, 2026 fremhævet
        klar("/history")
        rul(top_af(".figur", 0, 70), 0.01)
        vent(1.2)
        mark("h1_start")
        g = boks("h1_graf", '[data-testid="stVegaLiteChart"]')
        flyt(g["x"] + g["width"] * 0.25, g["y"] + g["height"] * 0.7, 0.01)
        flyt(g["x"] + g["width"] * 0.82, g["y"] + g["height"] * 0.35, 2.4)
        vent(1.6)
        mark("h1_slut")

        # 6. Currents (finale): noterne om det hurtigste og langsomste vand
        klar("/currents", 9)
        r = til_kort("c2_ramme")
        vent(0.6)
        mark("c2_start")
        flyt(r["x"] + r["width"] * 0.3, r["y"] + r["height"] * 0.7, 2.4)
        vent(3.2)
        mark("c2_slut")

        # 7. About: metoden og ændringsloggen
        klar("/about")
        mark("a1_start")
        vent(1.2)
        rul(top_af(".afsnit", 4, 70), 2.2)
        vent(1.4)
        mark("a1_slut")

        cdp.send("Page.stopScreencast")
        vent(0.5)
        b.close()
    (MAPPE / "log4.json").write_text(json.dumps(log))
    print("billeder:", len(log["billeder"]), "markører:", list(log["mark"]))


main()
