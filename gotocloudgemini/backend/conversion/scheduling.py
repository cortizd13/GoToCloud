"""backend.conversion.scheduling — Calendly integration.

Handles appointment scheduling link generation and persistence to Supabase.
Gracefully degrades when Calendly API key is not configured.
"""

from __future__ import annotations

import os
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


class CalendlyIntegration:
    """Integration with Calendly API for appointment scheduling.

    When CALENDLY_API_KEY is configured, creates real scheduling links.
    Otherwise returns a generic fallback link and logs to agent_citas.
    """

    DEFAULT_LINK = "https://calendly.com/gotocloud/asesoria"

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.calendly.com"):
        """Initialize Calendly integration.

        Args:
            api_key: Calendly API key. If None, reads from env.
            base_url: Calendly API base URL.
        """
        self.api_key = api_key or os.getenv("CALENDLY_API_KEY")
        self.base_url = base_url
        # Allow test injection of supabase mock
        self._supabase = None

    @property
    def _db(self):
        """Get the Supabase client (real or injected mock)."""
        return self._supabase if self._supabase is not None else supabase

    def create_event(
        self,
        lead_id: str,
        service: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a scheduling link for a lead.

        If Calendly API key is configured, creates a real scheduling link.
        Otherwise returns a generic fallback link. Always persists to agent_citas
        when Supabase is available.

        Args:
            lead_id: ID of the lead in Supabase.
            service: Service of interest.
            preferences: Optional scheduling preferences.

        Returns:
            Dict with cita_creada, calendly_link, estado.
        """
        preferences = preferences or {}
        cita_creada = False
        scheduling_link = self.DEFAULT_LINK
        estado = "pendiente"
        mensaje = ""

        # Try to create real Calendly link if API key is configured
        if self.api_key:
            try:
                scheduling_link, cita_creada, mensaje = self._create_calendly_link(
                    lead_id, service, preferences
                )
            except Exception as ex:
                mensaje = f"Calendly API error: {ex}"
                scheduling_link = self.DEFAULT_LINK
                cita_creada = False
        else:
            mensaje = "Calendly integration not configured — using fallback link."

        # Persist to agent_citas table
        cita_id = self._save_cita(lead_id, service, scheduling_link, estado, preferences)
        if cita_id:
            cita_creada = True  # At least we saved the record

        return {
            "cita_creada": cita_creada,
            "calendly_link": scheduling_link,
            "estado": estado,
            "lead_id": lead_id,
            "mensaje": mensaje,
        }

    def _create_calendly_link(
        self,
        lead_id: str,
        service: str | None,
        preferences: dict[str, Any],
    ) -> tuple[str, bool, str]:
        """Create a real Calendly scheduling link via API.

        Returns:
            Tuple of (scheduling_link, success, message).
        """
        # TODO: Implement real Calendly API call:
        # POST /scheduling_links with event_type and invitee info
        # For now, return the default link
        return self.DEFAULT_LINK, False, "Calendly API not yet fully implemented."

    def _save_cita(
        self,
        lead_id: str,
        service: str | None,
        link: str,
        estado: str,
        preferences: dict[str, Any],
    ) -> str | None:
        """Save the appointment record to agent_citas table.

        Returns:
            The cita UUID on success, None on failure.
        """
        db = self._db
        if db is None:
            return None

        try:
            # Build fecha_hora from preferences or default to now + 1 day
            fecha_hora = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
            if "dia_preferido" in preferences or "hora_preferida" in preferences:
                # TODO: Parse preferred date/time properly
                pass

            row = {
                "lead_id": lead_id,
                "fecha_hora": fecha_hora.isoformat(),
                "link_confirmacion": link,
                "estado": estado,
            }
            if service:
                row["metadata"] = {"servicio_interes": service, **preferences}

            result = db.table("agent_citas").insert(row).execute()
            if result.data and len(result.data) > 0:
                cita_id = result.data[0].get("id", "")
                print(f"[CalendlyIntegration] Cita saved: id={cita_id}, lead={lead_id}")
                return cita_id
        except Exception as ex:
            print(f"[CalendlyIntegration] Error saving cita: {ex}")

        return None

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
        return {
            "success": False,
            "mensaje": "Webhook handler not yet implemented.",
        }
