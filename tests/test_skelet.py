from lakselus import KILDE_TEKST, barentswatch, config


def test_pakken_importerer_uden_netvaerk():
    assert "BarentsWatch" in KILDE_TEKST
    assert barentswatch.TOKEN_URL.startswith("https://")
    assert config.DATA_RAW.name == "raw"
