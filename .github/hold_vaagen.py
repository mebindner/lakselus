"""Åbner den offentlige app i en usynlig browser, så den ikke går i dvale.

Streamlit Community Cloud lægger apps i dvale efter 12 timer uden besøg. Sover appen alligevel,
trykkes der på vækkeknappen. Scriptet fejler, hvis appens indhold ikke dukker op, så GitHub giver besked.
"""

import sys

from playwright.sync_api import sync_playwright

URL = "https://lakselus.streamlit.app/"
KENDETEGN = "Updates every Wednesday"  # tekst i selve appen, ikke i sidetitlen
VENT_MS = 180_000


def app_er_oppe(side) -> bool:
    return any(KENDETEGN.lower() in (f.content() or "").lower() for f in side.frames if not f.is_detached())


with sync_playwright() as p:
    browser = p.chromium.launch()
    side = browser.new_page()
    side.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    side.wait_for_timeout(8_000)

    vaek = side.get_by_role("button", name="get this app back up", exact=False)
    if vaek.count():
        print("Appen sov – vækker den.")
        vaek.first.click()

    for _ in range(VENT_MS // 5_000):
        if app_er_oppe(side):
            print("Appen er oppe.")
            browser.close()
            sys.exit(0)
        side.wait_for_timeout(5_000)

    browser.close()
    sys.exit("Appens indhold dukkede ikke op – tjek lakselus.streamlit.app.")
