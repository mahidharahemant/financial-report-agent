import logging

from src.log import get_logger


def test_log_writes_to_a_file(monkeypatch, tmp_path):
    import src.log as app_log

    logging.getLogger("src").handlers.clear()
    monkeypatch.setattr(app_log, "_configured", False)
    monkeypatch.setattr(app_log, "LOG_PATH", tmp_path / "app.log")
    get_logger("src.demo").info("saved filing")
    assert "saved filing" in (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "src.demo" in (tmp_path / "app.log").read_text(encoding="utf-8")
