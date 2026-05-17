"""backend.conversion.alerts — Lead alert dispatcher.

Dispatches hot lead alerts to sales team via configurable webhook URL.
Includes retry logic with exponential backoff and Supabase logging.
Controlled by CONVERSION_TOOLS_ENABLED feature flag (default: false).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

# Import compatibility: works with sys.path (standalone) and package-relative (main.py)
try:
    from backend.supabase_client import supabase
except ImportError:
    try:
        from supabase_client import supabase
    except ImportError:
        supabase = None

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


def _is_conversion_enabled() -> bool:
    """Check if conversion tools are enabled via feature flag."""
    return os.getenv("CONVERSION_TOOLS_ENABLED", "false").lower() == "true"


class LeadAlertDispatcher:
    """Dispatches hot lead alerts to sales team via webhook.

    POSTs alert payload to LEAD_ALERT_WEBHOOK_URL with retry logic
    (3 attempts with exponential backoff). Logs all attempts to
    lead_alerts_log table in Supabase.

    When CONVERSION_TOOLS_ENABLED is not set (default false), alerts
    are logged to Supabase only — no webhook is sent.
    """

    MAX_RETRIES = 3
    DEFAULT_WEBHOOK_URL = ""

    def __init__(
        self,
        webhook_url: str | None = None,
        secret: str | None = None,
    ):
        """Initialize alert dispatcher.

        Args:
            webhook_url: Target webhook URL. If None, reads from env.
            secret: Optional shared secret for signature header.
        """
        self.webhook_url = webhook_url or os.getenv("LEAD_ALERT_WEBHOOK_URL", "")
        self.secret = secret or os.getenv("LEAD_ALERT_WEBHOOK_SECRET", "")
        self._conversion_enabled = _is_conversion_enabled()
        # Allow test injection of supabase mock
        self._supabase = None

    @property
    def _db(self):
        """Get the Supabase client (real or injected mock)."""
        return self._supabase if self._supabase is not None else supabase

    def send_alert(
        self,
        lead_id: str,
        score: int,
        payload: dict[str, Any],
        intention: str | None = None,
    ) -> dict[str, Any]:
        """Send a hot lead alert via webhook.

        If CONVERSION_TOOLS_ENABLED is false or webhook URL is not configured,
        logs to Supabase only and returns status='skipped'.

        Otherwise POSTs to webhook URL with retry logic (up to MAX_RETRIES).

        Args:
            lead_id: ID of the lead in Supabase.
            score: Lead score (0-100).
            payload: Full alert payload with lead data, session info, and qualification.
            intention: Lead intention classification.

        Returns:
            Dict with alert status and attempt info.
        """
        # Feature flag check: if disabled, log only
        if not self._conversion_enabled:
            self._log_alert(lead_id, "logged_only", payload, attempts=0)
            return {
                "success": False,
                "lead_id": lead_id,
                "status": "logged_only",
                "attempts": 0,
                "mensaje": "CONVERSION_TOOLS_ENABLED is false. Alert logged only.",
            }

        # Webhook URL check
        if not self.webhook_url:
            self._log_alert(lead_id, "skipped", payload, attempts=0)
            return {
                "success": False,
                "lead_id": lead_id,
                "status": "skipped",
                "attempts": 0,
                "mensaje": "LEAD_ALERT_WEBHOOK_URL not configured. Alert logged only.",
            }

        # Attempt webhook with retries
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._post_webhook(payload)
                if response and response.status_code < 400:
                    self._log_alert(lead_id, "enviada", payload, attempts=attempt)
                    return {
                        "success": True,
                        "lead_id": lead_id,
                        "status": "enviada",
                        "attempts": attempt,
                        "mensaje": "Alert sent successfully.",
                    }
                last_error = f"HTTP {response.status_code}" if response else "No response"
                print(f"[LeadAlertDispatcher] Attempt {attempt} failed: {last_error}")
            except Exception as ex:
                last_error = str(ex)
                print(f"[LeadAlertDispatcher] Attempt {attempt} error: {ex}")

            # Exponential backoff before retry (skip after last attempt)
            if attempt < self.MAX_RETRIES:
                backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                time.sleep(backoff)

        # All retries exhausted
        self._log_alert(lead_id, "fallida", payload, attempts=self.MAX_RETRIES)
        return {
            "success": False,
            "lead_id": lead_id,
            "status": "fallida",
            "attempts": self.MAX_RETRIES,
            "mensaje": f"Webhook failed after {self.MAX_RETRIES} attempts: {last_error}",
        }

    def _post_webhook(self, payload: dict[str, Any]):
        """POST payload to webhook URL.

        Returns:
            Response object or None if requests is not available.
        """
        if requests is None:
            raise ImportError("requests library not installed")

        headers = {"Content-Type": "application/json"}
        if self.secret:
            headers["X-Gotocloud-Signature"] = self.secret

        return requests.post(
            self.webhook_url,
            json=payload,
            headers=headers,
            timeout=10,
        )

    def _log_alert(
        self,
        lead_id: str,
        status: str,
        payload: dict[str, Any],
        attempts: int,
    ) -> None:
        """Log alert attempt to lead_alerts_log table."""
        db = self._db
        if db is None:
            print(f"[LeadAlertDispatcher] Supabase not available — alert not logged")
            return

        try:
            row = {
                "lead_id": lead_id,
                "webhook_url": self.webhook_url,
                "payload": payload,
                "status": status,
                "attempts": attempts,
            }
            result = db.table("lead_alerts_log").insert(row).execute()
            if result.data:
                print(f"[LeadAlertDispatcher] Alert logged: status={status}, lead={lead_id}")
        except Exception as ex:
            print(f"[LeadAlertDispatcher] Error logging alert: {ex}")

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
        return {
            "event": "lead_caliente",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lead": lead_data,
            "session": session_data,
            "calificacion": qualification,
        }
