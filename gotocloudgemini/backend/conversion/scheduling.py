"""backend.conversion.scheduling — Calendly integration stub.

Phase 1: Stub implementation with TODO markers.
Phase 2: Full Calendly API integration for event creation and webhook handling.
"""

from __future__ import annotations

from typing import Any


class CalendlyIntegration:
    """Integration with Calendly API for appointment scheduling.

    TODO: Implement real Calendly API calls:
    - GET /event_types to list available meeting types
    - POST /scheduling_links to create booking links
    - Webhook handler for event.created, event.canceled, event.invitee.created

    TODO: Store CALENDLY_API_KEY and CALENDLY_WEBHOOK_SECRET in .env.
    """

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.calendly.com"):
        """Initialize Calendly integration.

        Args:
            api_key: Calendly API key. If None, reads from env.
            base_url: Calendly API base URL.
        """
        # TODO: Load API key from environment variable
        self.api_key = api_key
        self.base_url = base_url

    def create_event(
        self,
        lead_id: str,
        service: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a scheduling link for a lead.

        TODO: Call Calendly API to create a scheduling link.
        TODO: Persist event to agent_citas table.

        Args:
            lead_id: ID of the lead in Supabase.
            service: Service of interest.
            preferences: Optional scheduling preferences.

        Returns:
            Dict with scheduling_link and status.
        """
        # TODO: Replace stub with real Calendly API call
        return {
            "success": False,
            "scheduling_link": "https://calendly.com/gotocloud/asesoria",
            "lead_id": lead_id,
            "estado": "pendiente",
            "mensaje": "Calendly integration not yet configured.",
        }

    def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle Calendly webhook events.

        TODO: Process webhook events:
        - invitee.created → update agent_citas.estado = 'confirmada'
        - event.canceled → update agent_citas.estado = 'cancelada'
        - event.ended → update agent_citas.estado = 'completada'

        Args:
            payload: Webhook event payload from Calendly.

        Returns:
            Dict with processing result.
        """
        # TODO: Replace stub with real webhook handler
        return {
            "success": False,
            "mensaje": "Webhook handler not yet implemented.",
        }
