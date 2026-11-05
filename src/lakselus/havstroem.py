"""Havstrømme: overfladestrømmen fra MET Norways havmodel NorKyst v3, pakket til et animeret strømkort.

Kør efter `python -m lakselus.hent`:  python -m lakselus.havstroem
Skriver data/app/havstroem.npz med døgnmiddelstrømmen i overfladen for de syv dage i den seneste komplette
lusetælleuge, så kortet viser vandets bevægelse i samme uge som lusetallene.

Kilde: NorKyst v3 (800 m), MET Norway, licens CC BY 4.0 / NLOD – kilden skal angives som MET Norway.
Strømmen hentes over OPeNDAP uden ekstra pakker: DAP2-svaret er en tekstbeskrivelse efterfulgt af binære
XDR-data, som læses direkte med numpy.

Indhold
1. Kilde og konstanter
2. OPeNDAP          – et udsnit af en variabel som numpy-array
3. Ugens strømme    – døgnmiddel af overfladestrømmen (hver 3. time) for ugens syv dage
4. Omregning        – fra modellens skæve polarstereografiske gitter til et regulært Web Mercator-gitter
5. Kvalitetskontrol og pakning
6. HTML             – data indsættes i skabelonen havstroem.html (partikelanimationen kører i browseren)
7. Kommandolinje
"""

import base64
import json
import time
import warnings
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

from lakselus.config import DATA_APP

# --- 1. Kilde og konstanter -------------------------------------------------------------------

URL = "https://thredds.met.no/thredds/dodsC/fou-hi/norkystv3_800m_m00_be"  # "best estimate": analyser + nyeste prognose
APP_FIL = DATA_APP / "havstroem.npz"
SKABELON = Path(__file__).with_name("havstroem.html")
KILDE = "Surface currents: NorKyst v3 ocean model, MET Norway (CC BY 4.0)."

SKRIDT = 4            # hvert 4. modelpunkt: 3,2 km mellem punkterne (modellen har 800 m)
TIMER = range(0, 24, 3)  # døgnmiddel af hver 3. time – udglatter tidevandet, men bevarer døgnets strømbillede
GRAD = 0.07           # målgitterets skridt i grader længde (≈ 3 km ved 65° N); breddegrad i samme Mercator-enhed
LON = (-1.0, 33.0)    # hele norskekysten med havet ud for (modelområdet går fra Skagerrak til Barentshavet)
LAT = (56.5, 72.5)
MAKS_AFSTAND_KM = 2.6  # et målpunkt længere fra nærmeste havpunkt end dette regnes som land
SKALA = 0.01          # m/s pr. trin; int8 giver ±1,27 m/s, langt over døgnmidlet næsten overalt
JORD_KM = 6371.0


# --- 2. OPeNDAP -------------------------------------------------------------------------------

_XDR = {"Int16": ">i4", "Int32": ">i4", "Float32": ">f4", "Float64": ">f8"}  # Int16 sendes som 32 bit i XDR


def _hent(sti: str, forsoeg: int = 3) -> bytes:
    for i in range(forsoeg):
        try:
            r = requests.get(f"{URL}.dods?{sti}", timeout=180)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if i == forsoeg - 1:
                raise
            time.sleep(10 * (i + 1))


def laes_dods(svar: bytes) -> np.ndarray:
    """Første array i et DAP2-svar (beskrivelse + 'Data:' + XDR) som numpy-array med den beskrevne form."""
    hoved, _, krop = svar.partition(b"\nData:\n")
    linje = next(l for l in hoved.decode().splitlines() if "[" in l and l.strip().split()[0] in _XDR)
    type_, form = linje.strip().split()[0], [int(d.split("=")[1].split("]")[0]) for d in linje.split("[")[1:] if "=" in d]
    n = int(np.frombuffer(krop[:4], ">u4")[0])
    return np.frombuffer(krop[8:8 + n * np.dtype(_XDR[type_]).itemsize], _XDR[type_]).reshape(form)


def gitterstoerrelse() -> tuple[int, int]:
    """(Y, X) for modelgitteret, læst fra datasættets beskrivelse (DDS)."""
    dds = requests.get(f"{URL}.dds?h", timeout=60).text
    linje = next(l for l in dds.splitlines() if " h[" in l)
    return tuple(int(d.split("=")[1].split("]")[0]) for d in linje.split("[")[1:])


def udsnit(var: str, *dim: str) -> np.ndarray:
    """Fx udsnit('lat', '0:4:1147', '0:4:2746'). `var.var` giver kun selve arrayet, ikke gitterets akser."""
    navn = var if var == "time" else f"{var}.{var}"
    return laes_dods(_hent(navn + "".join(f"[{d}]" for d in dim)))


# --- 3. Ugens strømme -------------------------------------------------------------------------

def tidsindeks(tider: np.ndarray, dag: pd.Timestamp) -> list[int]:
    """Indeks for dagens timer i TIMER (UTC). Fejler, hvis modellen ikke dækker dagen."""
    sek = np.array([(dag + pd.Timedelta(hours=t)).value // 10**9 for t in TIMER], dtype=float)
    idx = np.searchsorted(tider, sek)
    if (idx >= len(tider)).any() or not np.allclose(tider[np.minimum(idx, len(tider) - 1)], sek):
        raise ValueError(f"NorKyst v3 dækker ikke {dag:%Y-%m-%d}")
    return idx.tolist()


def ugens_stroemme(uge_start: pd.Timestamp, log=print) -> dict:
    """Døgnmiddel af overfladestrømmen (0 m) for ugens syv dage, på modellens gitter med SKRIDT."""
    ny, nx = gitterstoerrelse()
    sy, sx = f"0:{SKRIDT}:{ny - 1}", f"0:{SKRIDT}:{nx - 1}"
    lat, lon = udsnit("lat", sy, sx), udsnit("lon", sy, sx)
    tider = udsnit("time")
    u_dage, v_dage = [], []
    for d in range(7):
        dag = uge_start + pd.Timedelta(days=d)
        idx = tidsindeks(tider, dag)
        t = f"{idx[0]}:{idx[1] - idx[0]}:{idx[-1]}"
        t0 = time.time()
        for var, dage in (("u_eastward", u_dage), ("v_northward", v_dage)):
            a = udsnit(var, t, "0", sy, sx)[:, 0].astype(float)  # (timer, Y, X) i overfladen
            a[a == -32767] = np.nan                                # land
            with warnings.catch_warnings():                        # landceller er NaN hele døgnet
                warnings.simplefilter("ignore", RuntimeWarning)
                dage.append(np.nanmean(a, axis=0) * 0.001)         # scale_factor 0.001 → m/s
        log(f"  {dag:%a %d %b}: {time.time() - t0:4.1f} s")
    return {"lat": lat, "lon": lon, "u": np.stack(u_dage), "v": np.stack(v_dage)}


# --- 4. Omregning til Web Mercator ------------------------------------------------------------
# Browseren tegner i Web Mercator (som deck.gl). Projektionen er konform og har nord opad, så øst- og
# nordkomponenten af strømmen kan bruges direkte. Målgitteret er regulært i længde og Mercator-y, så et
# opslag fra en position er to multiplikationer.

def merc_y(lat):
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def _enhedsvektor(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1)


def maalgitter() -> tuple[np.ndarray, np.ndarray]:
    """Længde- og breddegrad for målgitterets cellecentre (rækker fra syd mod nord)."""
    trin = np.radians(GRAD)
    lons = np.arange(LON[0], LON[1] + 1e-9, GRAD)
    ys = np.arange(merc_y(LAT[0]), merc_y(LAT[1]) + 1e-12, trin)
    lats = np.degrees(2 * np.arctan(np.exp(ys)) - np.pi / 2)
    return lons, lats


def til_mercator(st: dict) -> dict:
    """Nærmeste havpunkt for hver målcelle; celler uden havpunkt inden for MAKS_AFSTAND_KM bliver land (NaN)."""
    hav = np.isfinite(st["u"]).all(axis=0) & np.isfinite(st["v"]).all(axis=0)
    traer = cKDTree(_enhedsvektor(st["lat"][hav], st["lon"][hav]))
    lons, lats = maalgitter()
    glat, glon = np.meshgrid(lats, lons, indexing="ij")
    afstand, i = traer.query(_enhedsvektor(glat, glon).reshape(-1, 3))
    land = (afstand * JORD_KM > MAKS_AFSTAND_KM).reshape(glat.shape)
    u = st["u"][:, hav][:, i].reshape(7, *glat.shape)
    v = st["v"][:, hav][:, i].reshape(7, *glat.shape)
    u[:, land], v[:, land] = np.nan, np.nan
    return {"lons": lons, "lats": lats, "u": u, "v": v}


# --- 5. Kvalitetskontrol og pakning -----------------------------------------------------------

MIN_HAVCELLER = 40_000  # hele modelområdet giver omkring 100.000 ved 0,07°
FART = (0.03, 0.6)      # rimelig middelfart i overfladen, m/s


def kvalitetstjek(g: dict) -> list[str]:
    hav = np.isfinite(g["u"][0])
    problemer = []
    if hav.sum() < MIN_HAVCELLER:
        problemer.append(f"kun {hav.sum():,} havceller")
    fart = np.nanmean(np.hypot(g["u"], g["v"]), axis=(1, 2))
    if not ((fart > FART[0]) & (fart < FART[1])).all():
        problemer.append(f"urimelig middelfart pr. dag: {np.round(fart, 3).tolist()} m/s")
    return problemer


def pak(g: dict, uge_start: pd.Timestamp) -> dict:
    """int8 i trin af SKALA m/s; -128 = land. Rækker fra syd mod nord."""
    def kod(a):
        return np.where(np.isfinite(a), np.clip(np.round(a / SKALA), -127, 127), -128).astype(np.int8)
    return {"u": kod(g["u"]), "v": kod(g["v"]), "lon0": g["lons"][0], "lat0": g["lats"][0], "grad": GRAD,
            "skala": SKALA, "uge_start": np.datetime64(uge_start.date(), "D")}


def gem(pakke: dict) -> None:
    DATA_APP.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(APP_FIL, **pakke)


def indlaes() -> dict | None:
    if not APP_FIL.exists():
        return None
    with np.load(APP_FIL) as f:
        return {k: f[k][()] if f[k].ndim == 0 else f[k] for k in f.files}  # skalarer gemmes som 0-d arrays


# --- 6. HTML ---------------------------------------------------------------------------------

def html(pakke: dict, anlaeg: list[list], noter: list[list] | None = None) -> str:
    """Kortets HTML. `anlaeg`: [[lon, lat, navn, hunlus], ...] for ugens lusetal.
    `noter`: [[lon, lat, titel, tekst], ...] – nummererede noter, der står på kortet.

    Strømfeltet sendes som int8 (først u for alle dage, så v), pakket med zlib og base64-kodet; browseren pakker
    det ud med DecompressionStream. Det holder hele kysten i syv dage under 1 MB.
    """
    uge_start = pd.Timestamp(pakke["uge_start"])
    iso = uge_start.isocalendar()
    felt = np.concatenate([pakke["u"].ravel(), pakke["v"].ravel()])
    data = {
        "rader": int(pakke["u"].shape[1]), "kolonner": int(pakke["u"].shape[2]),
        "lon0": float(pakke["lon0"]), "lat0": float(pakke["lat0"]), "grad": float(pakke["grad"]),
        "skala": float(pakke["skala"]), "havceller": int((pakke["u"][0] != -128).sum()),
        "stroem": base64.b64encode(zlib.compress(felt.tobytes(), 9)).decode("ascii"),
        "dage": [[(uge_start + pd.Timedelta(days=d)).strftime("%a"),
                  (uge_start + pd.Timedelta(days=d)).strftime("%a %-d %b")] for d in range(7)],
        "uge": int(iso.week), "aar": int(iso.year), "anlaeg": anlaeg, "noter": noter or [],
    }
    tekst = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return SKABELON.read_text(encoding="utf-8").replace("__DATA__", tekst)


def anlaeg_i_ugen(raa: pd.DataFrame, uge_start: pd.Timestamp) -> list[list]:
    """Lokaliteter, der talte lus i ugen: [lon, lat, navn, hunlus]."""
    u = raa[(raa["har_talt"] == "Ja") & (raa["uge_start"] == uge_start)].dropna(subset=["hunlus", "lat", "lon"])
    return [[round(float(r.lon), 4), round(float(r.lat), 4), str(r.lokalitet_navn), round(float(r.hunlus), 3)]
            for r in u.itertuples()]


MAKS_ANLAEG_KM = 3.0  # anlæg længere fra nærmeste havcelle end dette ligger i en fjord, gitteret ikke viser


def fart_ved_anlaeg(pakke: dict, anlaeg: pd.DataFrame) -> pd.DataFrame:
    """Hvor langt overfladevandet flyttede sig pr. døgn ved hvert anlæg (km/døgn), som snit over ugens dage.

    Døgnmiddelstrømmen i nærmeste havcelle gange ét døgn. Cellen ligger ofte lidt ude i det åbne vand foran
    anlægget (gitteret er ca. 3 km), så tallet beskriver vandet, der passerer anlæggenes område. Anlæg mere end
    MAKS_ANLAEG_KM fra en havcelle får NaN.
    """
    lons, lats = maalgitter()
    r, c = np.nonzero(pakke["u"][0] != -128)
    traer = cKDTree(_enhedsvektor(lats[r], lons[c]))
    afstand, i = traer.query(_enhedsvektor(anlaeg["lat"].to_numpy(float), anlaeg["lon"].to_numpy(float)))
    u = pakke["u"][:, r[i], c[i]] * float(pakke["skala"])
    v = pakke["v"][:, r[i], c[i]] * float(pakke["skala"])
    km_dag = np.hypot(u, v).mean(axis=0) * 86.4  # m/s → km pr. døgn
    afstand_km = afstand * JORD_KM
    return anlaeg.assign(afstand_km=afstand_km, km_dag=np.where(afstand_km <= MAKS_ANLAEG_KM, km_dag, np.nan))


# --- 7. Kommandolinje -------------------------------------------------------------------------

def main() -> None:
    from lakselus import data

    raa = data.indlaes_raa()
    uge_start = raa.loc[raa["har_talt"] == "Ja", "uge_start"].max()
    iso = uge_start.isocalendar()
    print(f"Henter overfladestrømme for uge {iso.week} {iso.year} fra NorKyst v3 …")
    g = til_mercator(ugens_stroemme(uge_start))
    problemer = kvalitetstjek(g)
    if problemer:
        raise SystemExit("Publicerer ikke strømme – data ser forkerte ud:\n- " + "\n- ".join(problemer))
    gem(pak(g, uge_start))
    print(f"Skrev {APP_FIL.name} ({np.isfinite(g['u'][0]).sum():,} havceller, {APP_FIL.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
