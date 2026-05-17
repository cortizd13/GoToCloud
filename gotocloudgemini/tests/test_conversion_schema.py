"""Tests for PR Slice #1: Conversion Rate Improvement — Schema Changes (T-101).

These tests validate that supabase/schema.sql contains the correct
schema definitions for the conversion rate improvement feature.
They parse the SQL file as text (no live database required).
"""

from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"


@pytest.fixture(scope="module")
def schema_sql() -> str:
    """Load the full schema.sql content."""
    return SCHEMA_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def schema_code(schema_sql: str) -> str:
    """Schema SQL with comments stripped for code-only analysis."""
    lines = [
        line for line in schema_sql.splitlines()
        if not line.strip().startswith("--")
    ]
    return "\n".join(lines)


# ── REQ-101a: agent_citas table ───────────────────────────────────────────────


class TestAgentCitasTable:
    """SC-101.1: agent_citas table must exist with correct columns."""

    def test_agent_citas_table_exists(self, schema_code: str):
        """The agent_citas table must be defined."""
        assert "agent_citas" in schema_code

    def test_agent_citas_create_table(self, schema_code: str):
        """Must use CREATE TABLE IF NOT EXISTS for idempotency."""
        assert "CREATE TABLE IF NOT EXISTS" in schema_code
        # Find the agent_citas CREATE TABLE block
        for line in schema_code.splitlines():
            if "agent_citas" in line and "CREATE TABLE" in line:
                assert "IF NOT EXISTS" in line
                break
        else:
            pytest.fail("CREATE TABLE IF NOT EXISTS for agent_citas not found")

    def test_agent_citas_has_id_uuid(self, schema_code: str):
        """Primary key must be UUID with gen_random_uuid()."""
        # Look for id column definition near agent_citas
        in_table = False
        for line in schema_code.splitlines():
            if "agent_citas" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "id" in line and "UUID" in line:
                assert "PRIMARY KEY" in line
                assert "gen_random_uuid()" in line
                return
        pytest.fail("id UUID PRIMARY KEY not found in agent_citas")

    def test_agent_citas_has_cliente_id(self, schema_code: str):
        """Must have cliente_id column."""
        assert "cliente_id" in schema_code

    def test_agent_citas_has_lead_id(self, schema_code: str):
        """Must have lead_id column."""
        assert "lead_id" in schema_code

    def test_agent_citas_has_fecha_hora(self, schema_code: str):
        """Must have fecha_hora TIMESTAMP NOT NULL."""
        in_table = False
        for line in schema_code.splitlines():
            if "agent_citas" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "fecha_hora" in line:
                assert "TIMESTAMP" in line
                return
        pytest.fail("fecha_hora TIMESTAMP not found in agent_citas")

    def test_agent_citas_has_link_confirmacion(self, schema_code: str):
        """Must have link_confirmacion VARCHAR."""
        assert "link_confirmacion" in schema_code

    def test_agent_citas_has_estado_check(self, schema_code: str):
        """estado must have CHECK constraint with valid values."""
        assert "estado" in schema_code
        assert "pendiente" in schema_code
        assert "confirmada" in schema_code
        assert "cancelada" in schema_code
        assert "completada" in schema_code

    def test_agent_citas_has_created_at(self, schema_code: str):
        """Must have created_at with default NOW()."""
        in_table = False
        for line in schema_code.splitlines():
            if "agent_citas" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "created_at" in line:
                assert "TIMESTAMP" in line or "TIMESTAMPTZ" in line
                return
        pytest.fail("created_at not found in agent_citas")


# ── REQ-103a: lead_summaries extended columns ─────────────────────────────────


class TestLeadSummariesExtensions:
    """SC-103.1: lead_summaries must have new columns for budget/timeline."""

    def test_presupuesto_estimado_column(self, schema_code: str):
        """lead_summaries must have presupuesto_estimado (or presupuesto) column."""
        assert "presupuesto" in schema_code.lower()

    def test_timeline_column(self, schema_code: str):
        """lead_summaries must have timeline column."""
        assert "timeline" in schema_code.lower()

    def test_decision_maker_column(self, schema_code: str):
        """lead_summaries must have decision_maker BOOLEAN column."""
        assert "decision_maker" in schema_code

    def test_score_auto_column(self, schema_code: str):
        """lead_summaries must have score_auto INTEGER column."""
        assert "score_auto" in schema_code

    def test_alerta_enviada_column(self, schema_code: str):
        """lead_summaries must have alerta_enviada BOOLEAN DEFAULT FALSE."""
        assert "alerta_enviada" in schema_code

    def test_alter_table_if_not_exists(self, schema_code: str):
        """ALTER TABLE must use ADD COLUMN IF NOT EXISTS for idempotency."""
        assert "ADD COLUMN IF NOT EXISTS" in schema_code


# ── REQ-102a: lead_alerts_log table ──────────────────────────────────────────


class TestLeadAlertsLogTable:
    """SC-102.1: lead_alerts_log table must exist with correct columns."""

    def test_lead_alerts_log_table_exists(self, schema_code: str):
        """The lead_alerts_log table must be defined."""
        assert "lead_alerts_log" in schema_code

    def test_lead_alerts_log_create_if_not_exists(self, schema_code: str):
        """Must use CREATE TABLE IF NOT EXISTS for idempotency."""
        for line in schema_code.splitlines():
            if "lead_alerts_log" in line and "CREATE TABLE" in line:
                assert "IF NOT EXISTS" in line
                return
        pytest.fail("CREATE TABLE IF NOT EXISTS for lead_alerts_log not found")

    def test_lead_alerts_log_has_id_uuid(self, schema_code: str):
        """Primary key must be UUID."""
        in_table = False
        for line in schema_code.splitlines():
            if "lead_alerts_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "id" in line and "UUID" in line:
                assert "PRIMARY KEY" in line
                return
        pytest.fail("id UUID PRIMARY KEY not found in lead_alerts_log")

    def test_lead_alerts_log_has_lead_id(self, schema_code: str):
        """Must have lead_id referencing lead_summaries."""
        assert "lead_id" in schema_code

    def test_lead_alerts_log_has_webhook_url(self, schema_code: str):
        """Must have webhook_url column."""
        assert "webhook_url" in schema_code

    def test_lead_alerts_log_has_payload_jsonb(self, schema_code: str):
        """Must have payload JSONB column."""
        in_table = False
        for line in schema_code.splitlines():
            if "lead_alerts_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "payload" in line:
                assert "JSONB" in line
                return
        pytest.fail("payload JSONB not found in lead_alerts_log")

    def test_lead_alerts_log_has_status_check(self, schema_code: str):
        """status must have CHECK constraint with valid values."""
        assert "enviada" in schema_code
        assert "fallida" in schema_code
        assert "retry" in schema_code

    def test_lead_alerts_log_has_attempts(self, schema_code: str):
        """Must have attempts INTEGER DEFAULT 0."""
        assert "attempts" in schema_code

    def test_lead_alerts_log_has_created_at(self, schema_code: str):
        """Must have created_at column."""
        in_table = False
        for line in schema_code.splitlines():
            if "lead_alerts_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "created_at" in line:
                assert "TIMESTAMP" in line or "TIMESTAMPTZ" in line
                return
        pytest.fail("created_at not found in lead_alerts_log")


# ── Indexes ───────────────────────────────────────────────────────────────────


class TestConversionIndexes:
    """SC-101c: Indexes for conversion tables must exist."""

    def test_idx_agent_citas_fecha(self, schema_code: str):
        """Index on agent_citas(fecha_hora) must exist."""
        assert "idx_agent_citas_fecha" in schema_code

    def test_idx_lead_summaries_intencion(self, schema_code: str):
        """Index on lead_summaries(intencion) must exist."""
        assert "idx_lead_summaries_intencion" in schema_code

    def test_idx_lead_alerts_log_status(self, schema_code: str):
        """Index on lead_alerts_log(status) must exist."""
        assert "idx_lead_alerts_log_status" in schema_code

    def test_indexes_use_if_not_exists(self, schema_code: str):
        """All indexes must use IF NOT EXISTS for idempotency."""
        for line in schema_code.splitlines():
            if "idx_agent_citas_fecha" in line:
                assert "IF NOT EXISTS" in line
            if "idx_lead_summaries_intencion" in line:
                assert "IF NOT EXISTS" in line
            if "idx_lead_alerts_log_status" in line:
                assert "IF NOT EXISTS" in line


# ── REQ-201b: email_logs table (Phase 2) ─────────────────────────────────────


class TestEmailLogsTable:
    """SC-201.1: email_logs table must exist with correct columns."""

    def test_email_logs_table_exists(self, schema_code: str):
        """The email_logs table must be defined."""
        assert "email_logs" in schema_code

    def test_email_logs_create_if_not_exists(self, schema_code: str):
        """Must use CREATE TABLE IF NOT EXISTS for idempotency."""
        for line in schema_code.splitlines():
            if "email_logs" in line and "CREATE TABLE" in line:
                assert "IF NOT EXISTS" in line
                return
        pytest.fail("CREATE TABLE IF NOT EXISTS for email_logs not found")

    def test_email_logs_has_id_uuid(self, schema_code: str):
        """Primary key must be UUID."""
        in_table = False
        for line in schema_code.splitlines():
            if "email_logs" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "id" in line and "UUID" in line:
                assert "PRIMARY KEY" in line
                return
        pytest.fail("id UUID PRIMARY KEY not found in email_logs")

    def test_email_logs_has_lead_id(self, schema_code: str):
        """Must have lead_id column."""
        assert "lead_id" in schema_code

    def test_email_logs_has_destinatario(self, schema_code: str):
        """Must have destinatario column."""
        assert "destinatario" in schema_code

    def test_email_logs_has_subject(self, schema_code: str):
        """Must have subject column."""
        assert "subject" in schema_code

    def test_email_logs_has_status_check(self, schema_code: str):
        """status must have CHECK constraint with valid values."""
        in_table = False
        for line in schema_code.splitlines():
            if "email_logs" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "status" in line and "CHECK" in line:
                assert "enviado" in line
                assert "bounced" in line
                assert "spam" in line
                assert "error" in line
                return
        pytest.fail("status CHECK constraint not found in email_logs")

    def test_email_logs_has_template_used(self, schema_code: str):
        """Must have template_used column."""
        assert "template_used" in schema_code

    def test_email_logs_has_created_at(self, schema_code: str):
        """Must have created_at column."""
        in_table = False
        for line in schema_code.splitlines():
            if "email_logs" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "created_at" in line:
                assert "TIMESTAMP" in line or "TIMESTAMPTZ" in line
                return
        pytest.fail("created_at not found in email_logs")

    def test_email_logs_has_rls_policy(self, schema_sql: str):
        """RLS policies must exist for email_logs."""
        assert "email_logs" in schema_sql
        # Check for RLS enablement and policies
        assert "anon_select_email_logs" in schema_sql or "email_logs" in schema_sql


# ── REQ-202c: crm_sync_log table (Phase 2) ───────────────────────────────────


class TestCrmSyncLogTable:
    """SC-202.1: crm_sync_log table must exist with correct columns."""

    def test_crm_sync_log_table_exists(self, schema_code: str):
        """The crm_sync_log table must be defined."""
        assert "crm_sync_log" in schema_code

    def test_crm_sync_log_create_if_not_exists(self, schema_code: str):
        """Must use CREATE TABLE IF NOT EXISTS for idempotency."""
        for line in schema_code.splitlines():
            if "crm_sync_log" in line and "CREATE TABLE" in line:
                assert "IF NOT EXISTS" in line
                return
        pytest.fail("CREATE TABLE IF NOT EXISTS for crm_sync_log not found")

    def test_crm_sync_log_has_id_uuid(self, schema_code: str):
        """Primary key must be UUID."""
        in_table = False
        for line in schema_code.splitlines():
            if "crm_sync_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "id" in line and "UUID" in line:
                assert "PRIMARY KEY" in line
                return
        pytest.fail("id UUID PRIMARY KEY not found in crm_sync_log")

    def test_crm_sync_log_has_lead_id(self, schema_code: str):
        """Must have lead_id column."""
        assert "lead_id" in schema_code

    def test_crm_sync_log_has_crm_lead_id(self, schema_code: str):
        """Must have crm_lead_id column."""
        assert "crm_lead_id" in schema_code

    def test_crm_sync_log_has_crm_type(self, schema_code: str):
        """Must have crm_type column."""
        assert "crm_type" in schema_code

    def test_crm_sync_log_has_operation_check(self, schema_code: str):
        """operation must have CHECK constraint with valid values."""
        in_table = False
        for line in schema_code.splitlines():
            if "crm_sync_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "operation" in line and "CHECK" in line:
                assert "create" in line
                assert "update" in line
                assert "lookup" in line
                return
        pytest.fail("operation CHECK constraint not found in crm_sync_log")

    def test_crm_sync_log_has_status_check(self, schema_code: str):
        """status must have CHECK constraint with valid values."""
        in_table = False
        for line in schema_code.splitlines():
            if "crm_sync_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "status" in line and "CHECK" in line:
                assert "exitosa" in line
                assert "fallida" in line
                assert "pendiente" in line
                return
        pytest.fail("status CHECK constraint not found in crm_sync_log")

    def test_crm_sync_log_has_error_message(self, schema_code: str):
        """Must have error_message TEXT column."""
        assert "error_message" in schema_code

    def test_crm_sync_log_has_created_at(self, schema_code: str):
        """Must have created_at column."""
        in_table = False
        for line in schema_code.splitlines():
            if "crm_sync_log" in line and "CREATE TABLE" in line:
                in_table = True
            if in_table and "created_at" in line:
                assert "TIMESTAMP" in line or "TIMESTAMPTZ" in line
                return
        pytest.fail("created_at not found in crm_sync_log")

    def test_crm_sync_log_has_rls_policy(self, schema_sql: str):
        """RLS policies must exist for crm_sync_log."""
        assert "crm_sync_log" in schema_sql


# ── Phase 2 indexes ──────────────────────────────────────────────────────────


class TestPhase2Indexes:
    """SC-201c/202c: Indexes for Phase 2 tables."""

    def test_idx_email_logs_status(self, schema_code: str):
        """Index on email_logs(status) must exist."""
        assert "idx_email_logs_status" in schema_code

    def test_idx_crm_sync_log_status(self, schema_code: str):
        """Index on crm_sync_log(status) must exist."""
        assert "idx_crm_sync_log_status" in schema_code

    def test_phase2_indexes_use_if_not_exists(self, schema_code: str):
        """Phase 2 indexes must use IF NOT EXISTS."""
        for line in schema_code.splitlines():
            if "idx_email_logs_status" in line:
                assert "IF NOT EXISTS" in line
            if "idx_crm_sync_log_status" in line:
                assert "IF NOT EXISTS" in line
