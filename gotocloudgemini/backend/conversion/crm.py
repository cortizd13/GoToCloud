"""backend.conversion.crm — CRM provider interface and HubSpot implementation.

Phase 2: Full HubSpot API integration via REST API.
Supports get_lead, create_lead, update_lead with crm_sync_log logging.
Graceful degrade when HUBSPOT_API_KEY is not set.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

# Import compatibility: works with sys.path (standalone) and package-relative (main.py)
try:
    from backend.supabase_client import supabase
except ImportError:
    try:
        from supabase_client import supabase
    except ImportError:
        supabase = None


class CRMProvider:
    """Abstract interface for CRM integrations.

    Implement this interface for each CRM provider (HubSpot, Salesforce, etc.).
    The interface defines the minimum contract required by conversion tools.
    """

    def get_lead(self, identifier: str, identifier_type: str = "email") -> dict[str, Any]:
        """Look up a lead in the CRM by identifier.

        Args:
            identifier: Email, cedula, or CRM ID.
            identifier_type: Type of identifier ('email', 'cedula', 'crm_id').

        Returns:
            Dict with lead data if found, or cliente_encontrado=False.
        """
        raise NotImplementedError

    def create_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new lead in the CRM.

        Args:
            lead_data: Dict with name, email, phone, empresa, servicios_interes, etc.

        Returns:
            Dict with success status and CRM ID if created.
        """
        raise NotImplementedError

    def update_lead(self, crm_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an existing lead in the CRM.

        Args:
            crm_id: CRM identifier of the lead to update.
            updates: Dict of fields to update.

        Returns:
            Dict with success status.
        """
        raise NotImplementedError


class HubSpotCRM(CRMProvider):
    """HubSpot CRM implementation via REST API.

    Uses HubSpot CRM API v3:
    - POST /crm/v3/objects/contacts/search for get_lead
    - POST /crm/v3/objects/contacts for create_lead
    - PATCH /crm/v3/objects/contacts/{crm_id} for update_lead
    """

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, api_key: str | None = None):
        """Initialize HubSpot CRM integration.

        Args:
            api_key: HubSpot API key. If None, reads from HUBSPOT_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("HUBSPOT_API_KEY")

    def get_lead(self, identifier: str, identifier_type: str = "email") -> dict[str, Any]:
        """Look up a contact in HubSpot by email or property.

        Args:
            identifier: Email address or other identifier.
            identifier_type: Type of identifier ('email', 'cedula', 'crm_id').

        Returns:
            Dict with success, cliente_encontrado, and contact data if found.
        """
        if not self.api_key:
            return {
                "success": False,
                "cliente_encontrado": False,
                "identifier": identifier,
                "razon": "crm_no_configurado",
            }

        try:
            # Map identifier_type to HubSpot property
            property_map = {
                "email": "email",
                "cedula": "cedula",
                "crm_id": "hs_object_id",
            }
            hs_property = property_map.get(identifier_type, "email")

            # Search contacts by filter
            url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
            payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": hs_property,
                        "operator": "EQ",
                        "value": identifier,
                    }]
                }],
                "properties": ["email", "firstname", "lastname", "phone", "company", "cedula"],
            }

            response = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results:
                    contact = results[0]
                    props = contact.get("properties", {})
                    self._log_sync(
                        identifier=identifier,
                        operation="lookup",
                        status="exitosa",
                        crm_id=contact.get("id"),
                    )
                    return {
                        "success": True,
                        "cliente_encontrado": True,
                        "crm_id": contact.get("id"),
                        "datos": {
                            "nombre": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                            "email": props.get("email", ""),
                            "telefono": props.get("phone", ""),
                            "empresa": props.get("company", ""),
                            "ultima_interaccion": contact.get("updatedAt", ""),
                        },
                    }
                else:
                    self._log_sync(
                        identifier=identifier,
                        operation="lookup",
                        status="exitosa",
                        crm_id=None,
                    )
                    return {
                        "success": True,
                        "cliente_encontrado": False,
                        "identifier": identifier,
                    }
            else:
                self._log_sync(
                    identifier=identifier,
                    operation="lookup",
                    status="fallida",
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                )
                return {
                    "success": False,
                    "cliente_encontrado": False,
                    "identifier": identifier,
                    "mensaje": f"HubSpot API error: HTTP {response.status_code}",
                }

        except Exception as ex:
            self._log_sync(
                identifier=identifier,
                operation="lookup",
                status="fallida",
                error=str(ex),
            )
            return {
                "success": False,
                "cliente_encontrado": False,
                "identifier": identifier,
                "mensaje": str(ex),
            }

    def create_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new contact in HubSpot.

        Maps Supabase fields to HubSpot properties:
        - nombre → firstname + lastname (split on first space)
        - email → email
        - telefono → phone
        - empresa → company

        Args:
            lead_data: Dict with nombre, email, telefono, empresa, etc.

        Returns:
            Dict with success status and CRM ID if created.
        """
        if not self.api_key:
            return {
                "success": False,
                "crm_id": None,
                "razon": "crm_no_configurado",
            }

        try:
            # Map fields to HubSpot properties
            nombre = lead_data.get("nombre", "")
            name_parts = nombre.split(" ", 1)
            properties = {
                "firstname": name_parts[0] if name_parts else "",
                "lastname": name_parts[1] if len(name_parts) > 1 else "",
                "email": lead_data.get("email", ""),
                "phone": lead_data.get("telefono", ""),
                "company": lead_data.get("empresa", ""),
            }

            url = f"{self.BASE_URL}/crm/v3/objects/contacts"
            payload = {"properties": properties}

            response = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            if response.status_code in (200, 201):
                data = response.json()
                crm_id = data.get("id")
                self._log_sync(
                    identifier=lead_data.get("email", ""),
                    operation="create",
                    status="exitosa",
                    crm_id=crm_id,
                )
                return {
                    "success": True,
                    "crm_id": crm_id,
                    "lead_data": lead_data,
                }
            else:
                self._log_sync(
                    identifier=lead_data.get("email", ""),
                    operation="create",
                    status="fallida",
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                )
                return {
                    "success": False,
                    "crm_id": None,
                    "mensaje": f"HubSpot API error: HTTP {response.status_code}",
                }

        except Exception as ex:
            self._log_sync(
                identifier=lead_data.get("email", ""),
                operation="create",
                status="fallida",
                error=str(ex),
            )
            return {
                "success": False,
                "crm_id": None,
                "mensaje": str(ex),
            }

    def update_lead(self, crm_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an existing contact in HubSpot.

        Args:
            crm_id: CRM identifier of the lead to update.
            updates: Dict of fields to update.

        Returns:
            Dict with success status.
        """
        if not self.api_key:
            return {
                "success": False,
                "crm_id": crm_id,
                "razon": "crm_no_configurado",
            }

        try:
            # Map field names to HubSpot properties
            hs_properties = {}
            for key, value in updates.items():
                mapping = {
                    "nombre": "firstname",
                    "telefono": "phone",
                    "empresa": "company",
                    "email": "email",
                }
                hs_key = mapping.get(key, key)
                hs_properties[hs_key] = value

            url = f"{self.BASE_URL}/crm/v3/objects/contacts/{crm_id}"
            payload = {"properties": hs_properties}

            response = requests.patch(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            if response.status_code in (200, 201):
                self._log_sync(
                    identifier=crm_id,
                    operation="update",
                    status="exitosa",
                    crm_id=crm_id,
                )
                return {"success": True, "crm_id": crm_id}
            else:
                self._log_sync(
                    identifier=crm_id,
                    operation="update",
                    status="fallida",
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                )
                return {
                    "success": False,
                    "crm_id": crm_id,
                    "mensaje": f"HubSpot API error: HTTP {response.status_code}",
                }

        except Exception as ex:
            self._log_sync(
                identifier=crm_id,
                operation="update",
                status="fallida",
                error=str(ex),
            )
            return {
                "success": False,
                "crm_id": crm_id,
                "mensaje": str(ex),
            }

    def _log_sync(
        self,
        identifier: str,
        operation: str,
        status: str,
        crm_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Log CRM sync attempt to crm_sync_log table."""
        if supabase is None:
            return

        try:
            log_data = {
                "crm_lead_id": crm_id,
                "crm_type": "hubspot",
                "operation": operation,
                "status": status,
            }
            if error:
                log_data["error_message"] = error
            supabase.table("crm_sync_log").insert(log_data).execute()
        except Exception as ex:
            print(f"[HubSpotCRM] Error logging to crm_sync_log: {ex}")


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
    providers = {
        "hubspot": HubSpotCRM,
    }

    if provider_type not in providers:
        raise ValueError(f"Unsupported CRM provider: {provider_type}")

    return providers[provider_type](**kwargs)
