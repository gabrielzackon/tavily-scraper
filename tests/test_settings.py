from pathlib import Path
from src.settings import load_proxy_from_txt


def test_load_proxy_from_txt_parses_user_pass(tmp_path: Path):
    proxy_file = tmp_path / "ProxyURL.txt"
    proxy_file.write_text(
        "https://user123:pass456@proxy.example.com:8080",
        encoding="utf-8",
    )

    proxy = load_proxy_from_txt(str(proxy_file))

    assert proxy.server == "https://proxy.example.com:8080"
    assert proxy.username == "user123"
    assert proxy.password == "pass456"
    assert proxy.url == "https://user123:pass456@proxy.example.com:8080"