"""backend.conversion.alerts — Lead alert dispatcher stub.

Phase 1: Stub implementation with TODO markers.
Phase 2: Real webhook dispatch with retry logic and Supabase logging.
"""

from __future__ import annotations

from typing import Any


class LeadAlertDispatcher:
    """Dispatches hot lead alerts to sales team via webhook.

    TODO: Implement real webhook POST with:
    - Configurable URL from LEAD_ALERT_WEBHOOK_URL env var
    - X-Gotocloud-Signature header for verification
    - Retry logic with exponential backoff (3 attempts max)
    - Logging to lead_alerts_log table in Supabase

    TODO: Handle graceful degrade when webhook URL is not configured.
    """

    MAX_RETRIES = 3

    def __init__(self, webhook_url: str | None = None, secret: str | None = None):
        """Initialize alert dispatcher.

        Args:
            webhook_url: Target webhook URL. If None, reads from env.
            secret: Optional shared secret for signature header.
        """
        # TODO: Load webhook URL and secret from environment variables
        self.webhook_url = webhook_url
        self.secret = secret

    def send_alert(
        self,
        lead_id: str,
        score: int,
        payload: dict[str, Any],
        intention: str | None = None,
    ) -> dict[str, Any]:
        """Send a hot lead alert via webhook.

        TODO: POST payload to webhook URL with retry logic.
        TODO: Log attempt to lead_alerts_log table.

        Args:
            lead_id: ID of the lead in Supabase.
            score: Lead score (0-100).
            payload: Full alert payload with lead data, session info, and qualification.
            intention: Lead intention classification.

        Returns:
            Dict with alert status and attempt info.
        """
        # TODO: Replace stub with real webhook dispatch
        if not self.webhook_url:
            return {
                "success": False,
                "lead_id": lead_id,
                "status": "skipped",
                "mensaje": "LEAD_ALERT_WEBHOOK_URL not configured. Alert logged only.",
            }

        return {
            "success": False,
            "lead_id": lead_id,
            "status": "pending",
            "attempts": 0,
            "mensaje": "Webhook dispatch not yet implemented.",
        }

    def _build_payload(
        self,
        lead_id: str,
        score: int,
        lead_data: dict[str, Any],
        session_data: dict[str, Any],
        qualification: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the standard alert payload structure.

        Args:
            lead_id: Lead identifier.
            score: Lead score.
            lead_data: Lead contact information.
            session_data: Session metadata.
            qualification: Budget, timeline, urgency data.

        Returns:
            Standardized alert payload dict.
        """
        # TODO: Add timestamp generation
        return {
            "event": "lead_caliente",
            "timestamp": "",  # TODO: Generate ISO 8601 timestamp
            "lead": lead_data,
            "session": session_data,
            "calificacion": qualification,
        }
