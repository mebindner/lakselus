"""Hent rådata til lokal cache:  python -m lakselus.hent --fra 2019 --til 2025

Henter produktionsområder samt lusetal og lusebehandlinger år for år til data/raw.
Køres hver uge af GitHub Actions (se .github/workflows/ugentlig-opdatering.yml).
"""

import argparse
import datetime as dt

from lakselus import barentswatch
from lakselus.config import DATA_RAW

# Datasæt, der hentes pr. år: filnavnets præfiks → hentefunktion.
AARLIGE_DATASAET = {
    "lusetal": barentswatch.lusetal,
    "behandlinger": barentswatch.behandlinger,
}


def main() -> None:
    # --- Argumenter ----------------------------------------------------------------------
    i_aar = dt.date.today().isocalendar()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fra", type=int, default=2019)
    p.add_argument("--til", type=int, default=i_aar.year)
    args = p.parse_args()

    # --- Produktionsområder (omrids og trafiklys) ----------------------------------------
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    barentswatch.produktionsomraader().to_csv(DATA_RAW / "produktionsomraader.csv", index=False)
    print("Gemt produktionsomraader.csv")

    # --- Ugentlige data, ét år ad gangen og sekventielt – som BarentsWatch beder om ------
    for aar in range(args.fra, args.til + 1):
        til_uge = i_aar.week - 1 if aar == i_aar.year else dt.date(aar, 12, 28).isocalendar().week
        if til_uge < 1:  # i ISO-uge 1 er ingen uger i det nye år afsluttet endnu
            continue
        for praefiks, hent in AARLIGE_DATASAET.items():
            df = hent(aar, aar, til_uge)
            df.to_csv(DATA_RAW / f"{praefiks}_{aar}.csv", index=False)
            print(f"Gemt {praefiks}_{aar}.csv ({len(df):,} rækker)")


if __name__ == "__main__":
    main()
