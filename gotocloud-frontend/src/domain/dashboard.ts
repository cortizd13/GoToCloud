export type DashboardTrendDirection = "up" | "down" | "flat";

export type DashboardTrend = {
  value: string;
  direction: DashboardTrendDirection;
};

export type DashboardOverviewMetric = {
  id: string;
  label: string;
  value: string;
  detail: string;
  trend: DashboardTrend;
};

export type DashboardHourlyPoint = {
  hour: string;
  conversations: number;
  sentimentPositive: number;
  sentimentNegative: number;
};

export type DashboardBreakdownItem = {
  label: string;
  value: number;
  percentage: number;
};

export type DashboardRecommendation = {
  id: string;
  title: string;
  impact: "alto" | "medio" | "bajo";
};

export type DashboardSourceSummary = {
  sessions: number;
  calls: number;
  messages: number;
  events: number;
};

export type DashboardLead = {
  id: number;
  nombre: string;
  empresa: string;
  telefono: string;
  scoreLead: number;
  intention: "fria" | "calida" | "caliente";
  serviciosInteres: string[];
  recomendaciones: string;
  startedAt: string;
};

export type DashboardSummary = {
  generatedAt: string;
  range: "today";
  overview: DashboardOverviewMetric[];
  volumeByHour: DashboardHourlyPoint[];
  hotLeads: DashboardLead[];
  escalationCandidates: DashboardLead[];
  contactReasons: DashboardBreakdownItem[];
  channels: DashboardBreakdownItem[];
  recommendations: DashboardRecommendation[];
  source: DashboardSourceSummary;
};
