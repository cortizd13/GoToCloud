"""Tests for PR #1: Schema Foundation — llamadas → sesiones rename.

These tests validate that supabase/schema.sql contains the correct
schema definitions after the rename. They parse the SQL file as text
(no live database required).
"""

from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"


@pytest.fixture(scope="module")
def schema_sql() -> str:
    """Load the full schema.sql content."""
    return SCHEMA_PATH.read_text(encoding="utf-8")


# ── REQ-1: Rename llamadas → sesiones ─────────────────────────────────────────


class TestTableRename:
    """SC-1.1: Rename table with data — verify schema reflects rename."""

    def test_sesiones_table_exists(self, schema_sql: str):
        """The renamed table 'sesiones' must be defined in schema.sql."""
        assert "public.sesiones" in schema_sql or "CREATE TABLE" in schema_sql
        # More specific: look for the CREATE TABLE or the table reference
        assert "sesiones" in schema_sql.lower()

    def test_llamadas_table_removed(self, schema_sql: str):
        """The old 'llamadas' table must NOT appear in schema.sql."""
        # Normalize: remove comments to avoid false positives
        lines = [
            line for line in schema_sql.splitlines()
            if not line.strip().startswith("--")
        ]
        code_only = "\n".join(lines)
        # 'llamadas' should not appear in any non-comment SQL statement
        assert "llamadas" not in code_only.lower(), (
            "Old table name 'llamadas' still present in schema.sql (non-comment lines)"
        )

    def test_sesiones_has_cliente_id_fk(self, schema_sql: str):
        """The sesiones table must keep the cliente_id FK to clientes."""
        assert "cliente_id" in schema_sql
        assert "REFERENCES clientes(id)" in schema_sql

    def test_sesiones_has_expected_columns(self, schema_sql: str):
        """Key columns from llamadas must be preserved in sesiones."""
        required_columns = [
            "started_at",
            "ended_at",
            "duracion_segundos",
            "resumen",
            "intention",
            "score_lead",
            "servicios_interes",
        ]
        for col in required_columns:
            assert col in schema_sql, f"Column '{col}' missing from schema"


# ── REQ-2: RLS policies for sesiones ──────────────────────────────────────────


class TestRLSPolicies:
    """SC-1.3: RLS still permits legacy inserts — verify policies exist."""

    def test_sesiones_rls_enabled(self, schema_sql: str):
        """RLS must be enabled on the sesiones table."""
        assert "ALTER TABLE public.sesiones" in schema_sql
        assert "ENABLE ROW LEVEL SECURITY" in schema_sql

    def test_anon_select_sesiones_policy(self, schema_sql: str):
        """SELECT policy for anon on sesiones must exist."""
        assert "anon_select_sesiones" in schema_sql
        assert "FOR SELECT USING (true)" in schema_sql

    def test_anon_insert_sesiones_policy(self, schema_sql: str):
        """INSERT policy for anon on sesiones must exist."""
        assert "anon_insert_sesiones" in schema_sql
        assert "FOR INSERT WITH CHECK (true)" in schema_sql

    def test_no_llamadas_rls_policies(self, schema_sql: str):
        """No RLS policies should reference the old 'llamadas' table."""
        lines = [
            line for line in schema_sql.splitlines()
            if not line.strip().startswith("--")
        ]
        code_only = "\n".join(lines)
        assert "llamadas" not in code_only.lower(), (
            "RLS policies still reference 'llamadas'"
        )

    def test_drop_policies_for_sesiones(self, schema_sql: str):
        """DROP POLICY IF EXISTS should reference sesiones (idempotent rerun)."""
        assert 'DROP POLICY IF EXISTS "anon_select_sesiones"' in schema_sql
        assert 'DROP POLICY IF EXISTS "anon_insert_sesiones"' in schema_sql


# ── REQ-13: Composite index for dashboard queries ─────────────────────────────


class TestIndexes:
    """Index for channel_type + started_at dashboard aggregation."""

    def test_composite_index_exists(self, schema_sql: str):
        """The composite index idx_conversation_sessions_channel_started must exist."""
        assert "idx_conversation_sessions_channel_started" in schema_sql

    def test_composite_index_columns(self, schema_sql: str):
        """The index must cover channel_type and started_at DESC."""
        # Find the index line
        for line in schema_sql.splitlines():
            if "idx_conversation_sessions_channel_started" in line:
                assert "channel_type" in line
                assert "started_at" in line
                break
        else:
            pytest.fail("Composite index definition not found")

    def test_index_on_conversation_sessions(self, schema_sql: str):
        """The index must be on the conversation_sessions table."""
        assert "ON public.conversation_sessions" in schema_sql


# ── Verification query updated ────────────────────────────────────────────────


class TestVerificationQuery:
    """The final SELECT verification should reference sesiones, not llamadas."""

    def test_verification_includes_sesiones(self, schema_sql: str):
        """Verification query should include sesiones table."""
        assert "'sesiones'" in schema_sql or '"sesiones"' in schema_sql

    def test_verification_excludes_llamadas(self, schema_sql: str):
        """Verification query should NOT include llamadas table."""
        lines = [
            line for line in schema_sql.splitlines()
            if not line.strip().startswith("--")
        ]
        code_only = "\n".join(lines)
        # Check in the verification SELECT section
        verification_section = code_only[code_only.find("Verificación"):]
        assert "llamadas" not in verification_section.lower()
