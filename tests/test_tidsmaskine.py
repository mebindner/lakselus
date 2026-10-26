import base64

import pandas as pd

from lakselus.tidsmaskine import MANGLER, html, pak


def test_pak_koder_en_byte_pr_uge_og_lokalitet():
    raa = pd.DataFrame({
        "har_talt": ["Ja", "Ja", "Nei"],
        "uge_start": pd.to_datetime(["2020-01-06", "2020-01-13", "2020-01-13"]),
        "lokalitet": [1, 2, 1],
        "lokalitet_navn": ["A", "B", "A"],
        "hunlus": [0.25, 9.0, None],
        "lat": [60.0, 61.0, 60.0],
        "lon": [5.0, 6.0, 5.0],
    })
    p = pak(raa, fra="2020-01-01")
    v = list(base64.b64decode(p["vaerdier"]))
    # uge 0: A=25, B mangler · uge 1: A mangler (ikke talt), B loftet ved 254
    assert v == [25, MANGLER, MANGLER, 254]
    assert "</script>" not in html(p).split("const D = ")[1].split(";")[0]
