-- =============================================================
--  GoToCloud Voicebot — Schema de Base de Conocimientos
--  Proyecto Supabase: nzeruwamlpacikmqtcja
--  Ejecutar en: https://supabase.com/dashboard/project/nzeruwamlpacikmqtcja/sql/new
-- =============================================================

-- 1. Empresa (una fila, id=1)
CREATE TABLE IF NOT EXISTS public.empresa (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    presencia       TEXT,
    propuesta_valor         JSONB DEFAULT '[]'::jsonb,
    clientes_destacados     JSONB DEFAULT '[]'::jsonb,
    partners                JSONB DEFAULT '[]'::jsonb,
    reconocimientos         JSONB DEFAULT '[]'::jsonb,
    contacto                JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE public.empresa IS 'Información general de GoToCloud';
COMMENT ON COLUMN public.empresa.propuesta_valor IS 'Array de strings: propuesta de valor';
COMMENT ON COLUMN public.empresa.clientes_destacados IS 'Array de strings: nombres de clientes';
COMMENT ON COLUMN public.empresa.contacto IS 'Objeto: {whatsapp, web, linkedin}';

-- 2. Servicios (cloud_computing, seguridad, datos, etc.)
CREATE TABLE IF NOT EXISTS public.servicios (
    id              TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    categoria       TEXT,
    subcategoria    TEXT,
    beneficios      JSONB DEFAULT '[]'::jsonb,
    para_quien      JSONB DEFAULT '{}'::jsonb,
    pilares         JSONB DEFAULT '[]'::jsonb,
    metodologias    JSONB DEFAULT '[]'::jsonb,
    alcance         JSONB DEFAULT '[]'::jsonb,
    reportes        JSONB DEFAULT '[]'::jsonb,
    especializaciones JSONB DEFAULT '[]'::jsonb,
    partners        JSONB DEFAULT '[]'::jsonb
);

COMMENT ON TABLE public.servicios IS 'Servicios cloud de GoToCloud con metadata';

-- 3. Métricas (pares clave-valor)
CREATE TABLE IF NOT EXISTS public.metricas (
    clave   TEXT PRIMARY KEY,
    valor   TEXT NOT NULL
);

COMMENT ON TABLE public.metricas IS 'Cifras de impacto: empresas transformadas, servidores migrados, etc.';

-- 4. Productos SaaS (Kármán, OASIS AI, DataLoom)
CREATE TABLE IF NOT EXISTS public.productos_saas (
    id              TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    para_quien      TEXT,
    funcionalidades JSONB DEFAULT '[]'::jsonb,
    beneficios      JSONB DEFAULT '[]'::jsonb,
    seguridad       JSONB DEFAULT '[]'::jsonb
);

COMMENT ON TABLE public.productos_saas IS 'Productos SaaS propios de GoToCloud';

-- 5. Clientes (persistencia de sesión)
CREATE TABLE IF NOT EXISTS public.clientes (
    id          SERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL,
    cedula      TEXT NOT NULL UNIQUE,
    empresa     TEXT,
    telefono    TEXT,
    updated_at  TIMESTAMPTZ DEFAULT now(),
    created_at  TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.clientes IS 'Registro de llamadas / clientes contactados';

-- 6. Llamadas (metadata de cada llamada)
CREATE TABLE IF NOT EXISTS public.llamadas (
    id                  SERIAL PRIMARY KEY,
    cliente_id          INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    duracion_segundos   INTEGER,
    resumen             TEXT,
    intention           VARCHAR(10) CHECK (intention IN ('fria', 'calida', 'caliente')),
    score_lead          INTEGER CHECK (score_lead BETWEEN 0 AND 100),
    servicios_interes   TEXT[] DEFAULT '{}',
    recomendaciones     TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.llamadas IS 'Metadata de llamadas: resumen, intención, score, servicios de interés';

-- =============================================================
--  Multi-Channel AI Agent Platform — Phase 1: Database Foundation
--  New tables added alongside existing ones (no modifications to existing tables)
-- =============================================================

-- 1.1 PostgreSQL Enums (con guard IF NOT EXISTS vía DO block)
DO $$ BEGIN CREATE TYPE channel_type AS ENUM ('voice', 'whatsapp', 'telegram', 'webchat', 'sms'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE thread_status AS ENUM ('active', 'closed', 'archived'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE session_status AS ENUM ('active', 'completed', 'failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE message_sender AS ENUM ('user', 'agent', 'system'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE contact_role AS ENUM ('lead', 'client', 'employee', 'vendor', 'prospect'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 1.15 pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1.2 Companies (multi-tenant)
CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.3 Contacts (unified identity with emails TEXT[], phones TEXT[])
CREATE TABLE IF NOT EXISTS public.contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    emails TEXT[] DEFAULT '{}'::text[],
    phones TEXT[] DEFAULT '{}'::text[],
    metadata JSONB DEFAULT '{}'::jsonb,
    unified TSTZRANGE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.5 Contact-Companies (many-to-many with role enum)
CREATE TABLE IF NOT EXISTS public.contact_companies (
    contact_id UUID NOT NULL REFERENCES public.contacts(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    role contact_role DEFAULT 'client',
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (contact_id, company_id)
);

-- 1.4 Channel Identities (per-channel profiles)
CREATE TABLE IF NOT EXISTS public.channel_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES public.contacts(id) ON DELETE CASCADE,
    channel_type channel_type NOT NULL,
    external_id TEXT NOT NULL,
    profile_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(channel_type, external_id)
);

-- 1.6 Conversation Threads (global threads)
CREATE TABLE IF NOT EXISTS public.conversation_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES public.contacts(id) ON DELETE CASCADE,
    status thread_status DEFAULT 'active',
    topic TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.7 Conversation Sessions (per-channel sessions)
CREATE TABLE IF NOT EXISTS public.conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES public.conversation_threads(id) ON DELETE CASCADE,
    channel_type channel_type NOT NULL,
    channel_identity_id UUID REFERENCES public.channel_identities(id) ON DELETE SET NULL,
    status session_status DEFAULT 'active',
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.8 Messages (with metadata JSONB)
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.conversation_sessions(id) ON DELETE CASCADE,
    sender message_sender NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.9 Memory Summaries (persistent summaries)
CREATE TABLE IF NOT EXISTS public.memory_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES public.conversation_threads(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.10 Memory Embeddings (pgvector)
CREATE TABLE IF NOT EXISTS public.memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES public.conversation_threads(id) ON DELETE CASCADE,
    message_id UUID REFERENCES public.messages(id) ON DELETE CASCADE,
    content_chunk TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    model TEXT DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.11 Agents (agent registry)
CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    model TEXT NOT NULL,
    system_prompt TEXT,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.12 Agent Tools (tool registry per agent)
CREATE TABLE IF NOT EXISTS public.agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_schema JSONB DEFAULT '{}'::jsonb,
    handler_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.13 Analytics Events (audit/analytics)
CREATE TABLE IF NOT EXISTS public.analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES public.conversation_threads(id) ON DELETE SET NULL,
    session_id UUID REFERENCES public.conversation_sessions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.14 Indexes (BTREE + GIN for JSONB + vector index)
-- Todos con IF NOT EXISTS para ejecución idempotente

-- BTREE indexes on FK columns
CREATE INDEX IF NOT EXISTS idx_contact_companies_contact_id ON public.contact_companies(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_companies_company_id ON public.contact_companies(company_id);
CREATE INDEX IF NOT EXISTS idx_channel_identities_contact_id ON public.channel_identities(contact_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_company_id ON public.conversation_threads(company_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_contact_id ON public.conversation_threads(contact_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_status ON public.conversation_threads(status);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_thread_id ON public.conversation_sessions(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_channel_identity_id ON public.conversation_sessions(channel_identity_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status ON public.conversation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON public.messages(sender);
CREATE INDEX IF NOT EXISTS idx_memory_summaries_thread_id ON public.memory_summaries(thread_id);
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_thread_id ON public.memory_embeddings(thread_id);
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_message_id ON public.memory_embeddings(message_id);
CREATE INDEX IF NOT EXISTS idx_agents_company_id ON public.agents(company_id);
CREATE INDEX IF NOT EXISTS idx_agent_tools_agent_id ON public.agent_tools(agent_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_thread_id ON public.analytics_events(thread_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON public.analytics_events(session_id);

-- Composite indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_identities_channel_external ON public.channel_identities(channel_type, external_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_created ON public.messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type_created ON public.analytics_events(event_type, created_at DESC);

-- GIN indexes for arrays and JSONB
CREATE INDEX IF NOT EXISTS idx_contacts_emails_gin ON public.contacts USING GIN(emails);
CREATE INDEX IF NOT EXISTS idx_contacts_phones_gin ON public.contacts USING GIN(phones);
CREATE INDEX IF NOT EXISTS idx_contacts_metadata_gin ON public.contacts USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_channel_identities_profile_gin ON public.channel_identities USING GIN(profile_data);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_metadata_gin ON public.conversation_threads USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_messages_metadata_gin ON public.messages USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_agents_config_gin ON public.agents USING GIN(config);
CREATE INDEX IF NOT EXISTS idx_agent_tools_schema_gin ON public.agent_tools USING GIN(tool_schema);
CREATE INDEX IF NOT EXISTS idx_analytics_events_payload_gin ON public.analytics_events USING GIN(payload);

-- Vector index (IVFFlat placeholder)
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_vector_ivfflat ON public.memory_embeddings USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================
--  Permisos: habilitar acceso anónimo (lectura/escritura)
--  NOTA: Ajustar según necesidad de seguridad en producción
-- =============================================================
ALTER TABLE public.empresa         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.servicios       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metricas        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.productos_saas  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clientes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llamadas         ENABLE ROW LEVEL SECURITY;

-- Limpiar políticas existentes (para rerun seguro)
DROP POLICY IF EXISTS "anon_select_empresa"         ON public.empresa;
DROP POLICY IF EXISTS "anon_select_servicios"       ON public.servicios;
DROP POLICY IF EXISTS "anon_select_metricas"        ON public.metricas;
DROP POLICY IF EXISTS "anon_select_productos_saas"  ON public.productos_saas;
DROP POLICY IF EXISTS "anon_insert_clientes"        ON public.clientes;
DROP POLICY IF EXISTS "anon_select_clientes"        ON public.clientes;
DROP POLICY IF EXISTS "anon_insert_llamadas"        ON public.llamadas;
DROP POLICY IF EXISTS "anon_select_llamadas"        ON public.llamadas;
DROP POLICY IF EXISTS "anon_insert_empresa"         ON public.empresa;
DROP POLICY IF EXISTS "anon_upsert_empresa"         ON public.empresa;
DROP POLICY IF EXISTS "anon_insert_servicios"       ON public.servicios;
DROP POLICY IF EXISTS "anon_upsert_servicios"       ON public.servicios;
DROP POLICY IF EXISTS "anon_insert_metricas"        ON public.metricas;
DROP POLICY IF EXISTS "anon_upsert_metricas"        ON public.metricas;
DROP POLICY IF EXISTS "anon_insert_productos_saas"  ON public.productos_saas;
DROP POLICY IF EXISTS "anon_upsert_productos_saas"  ON public.productos_saas;

-- Permitir lectura anónima para todas las tablas
CREATE POLICY "anon_select_empresa"         ON public.empresa         FOR SELECT USING (true);
CREATE POLICY "anon_select_servicios"       ON public.servicios       FOR SELECT USING (true);
CREATE POLICY "anon_select_metricas"        ON public.metricas        FOR SELECT USING (true);
CREATE POLICY "anon_select_productos_saas"  ON public.productos_saas  FOR SELECT USING (true);

-- Permitir insert anónimo en clientes (registro de llamadas)
CREATE POLICY "anon_insert_clientes" ON public.clientes
    FOR INSERT WITH CHECK (true);

-- Permitir select anónimo en clientes (verificar si ya existe)
CREATE POLICY "anon_select_clientes" ON public.clientes
    FOR SELECT USING (true);

-- Políticas RLS para tabla llamadas
CREATE POLICY "anon_insert_llamadas" ON public.llamadas
    FOR INSERT WITH CHECK (true);

CREATE POLICY "anon_select_llamadas" ON public.llamadas
    FOR SELECT USING (true);

-- Permitir insert/upsert anónimo para seed de datos
CREATE POLICY "anon_insert_empresa" ON public.empresa
    FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_upsert_empresa" ON public.empresa
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "anon_insert_servicios" ON public.servicios
    FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_upsert_servicios" ON public.servicios
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "anon_insert_metricas" ON public.metricas
    FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_upsert_metricas" ON public.metricas
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "anon_insert_productos_saas" ON public.productos_saas
    FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_upsert_productos_saas" ON public.productos_saas
    FOR UPDATE USING (true) WITH CHECK (true);

-- RLS policies for new multi-channel tables (matching existing pattern)
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contact_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

-- anon policies for new tables (drop all before recreate)
DROP POLICY IF EXISTS "anon_select_companies" ON public.companies;
DROP POLICY IF EXISTS "anon_insert_companies" ON public.companies;
DROP POLICY IF EXISTS "anon_select_contacts" ON public.contacts;
DROP POLICY IF EXISTS "anon_insert_contacts" ON public.contacts;
DROP POLICY IF EXISTS "anon_select_contact_companies" ON public.contact_companies;
DROP POLICY IF EXISTS "anon_insert_contact_companies" ON public.contact_companies;
DROP POLICY IF EXISTS "anon_select_channel_identities" ON public.channel_identities;
DROP POLICY IF EXISTS "anon_insert_channel_identities" ON public.channel_identities;
DROP POLICY IF EXISTS "anon_select_conversation_threads" ON public.conversation_threads;
DROP POLICY IF EXISTS "anon_insert_conversation_threads" ON public.conversation_threads;
DROP POLICY IF EXISTS "anon_select_conversation_sessions" ON public.conversation_sessions;
DROP POLICY IF EXISTS "anon_insert_conversation_sessions" ON public.conversation_sessions;
DROP POLICY IF EXISTS "anon_select_messages" ON public.messages;
DROP POLICY IF EXISTS "anon_insert_messages" ON public.messages;
DROP POLICY IF EXISTS "anon_select_memory_summaries" ON public.memory_summaries;
DROP POLICY IF EXISTS "anon_insert_memory_summaries" ON public.memory_summaries;
DROP POLICY IF EXISTS "anon_select_memory_embeddings" ON public.memory_embeddings;
DROP POLICY IF EXISTS "anon_insert_memory_embeddings" ON public.memory_embeddings;
DROP POLICY IF EXISTS "anon_select_agents" ON public.agents;
DROP POLICY IF EXISTS "anon_insert_agents" ON public.agents;
DROP POLICY IF EXISTS "anon_select_agent_tools" ON public.agent_tools;
DROP POLICY IF EXISTS "anon_insert_agent_tools" ON public.agent_tools;
DROP POLICY IF EXISTS "anon_select_analytics_events" ON public.analytics_events;
DROP POLICY IF EXISTS "anon_insert_analytics_events" ON public.analytics_events;

CREATE POLICY "anon_select_companies" ON public.companies FOR SELECT USING (true);
CREATE POLICY "anon_insert_companies" ON public.companies FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_contacts" ON public.contacts FOR SELECT USING (true);
CREATE POLICY "anon_insert_contacts" ON public.contacts FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_contact_companies" ON public.contact_companies FOR SELECT USING (true);
CREATE POLICY "anon_insert_contact_companies" ON public.contact_companies FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_channel_identities" ON public.channel_identities FOR SELECT USING (true);
CREATE POLICY "anon_insert_channel_identities" ON public.channel_identities FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_conversation_threads" ON public.conversation_threads FOR SELECT USING (true);
CREATE POLICY "anon_insert_conversation_threads" ON public.conversation_threads FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_conversation_sessions" ON public.conversation_sessions FOR SELECT USING (true);
CREATE POLICY "anon_insert_conversation_sessions" ON public.conversation_sessions FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_messages" ON public.messages FOR SELECT USING (true);
CREATE POLICY "anon_insert_messages" ON public.messages FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_memory_summaries" ON public.memory_summaries FOR SELECT USING (true);
CREATE POLICY "anon_insert_memory_summaries" ON public.memory_summaries FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_memory_embeddings" ON public.memory_embeddings FOR SELECT USING (true);
CREATE POLICY "anon_insert_memory_embeddings" ON public.memory_embeddings FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_agents" ON public.agents FOR SELECT USING (true);
CREATE POLICY "anon_insert_agents" ON public.agents FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_agent_tools" ON public.agent_tools FOR SELECT USING (true);
CREATE POLICY "anon_insert_agent_tools" ON public.agent_tools FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_select_analytics_events" ON public.analytics_events FOR SELECT USING (true);
CREATE POLICY "anon_insert_analytics_events" ON public.analytics_events FOR INSERT WITH CHECK (true);

-- =============================================================
--  Seed data (INSERT con ON CONFLICT para ser idempotente)
--  Corre con permisos de owner (SQL Editor), no depende del anon key
-- =============================================================

-- 1. Empresa
INSERT INTO public.empresa (id, nombre, descripcion, presencia, propuesta_valor, clientes_destacados, partners, reconocimientos, contacto)
VALUES (
    1,
    'GoToCloud',
    'GoToCloud es una empresa colombiana especializada en transformación digital mediante soluciones en la nube con foco en Microsoft Azure. Ayuda a empresas a migrar, modernizar y optimizar su operación tecnológica con seguridad e IA.',
    'Opera en toda Latinoamérica: Colombia, Estados Unidos, México, Ecuador, Perú y Argentina. En Colombia cubre Costa Colombiana, Antioquia, Santander, Bogotá D.C., Eje Cafetero y Sur del país.',
    '["Inteligente: optimización de procesos con IA","Ágil: despliegue rápido con infraestructura orientada al negocio","Proactivo: modernización de sistemas legados antes de que fallen","Seguro: operaciones técnicas gestionadas por expertos con protección de datos"]'::jsonb,
    '["Semana","Ecopetrol","Colchones El Dorado","DIAN"]'::jsonb,
    '["Microsoft","Databricks","VMware","Veeam","Acronis","Fortinet"]'::jsonb,
    '["Partner del año – Migración a Cloud (CloudVerse)","Premio a la Excelencia en Migración hacia Azure 2023 – TD Synnex","Microsoft Partner of the Year Awards 2023, 2024 y finalista 2025"]'::jsonb,
    '{"whatsapp":"+57 317 427 0148","web":"https://www.gotocloud.ai","linkedin":"https://www.linkedin.com/company/gotocloudsas"}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- 2. Servicios
INSERT INTO public.servicios (id, nombre, descripcion, beneficios, para_quien) VALUES
(
    'cloud_computing',
    'Servicios en la Nube',
    'Migración y gestión de infraestructura en Microsoft Azure. Arquitecturas híbridas, multicloud y listas para IA.',
    '["Migración guiada a Azure con respaldo experto","FinOps: visibilidad y control total del gasto en tiempo real","Gobierno y seguridad integrados desde el primer despliegue","Arquitecturas escalables: híbridas, multicloud o nativas en Azure","Alta disponibilidad y recuperación ante fallos","Automatización cloud-native para reducir errores operativos","Hasta 40% de ahorro en costos operativos"]'::jsonb,
    '{"pymes":["Migración rápida y sin fricciones","Escalabilidad sin perder control","Ahorro de costos con FinOps","Infraestructura lista para IA"],"corporativos":["Gobernanza y seguridad avanzada","Arquitecturas resilientes y multi-región","Integración con sistemas heredados","Múltiples zonas geográficas"]}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.servicios (id, nombre, descripcion, pilares, metodologias, alcance, reportes, beneficios) VALUES
(
    'servicios_administrados',
    'Servicios Administrados de TI',
    'Gestión 24/7 de infraestructura cloud con soporte proactivo, monitoreo continuo y mejores prácticas en Azure. El equipo cliente se enfoca en el negocio mientras GoToCloud opera la tecnología.',
    '["Estabilidad","Optimización","Seguridad"]'::jsonb,
    '["ITIL","Scrum","Well-Architected Framework (WAF)","Cloud Adoption Framework (CAF)","FinOps"]'::jsonb,
    '["Resolución de incidentes y gestión de problemas","Configuración de infraestructura y automatización","Estrategias de backup y recuperación ante desastres","Evaluación de postura de seguridad de red","Análisis de optimización de costos","Mantenimiento y actualizaciones de sistemas"]'::jsonb,
    '["12 informes mensuales de validación operacional con KPI/SLA","4 informes trimestrales de arquitectura e innovación","Seguimiento de incidentes y recomendaciones correctivas"]'::jsonb,
    '["Monitoreo 24/7 de toda la infraestructura","Procesos proactivos que previenen caídas antes de que ocurran","Liberación del equipo interno para actividades estratégicas","Cumplimiento de los más altos estándares de seguridad"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.servicios (id, nombre, descripcion, especializaciones) VALUES
(
    'modernizacion_apps',
    'Modernización de Aplicaciones',
    'Transformación de entornos legados en soluciones modernas, integradas y preparadas para innovar en Microsoft Azure con IA.',
    '["Migración de aplicaciones empresariales a Microsoft Azure","Desarrollo y modernización de apps con IA en Azure","Migración de infraestructura y bases de datos","Azure VMware Solution (mover VMs VMware directamente a Azure)","Infraestructura de escritorios virtuales (VDI)"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.servicios (id, nombre, descripcion, especializaciones, partners) VALUES
(
    'seguridad',
    'Seguridad en la Nube',
    'Protección de datos, identidades y cargas de trabajo en la nube con los más altos estándares de seguridad y cumplimiento normativo.',
    '["Protección contra amenazas en Microsoft (especialización avanzada)","Gestión bajo estándares de seguridad internacionales","Cumplimiento normativo desde el primer despliegue"]'::jsonb,
    '["Fortinet","Acronis","Microsoft Defender","Azure Sentinel"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.servicios (id, nombre, descripcion, especializaciones, partners) VALUES
(
    'datos',
    'Servicios de Datos',
    'Orquestación y gestión de datos para decisiones más inteligentes, seguras y escalables. Analítica avanzada e IA/ML en Microsoft Azure.',
    '["Analítica avanzada con Power BI y Azure","IA y aprendizaje automático en Microsoft Azure (especialización avanzada)","Gestión de más de 1 PB de datos para decisiones estratégicas"]'::jsonb,
    '["Databricks","Microsoft Azure"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.servicios (id, nombre, descripcion) VALUES
(
    'soluciones_saas',
    'Soluciones SaaS',
    'Productos de software propios de GoToCloud para necesidades empresariales específicas.'
)
ON CONFLICT (id) DO NOTHING;

-- 3. Productos SaaS
INSERT INTO public.productos_saas (id, nombre, descripcion, para_quien, funcionalidades, beneficios) VALUES
(
    'karman',
    'Kármán Reporting Hub',
    'Portal web para gestionar y visualizar dashboards de Power BI de forma organizada, con control de acceso por usuario y departamento.',
    'Organizaciones que usan Power BI y necesitan distribuir reportes a múltiples usuarios sin que todos tengan licencia Pro individual.',
    '["Presentación organizada de tableros Power BI","Control granular de acceso por usuario y rol","Integración con Azure Active Directory","Interfaz web intuitiva, sin conocimientos técnicos avanzados"]'::jsonb,
    '["Ahorro significativo en licencias Power BI Pro","Democratización de datos: más usuarios acceden a la misma información","Cada área ve solo los reportes relevantes para su función","Integración fluida con infraestructura Azure existente"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.productos_saas (id, nombre, descripcion, para_quien, funcionalidades, beneficios, seguridad) VALUES
(
    'oasis',
    'OASIS AI',
    'Plataforma SaaS sobre Microsoft Azure que automatiza procesos con IA, extrae información de documentos no estructurados (facturas, contratos, correos, imágenes) y genera insights para la toma de decisiones.',
    'Empresas del sector financiero, retail, legal, y cualquier organización que gestione grandes volúmenes de documentos o datos no estructurados.',
    '["Extracción automática de datos de documentos (facturas, contratos, reportes)","Análisis de datos no estructurados con Azure Cognitive Search y Azure OpenAI","Generación de resúmenes automáticos e identificación de tendencias","Interfaz web Django intuitiva, sin conocimientos técnicos"]'::jsonb,
    '["40% de reducción en tiempo de gestión documental","25-30% de disminución en costos operativos","Eliminación de entrada manual de datos y esfuerzos duplicados","Mejor ROI con decisiones basadas en datos reales","Escalable: crece con la empresa sin fricción"]'::jsonb,
    '["Autenticación multifactor (MFA)","Cifrado AES-256","Monitoreo con Azure Sentinel","Cumplimiento GDPR, CCPA y SOC 2"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.productos_saas (id, nombre, descripcion, para_quien, beneficios) VALUES
(
    'dataloom',
    'DataLoom',
    'Herramienta para orquestar datos empresariales de múltiples fuentes, permitiendo decisiones más inteligentes, seguras y escalables.',
    'Empresas que necesitan centralizar datos de múltiples fuentes para tomar decisiones estratégicas.',
    '["Centralización de datos de múltiples fuentes","Decisiones estratégicas basadas en información consolidada","Escalabilidad con el crecimiento del negocio"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- 4. Métricas
INSERT INTO public.metricas (clave, valor) VALUES
    ('empresas_transformadas', 'Más de 100 empresas transformadas con soluciones en la nube y datos'),
    ('servidores_migrados', 'Más de 500 servidores migrados a Azure con 0 horas de downtime'),
    ('satisfaccion_cliente', '95% de satisfacción del cliente en cada proyecto'),
    ('ahorro_costos_cloud', 'Hasta 40% de ahorro en costos operativos con FinOps'),
    ('ahorro_oasis', '25-30% de reducción en costos operativos con OASIS AI'),
    ('reduccion_tiempo_oasis', '40% de reducción en tiempo de gestión documental con OASIS AI'),
    ('datos_gestionados', 'Más de 1 PB de datos gestionados para decisiones estratégicas'),
    ('cargas_modernizadas', 'Más de 200 cargas de trabajo modernizadas a IaaS y PaaS en Azure')
ON CONFLICT (clave) DO NOTHING;

-- =============================================================
--  Verificación
-- =============================================================
SELECT 'empresa' AS tabla, COUNT(*) AS filas FROM public.empresa
UNION ALL
SELECT 'servicios', COUNT(*) FROM public.servicios
UNION ALL
SELECT 'metricas', COUNT(*) FROM public.metricas
UNION ALL
SELECT 'productos_saas', COUNT(*) FROM public.productos_saas
UNION ALL
SELECT 'clientes', COUNT(*) FROM public.clientes
UNION ALL
SELECT 'companies', COUNT(*) FROM public.companies
UNION ALL
SELECT 'contacts', COUNT(*) FROM public.contacts
UNION ALL
SELECT 'contact_companies', COUNT(*) FROM public.contact_companies
UNION ALL
SELECT 'channel_identities', COUNT(*) FROM public.channel_identities
UNION ALL
SELECT 'conversation_threads', COUNT(*) FROM public.conversation_threads
UNION ALL
SELECT 'conversation_sessions', COUNT(*) FROM public.conversation_sessions
UNION ALL
SELECT 'messages', COUNT(*) FROM public.messages
UNION ALL
SELECT 'memory_summaries', COUNT(*) FROM public.memory_summaries
UNION ALL
SELECT 'memory_embeddings', COUNT(*) FROM public.memory_embeddings
UNION ALL
SELECT 'agents', COUNT(*) FROM public.agents
UNION ALL
SELECT 'agent_tools', COUNT(*) FROM public.agent_tools
UNION ALL
SELECT 'analytics_events', COUNT(*) FROM public.analytics_events
ORDER BY tabla;
