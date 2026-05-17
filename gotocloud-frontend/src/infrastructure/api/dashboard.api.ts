import type { ClientRecord, ClientSession, DashboardSummary } from "../../domain/dashboard";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getDashboardSummary(
  signal?: AbortSignal,
): Promise<DashboardSummary> {
  const response = await fetch(`${API_BASE_URL}/dashboard/summary`, { signal });

  if (!response.ok) {
    let message = "No se pudo cargar la información del dashboard";
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return (await response.json()) as DashboardSummary;
}

export async function getClients(): Promise<{ clients: ClientRecord[] }> {
  const response = await fetch(`${API_BASE_URL}/dashboard/clients`);
  if (!response.ok) throw new Error("No se pudieron cargar los clientes");
  return (await response.json()) as { clients: ClientRecord[] };
}

export async function getClientSessions(
  clientId: number,
): Promise<{ sessions: ClientSession[] }> {
  const response = await fetch(
    `${API_BASE_URL}/dashboard/clients/${clientId}/sessions`,
  );
  if (!response.ok) throw new Error("No se pudo cargar el historial");
  return (await response.json()) as { sessions: ClientSession[] };
}
