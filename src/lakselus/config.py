"""Stier og hemmeligheder. Nøgler læses kun fra miljøet / lokal .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROD = Path(__file__).resolve().parents[2]
DATA_RAW = ROD / "data" / "raw"
DATA_PROCESSED = ROD / "data" / "processed"

load_dotenv(ROD / ".env")


def har_noegle() -> bool:
    return bool(os.getenv("BW_CLIENT_ID") and os.getenv("BW_CLIENT_SECRET"))


def hent_noegle() -> tuple[str, str]:
    if not har_noegle():
        raise RuntimeError(
            "BW_CLIENT_ID/BW_CLIENT_SECRET mangler. Kopiér .env.example til .env og udfyld (se README)."
        )
    return os.environ["BW_CLIENT_ID"], os.environ["BW_CLIENT_SECRET"]
