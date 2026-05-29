"""Regression tests for gui/server.py."""

from dataclasses import asdict
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# Prevent the bot thread from actually running during tests
@pytest.fixture(autouse=True)
def _reset_state():
    """Reset server globals between tests."""
    import gui.server as srv
    srv._stop_event.clear()
    srv._bot_thread = None
    srv._state = srv.BotState()
    yield
    srv._stop_event.set()


@pytest.fixture()
def client():
    from gui.server import app
    return TestClient(app)


# ── BotState serialization ──────────────────────────────────────────────────

def test_botstate_has_symbol_field():
    from gui.server import BotState
    state = BotState()
    d = asdict(state)
    assert "symbol" in d, "BotState must expose 'symbol' for the JS dashboard"


def test_botstate_is_json_serializable():
    import json
    from gui.server import BotState
    d = asdict(BotState())
    assert json.dumps(d)  # must not raise


def test_botstate_symbol_matches_config():
    from config import config
    from gui.server import BotState
    assert BotState().symbol == config.SYMBOL


# ── _trim_chart ─────────────────────────────────────────────────────────────

def test_trim_chart_enforces_window():
    import gui.server as srv
    window = srv.CHART_WINDOW
    with srv._lock:
        for i in range(window + 10):
            srv._state.chart_labels.append(str(i))
            srv._state.chart_close.append(float(i))
            srv._state.chart_histogram.append(0.0)
            srv._state.chart_dif.append(0.0)
            srv._state.chart_dea.append(0.0)
        srv._trim_chart()

    assert len(srv._state.chart_labels) == window
    assert len(srv._state.chart_close) == window
    assert len(srv._state.chart_histogram) == window


def test_trim_chart_noop_when_within_window():
    import gui.server as srv
    with srv._lock:
        srv._state.chart_labels.extend(["a", "b"])
        srv._state.chart_close.extend([1.0, 2.0])
        srv._state.chart_histogram.extend([0.0, 0.0])
        srv._state.chart_dif.extend([0.0, 0.0])
        srv._state.chart_dea.extend([0.0, 0.0])
        srv._trim_chart()

    assert len(srv._state.chart_labels) == 2


# ── /api/config ─────────────────────────────────────────────────────────────

def test_api_config_returns_all_keys(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    required_keys = {
        "symbol", "timeframe", "trade_size_btc", "tp_long", "tp_short",
        "stop_loss_pct", "hard_cap_multiplier", "deep_swing", "mode",
    }
    assert required_keys.issubset(data.keys())


# ── /api/start double-start prevention ─────────────────────────────────────

def test_api_start_prevents_double_start(client):
    import threading
    import gui.server as srv

    # Simulate an already-running thread
    fake_thread = threading.Thread(target=lambda: None, daemon=True)
    fake_thread.start()
    fake_thread.join()  # make it NOT alive first — then we test alive path

    alive_event = threading.Event()
    stop_event = threading.Event()

    def _long_running():
        alive_event.set()
        stop_event.wait()

    real_thread = threading.Thread(target=_long_running, daemon=True)
    real_thread.start()
    alive_event.wait()

    with srv._lock:
        srv._bot_thread = real_thread

    r = client.post("/api/start")
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert "already running" in r.json()["msg"]

    stop_event.set()
    real_thread.join(timeout=2)


def test_api_start_succeeds_when_not_running(client):
    import gui.server as srv
    with patch.object(srv, "_run_bot", return_value=None):
        r = client.post("/api/start")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── /api/stop ───────────────────────────────────────────────────────────────

def test_api_stop_sets_stop_event(client):
    import gui.server as srv
    srv._stop_event.clear()
    r = client.stop = client.post("/api/stop")
    assert r.status_code == 200
    assert srv._stop_event.is_set()


# ── Dashboard HTML ──────────────────────────────────────────────────────────

def test_dashboard_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert b"BTC MACD Bot" in r.content


# ── WebSocket snapshot ──────────────────────────────────────────────────────

def test_ws_sends_state_snapshot(client):
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
    assert "price" in data
    assert "symbol" in data
    assert "status" in data
    assert "chart_labels" in data
    assert "trades" in data
