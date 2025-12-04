from __future__ import annotations

import importlib
import json


def _reload_modules():
    import app.config as app_config
    import app.services.logging_utils as logging_utils

    app_config = importlib.reload(app_config)
    logging_utils = importlib.reload(logging_utils)
    return app_config, logging_utils


def test_structured_logger_writes_json(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    monkeypatch.setenv("FOKS_LOG_FILE", str(log_file))
    monkeypatch.setenv("FOKS_LOG_JSON", "true")
    monkeypatch.setenv("FOKS_LOG_LEVEL", "INFO")

    _, logging_utils = _reload_modules()

    logger = logging_utils.get_logger("test.struct")
    logger.info("fbp.request", extra={"payload": {"token": "secret123", "value": 42}})

    # Flush handlers to ensure file write.
    for handler in logger.handlers:
        handler.flush()  # type: ignore[attr-defined]

    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "fbp.request"
    assert payload["payload"]["token"] == "***"
    assert payload["payload"]["value"] == 42


def test_text_logger_sanitizes(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    monkeypatch.setenv("FOKS_LOG_FILE", str(log_file))
    monkeypatch.setenv("FOKS_LOG_JSON", "false")
    monkeypatch.setenv("FOKS_LOG_LEVEL", "INFO")

    _, logging_utils = _reload_modules()

    logger = logging_utils.get_logger("test.text")
    logger.warning('token="abc123"')

    for handler in logger.handlers:
        handler.flush()  # type: ignore[attr-defined]

    contents = log_file.read_text()
    assert "***" in contents

