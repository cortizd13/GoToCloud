# =============================================================
#  GOTOCLOUD VOICEBOT TOOL — Compatible con Gemini Live
#  Agente: Camila | Empresa: GoToCloud
# =============================================================

from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import compatibility: funciona con sys.path (voice_to_voice.py) y package-relative (main.py)
try:
    from backend.supabase_client import supabase, is_connected
except ImportError:
    # Fallback: agregar backend al path si no está
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    try:
        from supabase_client import supabase, is_connected
    except ImportError:
        supabase = None
        is_connected = lambda: False

# ─────────────────────────────────────────────
# BASE DE CONOCIMIENTO
# ─────────────────────────────────────────────
GOTOCLOUD_KB: dict[str, Any] = {
    "empresa": {
        "nombre": "GoToCloud",
        "descripcion": (
            "GoToCloud es una empresa colombiana especializada en transformación digital "
            "mediante soluciones en la nube con foco en Microsoft Azure. Ayuda a empresas "
            "a migrar, modernizar y optimizar su operación tecnológica con seguridad e IA."
        ),
        "presencia": (
            "Opera en toda Latinoamérica: Colombia, Estados Unidos, México, Ecuador, Perú "
            "y Argentina. En Colombia cubre Costa Colombiana, Antioquia, Santander, "
            "Bogotá D.C., Eje Cafetero y Sur del país."
        ),
        "propuesta_valor": [
            "Inteligente: optimización de procesos con IA",
            "Ágil: despliegue rápido con infraestructura orientada al negocio",
            "Proactivo: modernización de sistemas legados antes de que fallen",
            "Seguro: operaciones técnicas gestionadas por expertos con protección de datos",
        ],
        "clientes_destacados": ["Semana", "Ecopetrol", "Colchones El Dorado", "DIAN"],
        "partners": ["Microsoft", "Databricks", "VMware", "Veeam", "Acronis", "Fortinet"],
        "reconocimientos": [
            "Partner del año – Migración a Cloud (CloudVerse)",
            "Premio a la Excelencia en Migración hacia Azure 2023 – TD Synnex",
            "Microsoft Partner of the Year Awards 2023, 2024 y finalista 2025",
        ],
        "contacto": {
            "whatsapp": "+57 317 427 0148",
            "web": "https://www.gotocloud.ai",
            "linkedin": "https://www.linkedin.com/company/gotocloudsas",
        },
    },

    "servicios": {
        "cloud_computing": {
            "nombre": "Servicios en la Nube",
            "descripcion": (
                "Migración y gestión de infraestructura en Microsoft Azure. Arquitecturas "
                "híbridas, multicloud y listas para IA."
            ),
            "beneficios": [
                "Migración guiada a Azure con respaldo experto",
                "FinOps: visibilidad y control total del gasto en tiempo real",
                "Gobierno y seguridad integrados desde el primer despliegue",
                "Arquitecturas escalables: híbridas, multicloud o nativas en Azure",
                "Alta disponibilidad y recuperación ante fallos",
                "Automatización cloud-native para reducir errores operativos",
                "Hasta 40% de ahorro en costos operativos",
            ],
            "para_quien": {
                "pymes": [
                    "Migración rápida y sin fricciones",
                    "Escalabilidad sin perder control",
                    "Ahorro de costos con FinOps",
                    "Infraestructura lista para IA",
                ],
                "corporativos": [
                    "Gobernanza y seguridad avanzada",
                    "Arquitecturas resilientes y multi-región",
                    "Integración con sistemas heredados",
                    "Múltiples zonas geográficas",
                ],
            },
        },

        "servicios_administrados": {
            "nombre": "Servicios Administrados de TI",
            "descripcion": (
                "Gestión 24/7 de infraestructura cloud con soporte proactivo, monitoreo "
                "continuo y mejores prácticas en Azure. El equipo cliente se enfoca en el "
                "negocio mientras GoToCloud opera la tecnología."
            ),
            "pilares": ["Estabilidad", "Optimización", "Seguridad"],
            "metodologias": ["ITIL", "Scrum", "Well-Architected Framework (WAF)", "Cloud Adoption Framework (CAF)", "FinOps"],
            "alcance": [
                "Resolución de incidentes y gestión de problemas",
                "Configuración de infraestructura y automatización",
                "Estrategias de backup y recuperación ante desastres",
                "Evaluación de postura de seguridad de red",
                "Análisis de optimización de costos",
                "Mantenimiento y actualizaciones de sistemas",
            ],
            "reportes": [
                "12 informes mensuales de validación operacional con KPI/SLA",
                "4 informes trimestrales de arquitectura e innovación",
                "Seguimiento de incidentes y recomendaciones correctivas",
            ],
            "beneficios": [
                "Monitoreo 24/7 de toda la infraestructura",
                "Procesos proactivos que previenen caídas antes de que ocurran",
                "Liberación del equipo interno para actividades estratégicas",
                "Cumplimiento de los más altos estándares de seguridad",
            ],
        },

        "modernizacion_apps": {
            "nombre": "Modernización de Aplicaciones",
            "descripcion": (
                "Transformación de entornos legados en soluciones modernas, integradas "
                "y preparadas para innovar en Microsoft Azure con IA."
            ),
            "especializaciones": [
                "Migración de aplicaciones empresariales a Microsoft Azure",
                "Desarrollo y modernización de apps con IA en Azure",
                "Migración de infraestructura y bases de datos",
                "Azure VMware Solution (mover VMs VMware directamente a Azure)",
                "Infraestructura de escritorios virtuales (VDI)",
            ],
        },

        "seguridad": {
            "nombre": "Seguridad en la Nube",
            "descripcion": (
                "Protección de datos, identidades y cargas de trabajo en la nube con "
                "los más altos estándares de seguridad y cumplimiento normativo."
            ),
            "especializaciones": [
                "Protección contra amenazas en Microsoft (especialización avanzada)",
                "Gestión bajo estándares de seguridad internacionales",
                "Cumplimiento normativo desde el primer despliegue",
            ],
            "partners": ["Fortinet", "Acronis", "Microsoft Defender", "Azure Sentinel"],
        },

        "datos": {
            "nombre": "Servicios de Datos",
            "descripcion": (
                "Orquestación y gestión de datos para decisiones más inteligentes, "
                "seguras y escalables. Analítica avanzada e IA/ML en Microsoft Azure."
            ),
            "especializaciones": [
                "Analítica avanzada con Power BI y Azure",
                "IA y aprendizaje automático en Microsoft Azure (especialización avanzada)",
                "Gestión de más de 1 PB de datos para decisiones estratégicas",
            ],
            "partners": ["Databricks", "Microsoft Azure"],
        },

        "soluciones_saas": {
            "nombre": "Soluciones SaaS",
            "descripcion": "Productos de software propios de GoToCloud para necesidades empresariales específicas.",
            "productos": {
                "karman": {
                    "nombre": "Kármán Reporting Hub",
                    "descripcion": (
                        "Portal web para gestionar y visualizar dashboards de Power BI de "
                        "forma organizada, con control de acceso por usuario y departamento."
                    ),
                    "para_quien": (
                        "Organizaciones que usan Power BI y necesitan distribuir reportes "
                        "a múltiples usuarios sin que todos tengan licencia Pro individual."
                    ),
                    "funcionalidades": [
                        "Presentación organizada de tableros Power BI",
                        "Control granular de acceso por usuario y rol",
                        "Integración con Azure Active Directory",
                        "Interfaz web intuitiva, sin conocimientos técnicos avanzados",
                    ],
                    "beneficios": [
                        "Ahorro significativo en licencias Power BI Pro",
                        "Democratización de datos: más usuarios acceden a la misma información",
                        "Cada área ve solo los reportes relevantes para su función",
                        "Integración fluida con infraestructura Azure existente",
                    ],
                },
                "oasis": {
                    "nombre": "OASIS AI",
                    "descripcion": (
                        "Plataforma SaaS avanzada que automatiza procesos con IA, extrae información "
                        "de documentos no estructurados (facturas, contratos, correos, imágenes) "
                        "y genera insights para la toma de decisiones, utilizando tecnologías "
                        "de Microsoft Azure, Azure OpenAI y Azure Cognitive Services."
                    ),
                    "para_quien": (
                        "Empresas del sector financiero, retail, legal, y cualquier organización "
                        "que gestione grandes volúmenes de documentos o datos no estructurados."
                    ),
                    "funcionalidades": [
                        "Automatización de procesos: extracción de información de documentos (facturas, contratos, reportes)",
                        "Análisis avanzado de datos no estructurados con Azure Cognitive Search y Azure OpenAI",
                        "Generación de insights: resúmenes automáticos, identificación de tendencias y recomendaciones",
                        "Interfaz web intuitiva desarrollada con Django",
                    ],
                    "beneficios": [
                        "Mejora en la productividad: 40% de reducción en tiempo de gestión documental",
                        "Optimización de recursos: 25-30% de disminución en costos operativos",
                        "Eliminación de entrada manual de datos y esfuerzos duplicados",
                        "Mejor ROI con decisiones basadas en datos reales",
                        "Escalable: crece con la empresa sin fricción",
                    ],
                    "seguridad": [
                        "Autenticación multifactor (MFA) con Azure Active Directory B2C",
                        "Cifrado AES-256 en tránsito y en reposo",
                        "Monitoreo continuo con Azure Sentinel",
                        "Cumplimiento GDPR, CCPA y SOC 2",
                    ],
                },
                "dataloom": {
                    "nombre": "DataLoom",
                    "descripcion": (
                        "Solución SaaS potente para gestionar, buscar y acceder de manera eficiente "
                        "a archivos almacenados en la nube, utilizando tecnologías de Azure para "
                        "escalabilidad, seguridad y accesibilidad."
                    ),
                    "beneficios": [
                        "Gestión, búsqueda y acceso eficiente a archivos en la nube",
                        "Indexación de metadatos para búsqueda avanzada (nombre, extensión, tipo, fecha)",
                        "Integración con Azure Storage y Azure Active Directory B2C",
                        "Implementación rápida (menos de 6 horas) y personalizable",
                        "Disponibilidad del 99.95% respaldada por Azure",
                    ],
                },
            },
        },
    },

    "metricas": {
        "empresas_transformadas": "Más de 100 empresas transformadas con soluciones en la nube y datos",
        "servidores_migrados": "Más de 500 servidores migrados a Azure con 0 horas de downtime",
        "satisfaccion_cliente": "95% de satisfacción del cliente en cada proyecto",
        "ahorro_costos_cloud": "Hasta 40% de ahorro en costos operativos con FinOps",
        "ahorro_oasis": "25-30% de reducción en costos operativos con OASIS AI",
        "reduccion_tiempo_oasis": "40% de reducción en tiempo de gestión documental con OASIS AI",
        "datos_gestionados": "Más de 1 PB de datos gestionados para decisiones estratégicas",
        "cargas_modernizadas": "Más de 200 cargas de trabajo modernizadas a IaaS y PaaS en Azure",
    },
}


# ─────────────────────────────────────────────
# TOOLS PARA GEMINI LIVE
# ─────────────────────────────────────────────
GOTOCLOUD_TOOLS: list[dict[str, Any]] = [
    {
        "name": "registrar_datos_cliente",
        "description": (
            "Registra los datos del cliente al inicio de la llamada: nombre completo, cédula, "
            "empresa donde trabaja y teléfono de contacto. "
            "SIEMPRE llama esta tool al comienzo de la conversación, antes de responder "
            "cualquier otra pregunta. Recoge todos los campos antes de llamarla.\n\n"
            "COMPORTAMIENTO: La cédula es única. Si el cliente YA EXISTE (llamada recurrente), "
            "la tool actualiza sus datos y retorna ya_registrado=true con el ID existente. "
            "Si es NUEVO, lo crea y retorna ya_registrado=false. "
            "En ambos casos retorna el cliente_id para usar en otras tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nombre": {
                    "type": "string",
                    "description": "Nombre completo del cliente.",
                },
                "cedula": {
                    "type": "string",
                    "description": "Número de cédula o documento de identidad del cliente.",
                },
                "empresa": {
                    "type": "string",
                    "description": "Nombre de la empresa u organización donde trabaja el cliente.",
                },
                "telefono": {
                    "type": "string",
                    "description": "Número de teléfono o celular de contacto del cliente.",
                },
            },
            "required": ["nombre", "cedula"],
        },
    },
    {
        "name": "obtener_informacion_empresa",
        "description": (
            "Retorna información general sobre GoToCloud: qué es, dónde opera, su propuesta "
            "de valor, clientes destacados, partners y reconocimientos. Úsala cuando pregunten "
            "quién es GoToCloud, dónde están o qué premios tienen."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "obtener_servicios",
        "description": (
            "Retorna información detallada de los servicios de GoToCloud. Úsala cuando "
            "pregunten qué servicios ofrecen, qué hacen en la nube, cómo pueden ayudar, "
            "o por un servicio específico."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "servicio": {
                    "type": "string",
                    "description": "Servicio específico a consultar, o 'todos' para ver todos.",
                    "enum": [
                        "cloud_computing",
                        "modernizacion_apps",
                        "seguridad",
                        "servicios_administrados",
                        "datos",
                        "soluciones_saas",
                        "todos",
                    ],
                }
            },
            "required": [],
        },
    },
    {
        "name": "obtener_producto_saas",
        "description": (
            "Retorna información detallada de los productos SaaS propios de GoToCloud: "
            "Kármán Reporting Hub (portal de Power BI), OASIS AI (automatización con IA) "
            "y DataLoom (orquestación de datos). Úsala cuando pregunten por productos de "
            "software, soluciones propias o mencionen alguno de esos nombres."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "producto": {
                    "type": "string",
                    "description": "Producto a consultar.",
                    "enum": ["karman", "oasis", "dataloom", "todos"],
                }
            },
            "required": [],
        },
    },
    {
        "name": "obtener_metricas",
        "description": (
            "Retorna números concretos de impacto de GoToCloud: empresas atendidas, "
            "servidores migrados, ahorros, satisfacción del cliente. Úsala cuando pidan "
            "cifras, resultados o quieran saber cuánto pueden ahorrar."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "obtener_contacto",
        "description": (
            "Retorna los datos de contacto de GoToCloud. Úsala cuando el cliente quiera "
            "hablar con un asesor, pedir una cotización o que lo llamen."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "obtener_beneficios_para_cliente",
        "description": (
            "Recomienda servicios de GoToCloud según el tipo de empresa y la necesidad "
            "detectada. Úsala cuando el cliente cuento su situación o problema y necesites "
            "recomendar la solución más adecuada."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tipo_empresa": {
                    "type": "string",
                    "enum": ["pyme", "corporativo", "gobierno", "cualquiera"],
                },
                "necesidad": {
                    "type": "string",
                    "description": "Área de necesidad: 'reducir costos', 'seguridad', 'migración', 'datos', 'IA', 'documentos', etc.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "registrar_resumen_llamada",
        "description": (
            "Guarda el resumen y metadata al final de la llamada. LLAMA CUANDO LA LLAMADA ESTÉ POR TERMINAR. "
            "Incluye toda la información obtenida durante la conversación."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resumen": {
                    "type": "string",
                    "description": "Resumen breve de la conversación, qué preguntó, qué le interessó.",
                },
                "intention": {
                    "type": "string",
                    "enum": ["fria", "calida", "caliente"],
                    "description": "'fria': solo consultas generales, 'calida': interés real pero sin urgencia, 'caliente': necesidad inmediata o presupuesto disponible",
                },
                "score_lead": {
                    "type": "integer",
                    "description": "Probabilidad de cierre 0-100. 0-30 baja, 31-60 media, 61-100 alta.",
                },
                "servicios_interes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs de servicios que le interesaron al cliente (cloud_computing, seguridad, etc.)",
                },
                "recomendaciones": {
                    "type": "string",
                    "description": "Recomendaciones para el vendedor que hará seguimiento",
                },
            },
            "required": ["resumen", "intention", "score_lead"],
        },
    },
]


# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────

# Almacén temporal de datos del cliente (el compañero conectará la BD)
_cliente_actual: dict[str, str] = {}


def _fallback(que: str) -> dict:
    """Fallback genérico para errores de base de datos."""
    return {"error": f"Base de datos no disponible. Intenta más tarde."}


def ejecutar_tool(nombre: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}

    if nombre == "registrar_datos_cliente":
        nombre_cliente = args.get("nombre", "").strip()
        cedula = args.get("cedula", "").strip()
        empresa_cliente = args.get("empresa", "").strip()
        telefono_cliente = args.get("telefono", "").strip()
        _cliente_actual["nombre"] = nombre_cliente
        _cliente_actual["cedula"] = cedula
        _cliente_actual["empresa"] = empresa_cliente
        _cliente_actual["telefono"] = telefono_cliente
        # Guardar timestamp de inicio de llamada
        _cliente_actual["started_at"] = datetime.now(timezone.utc).isoformat()

        cliente_id = None
        ya_registrado = False
        if supabase is not None:
            try:
                # 1. Buscar por cédula (es UNIQUE)
                existente = supabase.table("clientes") \
                    .select("id") \
                    .eq("cedula", cedula) \
                    .execute()
                if existente.data and len(existente.data) > 0:
                    # Ya existe → UPDATE
                    cliente_id = existente.data[0]["id"]
                    update_row = {}
                    if nombre_cliente:
                        update_row["nombre"] = nombre_cliente
                    if empresa_cliente:
                        update_row["empresa"] = empresa_cliente
                    if telefono_cliente:
                        update_row["telefono"] = telefono_cliente
                    update_row["updated_at"] = datetime.now(timezone.utc).isoformat()
                    supabase.table("clientes") \
                        .update(update_row) \
                        .eq("id", cliente_id) \
                        .execute()
                    ya_registrado = True
                    _cliente_actual["cliente_id"] = cliente_id
                    print(f"[Supabase] Cliente ACTUALIZADO: id={cliente_id}, cedula={cedula}")
                else:
                    # No existe → INSERT
                    row = {"nombre": nombre_cliente, "cedula": cedula}
                    if empresa_cliente:
                        row["empresa"] = empresa_cliente
                    if telefono_cliente:
                        row["telefono"] = telefono_cliente
                    resultado = supabase.table("clientes").insert(row).execute()
                    if resultado.data and len(resultado.data) > 0:
                        cliente_id = resultado.data[0]["id"]
                        _cliente_actual["cliente_id"] = cliente_id
                        print(f"[Supabase] Cliente NUEVO: id={cliente_id}, cedula={cedula}")
                    else:
                        print(f"[Supabase] Cliente insertado sin ID")
            except Exception as ex:
                print(f"[Supabase] Error al registrar cliente: {ex}")
        else:
            print(f"[BD] Cliente registrado (sin Supabase): nombre={nombre_cliente!r}, cedula={cedula!r}")

        response = {
            "registrado": True,
            "ya_registrado": ya_registrado,
            "nombre": nombre_cliente,
            "cedula": cedula,
            "empresa": empresa_cliente,
            "telefono": telefono_cliente,
        }
        if ya_registrado:
            response["mensaje"] = (
                f"Cliente ya registrado. Datos actualizados para {nombre_cliente}."
            )
        else:
            response["mensaje"] = (
                f"Datos registrados correctamente para {nombre_cliente}."
            )
        if cliente_id is not None:
            response["cliente_id"] = cliente_id
        return response

    elif nombre == "obtener_informacion_empresa":
        e = GOTOCLOUD_KB["empresa"]
        return {
            "nombre": e["nombre"],
            "descripcion": e["descripcion"],
            "presencia": e["presencia"],
            "propuesta_valor": e["propuesta_valor"],
            "clientes_destacados": e["clientes_destacados"],
            "partners": e["partners"],
            "reconocimientos": e["reconocimientos"],
        }

    elif nombre == "obtener_servicios":
        servicios = GOTOCLOUD_KB["servicios"]
        servicio = args.get("servicio", "todos")
        if servicio == "todos":
            return {
                "servicios": [
                    {"id": k, "nombre": v.get("nombre"), "descripcion": v.get("descripcion")}
                    for k, v in servicios.items()
                ]
            }
        if servicio in servicios:
            return servicios[servicio]
        return {"error": f"Servicio '{servicio}' no encontrado."}

    elif nombre == "obtener_producto_saas":
        productos = GOTOCLOUD_KB["servicios"]["soluciones_saas"]["productos"]
        producto = args.get("producto", "todos")
        if producto == "todos":
            return {"productos": productos}
        if producto in productos:
            return productos[producto]
        return {"error": f"Producto '{producto}' no encontrado."}

    elif nombre == "obtener_metricas":
        return GOTOCLOUD_KB["metricas"]

    elif nombre == "obtener_contacto":
        contacto = GOTOCLOUD_KB["empresa"]["contacto"].copy()
        contacto["mensaje"] = (
            "Un asesor de GoToCloud puede orientarte y preparar una propuesta personalizada. "
            "Te pueden contactar por WhatsApp al +57 317 427 0148."
        )
        return contacto

    elif nombre == "obtener_beneficios_para_cliente":
        s = GOTOCLOUD_KB["servicios"]
        productos = s["soluciones_saas"]["productos"]
        tipo = args.get("tipo_empresa", "cualquiera")
        necesidad = args.get("necesidad", "").lower()
        recomendaciones: list[dict] = []

        if any(k in necesidad for k in ["costo", "ahorro", "finops", "gasto"]):
            recomendaciones.append({
                "servicio": "Servicios en la Nube con FinOps",
                "razon": "GoToCloud ofrece hasta un 40% de ahorro en costos operativos mediante FinOps.",
                "beneficios": s["cloud_computing"].get("beneficios", []),
            })
        if any(k in necesidad for k in ["document", "factura", "contrato", "papeleo", "manual"]):
            recomendaciones.append({
                "servicio": "OASIS AI",
                "razon": "OASIS AI reduce en 40% el tiempo de gestión documental y en 25-30% los costos operativos.",
                "beneficios": productos["oasis"].get("beneficios", []),
            })
        if any(k in necesidad for k in ["reporte", "dashboard", "power bi", "analítica", "datos"]):
            recomendaciones.append({
                "servicio": "Kármán Reporting Hub + Servicios de Datos",
                "razon": "Kármán permite distribuir reportes Power BI con ahorro en licencias.",
                "beneficios": productos["karman"].get("beneficios", []),
            })
        if any(k in necesidad for k in ["seguridad", "protección", "cumplimiento", "hack"]):
            recomendaciones.append({
                "servicio": "Seguridad en la Nube",
                "razon": "GoToCloud tiene especialización avanzada en protección contra amenazas Microsoft.",
                "beneficios": s["seguridad"].get("especializaciones", []),
            })
        if any(k in necesidad for k in ["migración", "migracion", "nube", "azure", "mover"]):
            beneficios_tipo = (
                s["cloud_computing"]["para_quien"].get("pymes", [])
                if tipo == "pyme"
                else s["cloud_computing"]["para_quien"].get("corporativos", [])
            )
            recomendaciones.append({
                "servicio": "Servicios en la Nube",
                "razon": "GoToCloud ha migrado más de 500 servidores a Azure con 0 horas de downtime.",
                "beneficios": beneficios_tipo,
            })
        if any(k in necesidad for k in ["ia", "inteligencia artificial", "automatiz"]):
            recomendaciones.append({
                "servicio": "OASIS AI + Modernización de Aplicaciones con IA",
                "razon": "GoToCloud tiene especialización avanzada en IA y ML sobre Azure.",
                "beneficios": s["datos"].get("especializaciones", []),
            })
        if any(k in necesidad for k in ["soporte", "administr", "mantenimiento", "operar"]):
            recomendaciones.append({
                "servicio": "Servicios Administrados de TI",
                "razon": "GoToCloud opera la infraestructura 24/7 para que el equipo se enfoque en el negocio.",
                "beneficios": s["servicios_administrados"].get("beneficios", []),
            })
        if not recomendaciones:
            recomendaciones = [{
                "servicio": "Consultoría GoToCloud",
                "razon": "GoToCloud diseña soluciones personalizadas según tu industria y necesidades.",
                "beneficios": [
                    "95% de satisfacción del cliente",
                    "Más de 100 empresas transformadas en Latinoamérica",
                    "Partner certificado Microsoft con múltiples especializaciones avanzadas",
                ],
            }]
        return {"tipo_empresa": tipo, "necesidad": necesidad or "general", "recomendaciones": recomendaciones}

    elif nombre == "registrar_resumen_llamada":
        resumen = args.get("resumen", "").strip()
        intention = args.get("intention", "calida")
        score_lead = args.get("score_lead", 50)
        servicios_interes = args.get("servicios_interes", [])
        recomendaciones = args.get("recomendaciones", "").strip()

        # Validar score_lead
        if score_lead < 0 or score_lead > 100:
            return {"error": "score_lead debe estar entre 0 y 100"}

        # Validar intention
        if intention not in ("fria", "calida", "caliente"):
            return {"error": "intention debe ser 'fria', 'calida' o 'caliente'"}

        # Obtener cliente_id
        cliente_id = _cliente_actual.get("cliente_id")
        cedula = _cliente_actual.get("cedula")

        if not cliente_id and cedula and supabase is not None:
            # Buscar por cédula
            try:
                result = supabase.table("clientes").select("id").eq("cedula", cedula).execute()
                if result.data and len(result.data) > 0:
                    cliente_id = result.data[0]["id"]
            except Exception as ex:
                print(f"[Supabase] Error al buscar cliente por cédula: {ex}")

        if not cliente_id:
            return {"error": "No hay cliente registrado. Llama primero a registrar_datos_cliente."}

        # Insertar en tabla llamadas
        started_at = _cliente_actual.get("started_at")
        row = {
            "cliente_id": cliente_id,
            "resumen": resumen,
            "intention": intention,
            "score_lead": score_lead,
            "servicios_interes": servicios_interes or [],
            "recomendaciones": recomendaciones,
            "started_at": started_at,
        }

        if supabase is not None:
            try:
                resultado = supabase.table("llamadas").insert(row).execute()
                if resultado.data and len(resultado.data) > 0:
                    llamada_id = resultado.data[0]["id"]
                    print(f"[Supabase] Llamada registrada: id={llamada_id}")
                    return {"registrado": True, "llamada_id": llamada_id}
                else:
                    print(f"[Supabase] Llamada registrada sin返回 ID")
                    return {"registrado": True}
            except Exception as ex:
                print(f"[Supabase] Error al registrar llamada: {ex}")
                return {"error": f"Error al registrar llamada: {ex}"}
        else:
            print(f"[BD] Llamada registrada (sin Supabase): cliente_id={cliente_id}, resumen={resumen!r}")
            return {"registrado": True}

    else:
        return {"error": f"Tool '{nombre}' no reconocida."}


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
Eres Camila, agente de atención al cliente por voz de GoToCloud, empresa líder en soluciones cloud y transformación digital en Latinoamérica, partner certificado de Microsoft Azure.

## REGLA ABSOLUTA — TEMA ÚNICO
Tus respuestas SOLO pueden ser sobre GoToCloud y sus servicios. Si alguien pregunta sobre temas que no son de GoToCloud (tecnología general, competidores, política, ciencia, etc.), redirígelos amablemente: "Eso está fuera de mi especialidad, pero lo que sí puedo contarte es cómo GoToCloud puede ayudarte con [tema relacionado]."

## INICIO OBLIGATORIO DE CADA LLAMADA
Lo primero que debes hacer SIEMPRE, antes de cualquier otra cosa, es:
1. Saludar y presentarte como Camila de GoToCloud.
2. Informar que "esta llamada queda registrada bajo nuestra política de tratamiento de datos personales".
3. Pedir el nombre completo del cliente.
4. Pedir el número de cédula.
5. Pedir el nombre de la empresa u organización donde trabaja.
6. Pedir un número de teléfono de contacto.
7. Llamar la tool `registrar_datos_cliente` con todos esos datos.
8. Revisar la respuesta: si `ya_registrado` es `true`, saluda al cliente como ya conocido ("Qué bueno tenerte de vuelta, [nombre]") y confirma si sus datos siguen igual.
9. Luego preguntar en qué puedes ayudar.

## CÓMO USAR LAS TOOLS
- Usa SIEMPRE las tools para dar información. No inventes datos.
- Cuando alguien pregunte por servicios, productos, métricas o contacto, llama la tool correspondiente.
- Después de recibir el resultado de una tool, conviértelo en una respuesta de voz: natural, breve, sin listas largas.

## PRODUCTOS CLAVE QUE DEBES CONOCER
- **Kármán**: portal web para gestionar dashboards Power BI con ahorro en licencias
- **OASIS AI**: automatización de documentos con IA — 40% menos tiempo, 25-30% menos costos
- **DataLoom**: orquestación de datos empresariales
- **Servicios Administrados**: gestión 24/7 de Azure con ITIL, WAF, FinOps

## TONO Y ESTILO DE VOZ
- Habla como en una llamada telefónica real: frases cortas, naturales, sin listas ni bullets.
- Sé profesional pero cercana. Usa "usted" o "tú" según cómo hable el cliente.
- Si no sabes algo, di: "Permítame conectarte con un asesor especializado."
- Cuando haya interés real, ofrece conectar por WhatsApp al +57 317 427 0148.

## FLUJO DE LLAMADA
1. Saludo + presentación + aviso política de datos + pedir nombre, cédula, empresa y teléfono + registrar
2. Preguntar necesidad
3. Identificar tipo de empresa (pyme, corporativo, gobierno)
4. Usar tool adecuada para dar información precisa
5. Ofrecer hablar con asesor si hay interés

## CIERRE DE LLAMADA
Al final de la conversación, cuando el cliente indique que se va, agradezca o no tenga más preguntas:
1. Pregunta si hay algo más en lo que puedas ayudar
2. Si el cliente confirma que no, llama la tool `registrar_resumen_llamada` con:
   - Resumen: qué preguntó, qué le interesó, en qué estado quedó
   - Intención: 'fria' (solo consultas), 'calida' (interés real sin urgencia), 'caliente' (necesidad inmediata)
   - Score: 0-100 según probabilidad de compra
   - Servicios de interés: solo los que mencionó explícitamente
   - Recomendaciones: qué debería hacer el vendedor en el seguimiento
3. Después de recibir la confirmación de la tool, despidete cordialmente
""".strip()


if __name__ == "__main__":
    print("=" * 60)
    print("GoToCloud Voicebot Tool — Test rápido")
    print("=" * 60)
    tests = [
        ("registrar_datos_cliente", {"nombre": "Juan Pérez", "cedula": "1234567890"}),
        ("obtener_informacion_empresa", {}),
        ("obtener_servicios", {"servicio": "servicios_administrados"}),
        ("obtener_producto_saas", {"producto": "oasis"}),
        ("obtener_producto_saas", {"producto": "karman"}),
        ("obtener_metricas", {}),
        ("obtener_beneficios_para_cliente", {"tipo_empresa": "pyme", "necesidad": "documentos y facturas"}),
        ("obtener_contacto", {}),
    ]
    for nombre, args in tests:
        print(f"\n>> {nombre}({args})")
        print(json.dumps(ejecutar_tool(nombre, args), ensure_ascii=False, indent=2)[:400])
    print(f"\nTools OK | {len(GOTOCLOUD_TOOLS)} tools | System prompt: {len(SYSTEM_PROMPT)} chars")
