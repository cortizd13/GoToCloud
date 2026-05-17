# Tests for PR #4: Dashboard Metrics Aggregation
# Update /dashboard/summary to aggregate from conversation_sessions by channel_type
# and include legacy sesiones data during transition.

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class MockExecResult:
    def __init__(self, data=None):
        self.data = data or []


class MockTable:
    """Mock Supabase table that records select calls and returns seeded data."""

    def __init__(self, seed_data=None):
        self._seed_data = seed_data or []
        self.calls = []

    def select(self, *cols):
        self.calls.append(("select", cols))
        return self

    def gte(self, col, val):
        self.calls.append(("gte", col, val))
        self._gte_col = col
        self._gte_val = val
        return self

    def lt(self, col, val):
        self.calls.append(("lt", col, val))
        self._lt_col = col
        self._lt_val = val
        return self

    def order(self, col, desc=False):
        self.calls.append(("order", col, desc))
        return self

    def execute(self):
        return MockExecResult(list(self._seed_data))


class MockSupabase:
    """Mock Supabase client that returns MockTable with seeded data per table."""

    def __init__(self, table_data=None):
        """
        table_data: dict mapping table name -> list of row dicts to return.
        """
        self._table_data = table_data or {}

    def table(self, name):
        seed = self._table_data.get(name, [])
        return MockTable(seed_data=seed)


def _today_bogota():
    """Return today's date in Bogota timezone (UTC-5)."""
    from backend.main import BOGOTA_TZ
    return datetime.now(BOGOTA_TZ)


def _make_session(channel_type="voice", status="completed", hours_ago=0):
    """Create a conversation_sessions row."""
    now = _today_bogota()
    started = now - timedelta(hours=hours_ago)
    ended = started + timedelta(minutes=5)
    return {
        "id": f"sess-{channel_type}-{hours_ago}",
        "channel_type": channel_type,
        "status": status,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "created_at": started.isoformat(),
    }


def _make_sesion(hours_ago=0, duracion=300):
    """Create a sesiones (legacy) row."""
    now = _today_bogota()
    started = now - timedelta(hours=hours_ago)
    return {
        "id": f"legacy-{hours_ago}",
        "started_at": started.isoformat(),
        "ended_at": (started + timedelta(seconds=duracion)).isoformat(),
        "duracion_segundos": duracion,
        "intention": "consulta",
        "score_lead": 5,
        "servicios_interes": ["migracion"],
        "recomendaciones": [],
        "created_at": started.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
#  Task 4.1: Dashboard aggregates from conversation_sessions
# ═══════════════════════════════════════════════════════════════


def test_dashboard_channels_from_conversation_sessions():
    """GET /dashboard/summary returns channel breakdown from conversation_sessions."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("voice", hours_ago=1),
            _make_session("voice", hours_ago=2),
            _make_session("webchat", hours_ago=3),
        ],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
        "sesiones": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        channels = data["channels"]
        channel_map = {c["label"]: c["value"] for c in channels}

        assert "Voice" in channel_map
        assert channel_map["Voice"] == 2
        assert "Webchat" in channel_map
        assert channel_map["Webchat"] == 1


def test_dashboard_total_includes_conversation_sessions():
    """Total volume includes conversation_sessions count."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("voice", hours_ago=1),
            _make_session("webchat", hours_ago=2),
            _make_session("webchat", hours_ago=3),
        ],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
        "sesiones": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        volume = data["overview"][0]  # "Volumen total"
        assert "3" in volume["value"]


# ═══════════════════════════════════════════════════════════════
#  Task 4.2: Include legacy sesiones during transition
# ═══════════════════════════════════════════════════════════════


def test_dashboard_includes_legacy_sesiones_in_total():
    """Total volume includes both conversation_sessions and sesiones (legacy)."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("webchat", hours_ago=1),
            _make_session("webchat", hours_ago=2),
        ],
        "sesiones": [
            _make_sesion(hours_ago=3),
            _make_sesion(hours_ago=4),
            _make_sesion(hours_ago=5),
        ],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        # 2 webchat + 3 legacy = 5 total
        volume = data["overview"][0]
        assert "5" in volume["value"]


def test_dashboard_legacy_sesiones_counted_as_voice():
    """Legacy sesiones rows are counted as voice in channel breakdown."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("webchat", hours_ago=1),
        ],
        "sesiones": [
            _make_sesion(hours_ago=2),
            _make_sesion(hours_ago=3),
        ],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        channels = data["channels"]
        channel_map = {c["label"]: c["value"] for c in channels}

        # 1 webchat + 2 legacy voice = voice:2, webchat:1
        assert channel_map.get("Voice", 0) == 2
        assert channel_map.get("Webchat", 0) == 1


def test_dashboard_source_reflects_both_tables():
    """Source breakdown shows counts from both conversation_sessions and sesiones."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("voice", hours_ago=1),
            _make_session("webchat", hours_ago=2),
        ],
        "sesiones": [
            _make_sesion(hours_ago=3),
        ],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        source = data["source"]
        assert source["sessions"] == 2  # conversation_sessions
        assert source["calls"] == 1     # sesiones (legacy)


# ═══════════════════════════════════════════════════════════════
#  Edge cases
# ═══════════════════════════════════════════════════════════════


def test_dashboard_empty_day_returns_zeros():
    """When no sessions today, dashboard returns zeros not errors."""
    from backend import main

    table_data = {
        "conversation_sessions": [],
        "sesiones": [],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        volume = data["overview"][0]
        assert volume["value"] == "0"
        assert data["channels"] == []


def test_dashboard_no_legacy_table_graceful():
    """When sesiones table returns empty (not yet migrated), dashboard still works."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("voice", hours_ago=1),
            _make_session("webchat", hours_ago=2),
        ],
        "sesiones": [],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        volume = data["overview"][0]
        assert "2" in volume["value"]


def test_dashboard_channel_percentages_sum_to_100():
    """Channel percentages should sum to approximately 100%."""
    from backend import main

    table_data = {
        "conversation_sessions": [
            _make_session("voice", hours_ago=1),
            _make_session("voice", hours_ago=2),
            _make_session("webchat", hours_ago=3),
        ],
        "sesiones": [],
        "messages": [],
        "analytics_events": [],
        "conversation_threads": [],
    }
    supabase = MockSupabase(table_data)

    with patch.object(main, "supabase", supabase):
        client = TestClient(main.app)
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        total_pct = sum(c["percentage"] for c in data["channels"])
        assert total_pct == 100
