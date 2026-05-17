"""backend.conversion.crm — CRM provider interface and HubSpot stub.

Phase 1: Interface definition + HubSpot stub with TODO markers.
Phase 2: Full HubSpot API integration.

Design: Provider interface allows swapping HubSpot for Salesforce/Pipedream later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CRMProvider(ABC):
    """Abstract interface for CRM integrations.

    Implement this interface for each CRM provider (HubSpot, Salesforce, etc.).
    The interface defines the minimum contract required by conversion tools.
    """

    @abstractmethod
    def get_lead(self, identifier: str, identifier_type: str = "email") -> dict[str, Any]:
        """Look up a lead in the CRM by identifier.

        Args:
            identifier: Email, cedula, or CRM ID.
            identifier_type: Type of identifier ('email', 'cedula', 'crm_id').

        Returns:
            Dict with lead data if found, or cliente_encontrado=False.
        """
        ...

    @abstractmethod
    def create_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new lead in the CRM.

        Args:
            lead_data: Dict with name, email, phone, empresa, servicios_interes, etc.

        Returns:
            Dict with success status and CRM ID if created.
        """
        ...

    @abstractmethod
    def update_lead(self, crm_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an existing lead in the CRM.

        Args:
            crm_id: CRM identifier of the lead to update.
            updates: Dict of fields to update.

        Returns:
            Dict with success status.
        """
        ...


class HubSpotCRM(CRMProvider):
    """HubSpot CRM implementation.

    TODO: Implement real HubSpot API calls:
    - GET /crm/v3/objects/contacts/search for get_lead
    - POST /crm/v3/objects/contacts for create_lead
    - PATCH /crm/v3/objects/contacts/{crm_id} for update_lead

    TODO: Store HUBSPOT_API_KEY in .env.
    TODO: Implement field mapping between Supabase and HubSpot schemas.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize HubSpot CRM integration.

        Args:
            api_key: HubSpot API key. If None, reads from env.
        """
        # TODO: Load API key from environment variable
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"

    def get_lead(self, identifier: str, identifier_type: str = "email") -> dict[str, Any]:
        """Look up a contact in HubSpot.

        TODO: Call HubSpot search API.
        """
        # TODO: Replace stub with real HubSpot API call
        return {
            "success": False,
            "cliente_encontrado": False,
            "identifier": identifier,
            "mensaje": "HubSpot integration not yet configured.",
        }

    def create_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new contact in HubSpot.

        TODO: Map Supabase fields to HubSpot properties.
        TODO: Call HubSpot create contact API.
        """
        # TODO: Replace stub with real HubSpot API call
        return {
            "success": False,
            "crm_id": None,
            "lead_data": lead_data,
            "mensaje": "HubSpot integration not yet configured.",
        }

    def update_lead(self, crm_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an existing contact in HubSpot.

        TODO: Call HubSpot update contact API.
        """
        # TODO: Replace stub with real HubSpot API call
        return {
            "success": False,
            "crm_id": crm_id,
            "updates": updates,
            "mensaje": "HubSpot integration not yet configured.",
        }


def get_crm_provider(provider_type: str = "hubspot", **kwargs: Any) -> CRMProvider:
    """Factory function to get a CRM provider instance.

    Args:
        provider_type: Provider type ('hubspot', 'salesforce', etc.).
        **kwargs: Provider-specific configuration.

    Returns:
        CRMProvider instance.

    Raises:
        ValueError: If provider_type is not supported.
    """
    # TODO: Add support for additional providers
    providers = {
        "hubspot": HubSpotCRM,
    }

    if provider_type not in providers:
        raise ValueError(f"Unsupported CRM provider: {provider_type}")

    return providers[provider_type](**kwargs)
