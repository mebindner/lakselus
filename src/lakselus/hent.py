"""Hent rådata til lokal cache:  python -m lakselus.hent --fra 2019 --til 2025"""

import argparse
import datetime as dt

from lakselus import barentswatch
from lakselus.config import DATA_RAW


def main() -> None:
    i_aar = dt.date.today().isocalendar()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fra", type=int, default=2019)
    p.add_argument("--til", type=int, default=i_aar.year)
    args = p.parse_args()

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    barentswatch.produktionsomraader().to_csv(DATA_RAW / "produktionsomraader.csv", index=False)
    print("Gemt produktionsomraader.csv")

    # Ét år ad gangen, sekventielt – som BarentsWatch beder om.
    for aar in range(args.fra, args.til + 1):
        til_uge = i_aar.week - 1 if aar == i_aar.year else dt.date(aar, 12, 28).isocalendar().week
        df = barentswatch.lusetal(aar, aar, til_uge)
        df.to_csv(DATA_RAW / f"lusetal_{aar}.csv", index=False)
        print(f"Gemt lusetal_{aar}.csv ({len(df):,} rækker)")


if __name__ == "__main__":
    main()
