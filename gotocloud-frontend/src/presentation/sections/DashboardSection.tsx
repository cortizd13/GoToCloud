import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FiAlertCircle,
  FiChevronDown,
  FiChevronUp,
  FiDatabase,
  FiDownload,
  FiFileText,
  FiRefreshCw,
  FiSearch,
  FiX,
} from "react-icons/fi";
import type {
  ClientRecord,
  ClientSession,
  DashboardBreakdownItem,
  DashboardHourlyPoint,
  DashboardLead,
  DashboardSummary,
} from "../../domain/dashboard";
import {
  getClientSessions,
  getClients,
  getDashboardSummary,
} from "../../infrastructure/api/dashboard.api";
import "./DashboardSection.css";

type NavSection = "resumen" | "clientes" | "leads";

type DashboardState =
  | { status: "loading"; data: DashboardSummary | null; error: null }
  | { status: "ready"; data: DashboardSummary; error: null }
  | { status: "error"; data: DashboardSummary | null; error: string };

const emptySummary: DashboardSummary = {
  generatedAt: new Date().toISOString(),
  range: "today",
  overview: [
    {
      id: "volume",
      label: "Volumen total",
      value: "0",
      detail: "conversaciones hoy · vs ayer",
      trend: { value: "0%", direction: "flat" },
    },
    {
      id: "csat",
      label: "CSAT promedio",
      value: "N/D",
      detail: "de 5.0 · eventos Supabase",
      trend: { value: "N/D", direction: "flat" },
    },
    {
      id: "fcr",
      label: "First contact res.",
      value: "N/D",
      detail: "resuelto sin escalar",
      trend: { value: "N/D", direction: "flat" },
    },
    {
      id: "aht",
      label: "AHT promedio",
      value: "N/D",
      detail: "tiempo promedio de manejo",
      trend: { value: "N/D", direction: "flat" },
    },
  ],
  volumeByHour: Array.from({ length: 24 }, (_, hour) => ({
    hour: `${String(hour).padStart(2, "0")}:00`,
    conversations: 0,
    sentimentPositive: 0,
    sentimentNegative: 0,
  })),
  contactReasons: [],
  channels: [],
  hotLeads: [],
  escalationCandidates: [],
  recommendations: [],
  source: { sessions: 0, calls: 0, messages: 0, events: 0 },
};

function formatGeneratedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin sincronizar";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(d);
}

function formatDuration(seconds: number | null): string {
  if (!seconds || seconds === 0) return "N/D";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function getMaxVolume(points: DashboardHourlyPoint[]): number {
  return Math.max(1, ...points.map((p) => p.conversations));
}

function downloadReport(summary: DashboardSummary) {
  const blob = new Blob([JSON.stringify(summary, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `gotocloud-dashboard-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function generateSessionPDF(client: ClientRecord, session: ClientSession) {
  const win = window.open("", "_blank");
  if (!win) return;

  const servicesHtml =
    session.serviciosInteres.length > 0
      ? session.serviciosInteres
          .map((s) => `<span class="tag">${escapeHtml(s)}</span>`)
          .join("")
      : "<em>Sin servicios registrados</em>";

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Sesión — ${escapeHtml(client.nombre)}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#172033;padding:40px;max-width:720px;margin:0 auto}
.logo{color:#10223d;font-size:1.2rem;font-weight:800;border-bottom:2px solid #e0e6ef;padding-bottom:16px;margin-bottom:28px}
.logo span{display:block;color:#227f9c;font-size:0.75rem;font-weight:700;text-transform:uppercase;margin-top:4px}
h1{font-size:1.5rem;color:#10223d;margin-bottom:6px}
.subtitle{color:#64748b;font-size:0.88rem;margin-bottom:28px}
.section{margin-bottom:24px}
.section h2{font-size:0.8rem;font-weight:700;color:#227f9c;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px}
.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.info-item label{display:block;font-size:0.72rem;color:#64748b;font-weight:700;margin-bottom:2px}
.info-item p{font-size:0.9rem;color:#172033;font-weight:600}
.badge{display:inline-block;border-radius:999px;padding:3px 10px;font-size:0.78rem;font-weight:700}
.caliente{background:#fee2e2;color:#991b1b}
.calida{background:#fef9c3;color:#854d0e}
.fria{background:#e0f2fe;color:#0369a1}
.box{background:#f7f9fc;border:1px solid #e3eaf3;border-radius:8px;padding:16px;font-size:0.9rem;line-height:1.6;color:#27384f}
.tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{background:#edf2fb;border-radius:999px;color:#3d5580;font-size:0.78rem;font-weight:700;padding:4px 10px}
.rec{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;font-size:0.88rem;line-height:1.6;color:#15803d}
.footer{margin-top:36px;padding-top:14px;border-top:1px solid #e0e6ef;color:#94a3b8;font-size:0.75rem}
@media print{body{padding:20px}}
</style>
</head>
<body>
<div class="logo">GoToCloud<span>Contact Center IA — Resumen de sesión</span></div>
<h1>${escapeHtml(client.nombre)}</h1>
<p class="subtitle">Generado el ${new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeStyle: "short" }).format(new Date())}</p>
<div class="section">
<h2>Información del cliente</h2>
<div class="info-grid">
<div class="info-item"><label>Empresa</label><p>${escapeHtml(client.empresa || "—")}</p></div>
<div class="info-item"><label>Teléfono</label><p>${escapeHtml(client.telefono || "—")}</p></div>
<div class="info-item"><label>Cédula</label><p>${escapeHtml(client.cedula || "—")}</p></div>
</div>
</div>
<div class="section">
<h2>Datos de la sesión</h2>
<div class="info-grid">
<div class="info-item"><label>Fecha inicio</label><p>${formatDate(session.startedAt)}</p></div>
<div class="info-item"><label>Duración</label><p>${formatDuration(session.duracionSegundos)}</p></div>
<div class="info-item"><label>Score lead</label><p>${session.scoreLead > 0 ? session.scoreLead + " / 100" : "N/D"}</p></div>
<div class="info-item"><label>Intención</label><p><span class="badge ${session.intention}">${session.intention}</span></p></div>
</div>
</div>
${session.resumen ? `<div class="section"><h2>Resumen de la conversación</h2><div class="box">${escapeHtml(session.resumen)}</div></div>` : ""}
${session.serviciosInteres.length > 0 ? `<div class="section"><h2>Servicios de interés</h2><div class="tags">${servicesHtml}</div></div>` : ""}
${session.recomendaciones ? `<div class="section"><h2>Recomendaciones del agente</h2><div class="rec">${escapeHtml(session.recomendaciones)}</div></div>` : ""}
<div class="footer">GoToCloud · Reporte generado automáticamente por Camila IA</div>
<script>setTimeout(()=>window.print(),400)</script>
</body>
</html>`;

  win.document.write(html);
  win.document.close();
}

function BreakdownList({
  emptyLabel,
  items,
}: {
  emptyLabel: string;
  items: DashboardBreakdownItem[];
}) {
  if (!items.length) {
    return <p className="dashboard-empty">{emptyLabel}</p>;
  }
  return (
    <ul className="dashboard-breakdown">
      {items.map((item) => (
        <li className="dashboard-breakdown__item" key={item.label}>
          <div className="dashboard-breakdown__row">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <div className="dashboard-progress" aria-hidden="true">
            <span style={{ width: `${Math.min(100, item.percentage)}%` }} />
          </div>
          <small>{item.percentage}%</small>
        </li>
      ))}
    </ul>
  );
}

function waLink(telefono: string): string {
  const digits = telefono.replace(/\D/g, "");
  const normalized = digits.startsWith("57") ? digits : `57${digits}`;
  return `https://wa.me/${normalized}`;
}

function LeadList({
  leads,
  showRec,
}: {
  leads: DashboardLead[];
  showRec: boolean;
}) {
  if (!leads.length) {
    return (
      <p className="dashboard-empty">
        {showRec
          ? "Sin candidatos a escalado registrados."
          : "Sin leads calientes registrados."}
      </p>
    );
  }
  return (
    <ul className="dashboard-leads">
      {leads.map((lead) => (
        <li className="dashboard-lead" key={lead.id}>
          <div className="dashboard-lead__info">
            <strong>{lead.nombre}</strong>
            {lead.empresa && <span>{lead.empresa}</span>}
            {!showRec && lead.serviciosInteres.length > 0 && (
              <div className="dashboard-lead__services">
                {lead.serviciosInteres.map((s) => (
                  <span className="dashboard-lead__service-tag" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            )}
            {showRec && lead.recomendaciones && (
              <p className="dashboard-lead__rec">{lead.recomendaciones}</p>
            )}
          </div>
          <div className="dashboard-lead__meta">
            {lead.scoreLead > 0 && (
              <span
                className={`dashboard-score dashboard-score--${
                  lead.scoreLead >= 80
                    ? "high"
                    : lead.scoreLead >= 50
                      ? "mid"
                      : "low"
                }`}
              >
                {lead.scoreLead}
              </span>
            )}
            <span
              className={`dashboard-intention dashboard-intention--${lead.intention}`}
            >
              {lead.intention}
            </span>
          </div>
          {lead.telefono && (
            <a
              className="dashboard-lead__wa"
              href={waLink(lead.telefono)}
              rel="noopener noreferrer"
              target="_blank"
            >
              WhatsApp
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

function ClientDrawer({
  client,
  onClose,
}: {
  client: ClientRecord;
  onClose: () => void;
}) {
  const [sessions, setSessions] = useState<ClientSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    getClientSessions(client.id)
      .then((data) => setSessions(data.sessions))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, [client.id]);

  function toggleSession(id: number) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} aria-hidden="true" />
      <aside
        className="client-drawer"
        aria-label={`Detalle de ${client.nombre}`}
      >
        <div className="client-drawer__header">
          <div className="client-drawer__title">
            <div className="client-avatar">
              {client.nombre.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2>{client.nombre}</h2>
              {client.empresa && <p>{client.empresa}</p>}
            </div>
          </div>
          <button
            className="dashboard-icon-button"
            onClick={onClose}
            title="Cerrar"
            type="button"
          >
            <FiX aria-hidden="true" />
          </button>
        </div>

        <div className="client-drawer__info">
          {client.telefono && (
            <div className="client-info-item">
              <span>Teléfono</span>
              <strong>{client.telefono}</strong>
            </div>
          )}
          {client.cedula && (
            <div className="client-info-item">
              <span>Cédula</span>
              <strong>{client.cedula}</strong>
            </div>
          )}
          <div className="client-info-item">
            <span>Sesiones</span>
            <strong>{client.totalSessions}</strong>
          </div>
          <div className="client-info-item">
            <span>Intención</span>
            <span
              className={`dashboard-intention dashboard-intention--${client.intention}`}
            >
              {client.intention}
            </span>
          </div>
          {client.avgScore > 0 && (
            <div className="client-info-item">
              <span>Score promedio</span>
              <span
                className={`dashboard-score dashboard-score--${
                  client.avgScore >= 80
                    ? "high"
                    : client.avgScore >= 50
                      ? "mid"
                      : "low"
                }`}
              >
                {client.avgScore}
              </span>
            </div>
          )}
          {client.lastSessionAt && (
            <div className="client-info-item">
              <span>Última sesión</span>
              <strong>{formatDate(client.lastSessionAt)}</strong>
            </div>
          )}
        </div>

        <div className="client-drawer__sessions">
          <h3>Historial de llamadas</h3>
          {loading && (
            <p className="dashboard-empty">Cargando historial...</p>
          )}
          {!loading && sessions.length === 0 && (
            <p className="dashboard-empty">Sin sesiones registradas.</p>
          )}
          <div className="session-list">
            {sessions.map((session) => (
              <div className="session-card" key={session.id}>
                <button
                  className="session-card__header"
                  onClick={() => toggleSession(session.id)}
                  type="button"
                  aria-expanded={expandedId === session.id}
                >
                  <div className="session-card__meta">
                    <strong>{formatDate(session.startedAt)}</strong>
                    <span>{formatDuration(session.duracionSegundos)}</span>
                  </div>
                  <div className="session-card__badges">
                    {session.scoreLead > 0 && (
                      <span
                        className={`dashboard-score dashboard-score--${
                          session.scoreLead >= 80
                            ? "high"
                            : session.scoreLead >= 50
                              ? "mid"
                              : "low"
                        }`}
                      >
                        {session.scoreLead}
                      </span>
                    )}
                    <span
                      className={`dashboard-intention dashboard-intention--${session.intention}`}
                    >
                      {session.intention}
                    </span>
                    {expandedId === session.id ? (
                      <FiChevronUp
                        className="session-chevron"
                        aria-hidden="true"
                      />
                    ) : (
                      <FiChevronDown
                        className="session-chevron"
                        aria-hidden="true"
                      />
                    )}
                  </div>
                </button>

                {expandedId === session.id && (
                  <div className="session-card__detail">
                    {session.resumen && (
                      <div className="session-detail-block">
                        <label>Resumen de la conversación</label>
                        <p>{session.resumen}</p>
                      </div>
                    )}
                    {session.serviciosInteres.length > 0 && (
                      <div className="session-detail-block">
                        <label>Servicios de interés</label>
                        <div className="dashboard-lead__services">
                          {session.serviciosInteres.map((s) => (
                            <span
                              className="dashboard-lead__service-tag"
                              key={s}
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {session.recomendaciones && (
                      <div className="session-detail-block">
                        <label>Recomendaciones</label>
                        <p>{session.recomendaciones}</p>
                      </div>
                    )}
                    <button
                      className="session-pdf-btn"
                      onClick={() => generateSessionPDF(client, session)}
                      type="button"
                    >
                      <FiFileText aria-hidden="true" />
                      Descargar PDF de esta sesión
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}

function ClientsSection() {
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [drawerClient, setDrawerClient] = useState<ClientRecord | null>(null);

  useEffect(() => {
    getClients()
      .then((data) => setClients(data.clients))
      .catch(() => setClients([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return clients;
    const q = search.toLowerCase();
    return clients.filter(
      (c) =>
        c.nombre.toLowerCase().includes(q) ||
        c.empresa.toLowerCase().includes(q) ||
        c.telefono.includes(q),
    );
  }, [clients, search]);

  return (
    <section className="clients-section" aria-labelledby="clients-title">
      <div className="clients-header">
        <div>
          <h2 id="clients-title">Clientes</h2>
          <p>
            {loading
              ? "Cargando..."
              : `${clients.length} contactos registrados`}
          </p>
        </div>
        <div className="clients-search-wrap">
          <FiSearch className="clients-search-icon" aria-hidden="true" />
          <input
            className="clients-search"
            placeholder="Buscar cliente..."
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {loading && <p className="dashboard-empty">Cargando clientes...</p>}

      {!loading && filtered.length === 0 && (
        <p className="dashboard-empty">
          {search
            ? `Sin resultados para "${search}"`
            : "Sin clientes registrados."}
        </p>
      )}

      {!loading && filtered.length > 0 && (
        <div className="clients-grid">
          {filtered.map((client) => (
            <button
              className="client-card"
              key={client.id}
              onClick={() => setDrawerClient(client)}
              type="button"
            >
              <div className="client-card__avatar">
                {client.nombre.charAt(0).toUpperCase()}
              </div>
              <div className="client-card__body">
                <strong>{client.nombre}</strong>
                <span className="client-card__company">
                  {client.empresa || "Sin empresa"}
                </span>
                {client.telefono && (
                  <span className="client-card__phone">{client.telefono}</span>
                )}
              </div>
              <div className="client-card__footer">
                <span
                  className={`dashboard-intention dashboard-intention--${client.intention}`}
                >
                  {client.intention}
                </span>
                {client.avgScore > 0 && (
                  <span
                    className={`dashboard-score dashboard-score--${
                      client.avgScore >= 80
                        ? "high"
                        : client.avgScore >= 50
                          ? "mid"
                          : "low"
                    }`}
                  >
                    {client.avgScore}
                  </span>
                )}
                <small>
                  {client.totalSessions}{" "}
                  {client.totalSessions === 1 ? "sesión" : "sesiones"}
                </small>
              </div>
            </button>
          ))}
        </div>
      )}

      {drawerClient && (
        <ClientDrawer
          key={drawerClient.id}
          client={drawerClient}
          onClose={() => setDrawerClient(null)}
        />
      )}
    </section>
  );
}

export function DashboardSection() {
  const [activeSection, setActiveSection] = useState<NavSection>("resumen");
  const [state, setState] = useState<DashboardState>({
    status: "loading",
    data: null,
    error: null,
  });

  const loadDashboard = useCallback((signal?: AbortSignal) => {
    setState((current) => ({
      status: "loading",
      data: current.data,
      error: null,
    }));

    getDashboardSummary(signal)
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error: Error) => {
        if (signal?.aborted) return;
        setState((current) => ({
          status: "error",
          data: current.data,
          error: error.message,
        }));
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getDashboardSummary(controller.signal)
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error: Error) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", data: null, error: error.message });
      });
    return () => controller.abort();
  }, []);

  const summary = state.data ?? emptySummary;
  const maxVolume = useMemo(
    () => getMaxVolume(summary.volumeByHour),
    [summary.volumeByHour],
  );
  const isLoading = state.status === "loading";

  const navItems: { id: NavSection; label: string }[] = [
    { id: "resumen", label: "Resumen" },
    { id: "clientes", label: "Clientes" },
    { id: "leads", label: "Leads" },
  ];

  const sectionKicker: Record<NavSection, string> = {
    resumen: "Resumen ejecutivo",
    clientes: "Gestión de clientes",
    leads: "Leads y escalados",
  };

  return (
    <main className="dashboard-shell">
      <aside className="dashboard-sidebar" aria-label="Navegación dashboard">
        <a className="dashboard-sidebar__brand" href="/">
          GoToCloud
          <span>Contact Center IA</span>
        </a>
        <nav className="dashboard-sidebar__nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={activeSection === item.id ? "is-active" : ""}
              onClick={() => setActiveSection(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="dashboard-sidebar__status">
          <FiDatabase aria-hidden="true" />
          <span>Supabase</span>
          <strong>{state.status === "error" ? "Revisar" : "Conectado"}</strong>
        </div>
      </aside>

      <section className="dashboard-main" aria-labelledby="dashboard-title">
        <header className="dashboard-header">
          <div>
            <p className="dashboard-kicker">{sectionKicker[activeSection]}</p>
            <h1 id="dashboard-title">Contact Center IA</h1>
            <p className="dashboard-subtitle">
              Actualizado desde Supabase ·{" "}
              {formatGeneratedAt(summary.generatedAt)}
            </p>
          </div>
          <div className="dashboard-actions">
            {activeSection === "resumen" && (
              <>
                <div className="dashboard-range" aria-label="Rango de fechas">
                  <button className="is-active" type="button">
                    Día
                  </button>
                  <button type="button">Semana</button>
                  <button type="button">Mes</button>
                </div>
                <button
                  className="dashboard-icon-button"
                  disabled={isLoading}
                  onClick={() => loadDashboard()}
                  title="Actualizar"
                  type="button"
                >
                  <FiRefreshCw aria-hidden="true" />
                  <span className="visually-hidden">Actualizar</span>
                </button>
                <button
                  className="dashboard-icon-button dashboard-icon-button--primary"
                  onClick={() => downloadReport(summary)}
                  title="Exportar reporte"
                  type="button"
                >
                  <FiDownload aria-hidden="true" />
                  <span className="visually-hidden">Exportar reporte</span>
                </button>
              </>
            )}
          </div>
        </header>

        {state.status === "error" && (
          <div className="dashboard-alert" role="alert">
            <FiAlertCircle aria-hidden="true" />
            <span>{state.error}</span>
          </div>
        )}

        {activeSection === "resumen" && (
          <>
            <section
              className="dashboard-metrics"
              aria-label="Indicadores principales"
            >
              {summary.overview.map((metric) => (
                <article
                  className={`dashboard-metric ${isLoading ? "is-loading" : ""}`}
                  key={metric.id}
                >
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <div>
                    <small className={`trend trend--${metric.trend.direction}`}>
                      {metric.trend.value}
                    </small>
                    <small>{metric.detail}</small>
                  </div>
                </article>
              ))}
            </section>

            <section className="dashboard-grid">
              <article
                className="dashboard-panel dashboard-panel--wide"
                id="conversaciones"
              >
                <div className="dashboard-panel__header">
                  <div>
                    <h2>Volumen y sentimiento</h2>
                    <p>Conversaciones por hora · sentimiento registrado</p>
                  </div>
                  <div className="dashboard-legend">
                    <span>
                      <i className="legend-volume" />
                      Volumen
                    </span>
                    <span>
                      <i className="legend-positive" />
                      Sentimiento +
                    </span>
                    <span>
                      <i className="legend-negative" />
                      Sentimiento -
                    </span>
                  </div>
                </div>
                <div
                  className="dashboard-chart"
                  aria-label="Conversaciones por hora"
                >
                  {summary.volumeByHour.map((point) => {
                    const height = Math.max(
                      6,
                      Math.round(
                        (point.conversations / maxVolume) * 100,
                      ),
                    );
                    return (
                      <div className="dashboard-chart__bar" key={point.hour}>
                        <span
                          className="dashboard-chart__positive"
                          style={{
                            height: `${point.sentimentPositive * 6}px`,
                          }}
                        />
                        <span
                          className="dashboard-chart__negative"
                          style={{
                            height: `${point.sentimentNegative * 6}px`,
                          }}
                        />
                        <strong style={{ height: `${height}%` }} />
                        <small>{point.hour.slice(0, 2)}</small>
                      </div>
                    );
                  })}
                </div>
              </article>

              <article className="dashboard-panel">
                <div className="dashboard-panel__header">
                  <div>
                    <h2>Motivos de contacto</h2>
                    <p>Top 6 · datos del día</p>
                  </div>
                </div>
                <BreakdownList
                  emptyLabel="Sin motivos registrados para hoy."
                  items={summary.contactReasons}
                />
              </article>

              <article className="dashboard-panel" id="canales">
                <div className="dashboard-panel__header">
                  <div>
                    <h2>Mix por canal</h2>
                    <p>Voz · WhatsApp · Chat · SMS</p>
                  </div>
                </div>
                <BreakdownList
                  emptyLabel="Sin conversaciones por canal para hoy."
                  items={summary.channels}
                />
              </article>

              <article className="dashboard-panel dashboard-panel--full" id="agente">
                <div className="dashboard-panel__header">
                  <div>
                    <h2>Recomendaciones del agente IA</h2>
                    <p>Generadas con patrones actuales de Supabase</p>
                  </div>
                  <span className="dashboard-source">
                    {summary.source.sessions} sesiones ·{" "}
                    {summary.source.calls} llamadas ·{" "}
                    {summary.source.messages} mensajes
                  </span>
                </div>
                <ol className="dashboard-recommendations">
                  {summary.recommendations.map((rec, idx) => (
                    <li key={rec.id}>
                      <span>{idx + 1}</span>
                      <p>{rec.title}</p>
                      <strong data-impact={rec.impact}>
                        impacto {rec.impact}
                      </strong>
                    </li>
                  ))}
                </ol>
              </article>
            </section>
          </>
        )}

        {activeSection === "clientes" && <ClientsSection />}

        {activeSection === "leads" && (
          <section className="dashboard-grid">
            <article
              className="dashboard-panel dashboard-panel--full"
              id="leads"
            >
              <div className="dashboard-panel__header">
                <div>
                  <h2>Leads calientes</h2>
                  <p>Score ≥ 70 o intención caliente · seguimiento prioritario</p>
                </div>
                {summary.hotLeads.length > 0 && (

                  
                  <span className="dashboard-badge dashboard-badge--hot">
                    {summary.hotLeads.length}
                  </span>
                )}
              </div>
              <LeadList leads={summary.hotLeads} showRec={false} />
            </article>

            <article
              className="dashboard-panel dashboard-panel--full"
              id="escalado"
            >
              <div className="dashboard-panel__header">
                <div>
                  <h2>Candidatos a escalado humano</h2>
                  <p>El agente IA dejó recomendaciones de seguimiento</p>
                </div>
                {summary.escalationCandidates.length > 0 && (
                  <span className="dashboard-badge dashboard-badge--escalation">
                    {summary.escalationCandidates.length}
                  </span>
                )}
              </div>
              <LeadList leads={summary.escalationCandidates} showRec={true} />
            </article>
          </section>
        )}
      </section>
    </main>
  );
}
