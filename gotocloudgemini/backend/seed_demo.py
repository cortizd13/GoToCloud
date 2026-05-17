# Script de seed para poblar tablas de DEMO en Supabase
# Esto permite ver el dashboard con datos realistas.
# Uso: python backend/seed_demo.py

import sys
import os
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Agregar project root al path para poder importar service/
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
load_dotenv(_project_root / "backend" / ".env")

from supabase import create_client

NAMESPACE = uuid.NAMESPACE_DNS
random.seed(42)


def _u(name: str) -> uuid.UUID:
    """UUID determinista para seed_demo."""
    return uuid.uuid5(NAMESPACE, f"gotocloud.demo/{name}")


def random_choice(seq):
    return random.choice(seq) if seq else None


def seed_demo():
    """Popula tablas de demo para que el dashboard tenga datos que mostrar."""

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        print("[SeedDemo] ERROR: SUPABASE_URL o SUPABASE_ANON_KEY no configurados")
        return

    client = create_client(supabase_url, supabase_key)
    print("[SeedDemo] Iniciando carga de datos de demo...")

    # IDs deterministas
    company_id = _u("company")
    contact_templates = [
        {"name": "Carlos Mendoza", "email": "carlos@ejemplo.com", "phone": "+573001234560", "role": "lead"},
        {"name": "Ana Rodriguez", "email": "ana@empresa.co", "phone": "+573112345670", "role": "client"},
        {"name": "Luis Peralta", "email": "luis@tech.io", "phone": "+573223456780", "role": "prospect"},
        {"name": "Maria Gonzalez", "email": "maria@cloud.mx", "phone": "+573334567890", "role": "lead"},
        {"name": "Pedro Sanchez", "email": "pedro@data.ar", "phone": "+573445678900", "role": "client"},
    ]
    legacy_clients = [
        {"nombre": "Juan Perez", "cedula": "1010101010DEMO", "empresa": "Empresa A", "telefono": "+573001111110"},
        {"nombre": "Diana Torres", "cedula": "2020202020DEMO", "empresa": "Empresa B", "telefono": "+573002222220"},
        {"nombre": "Roberto Diaz", "cedula": "3030303030DEMO", "empresa": "Empresa C", "telefono": "+573003333330"},
        {"nombre": "Sofia Herrera", "cedula": "4040404040DEMO", "empresa": "Empresa D", "telefono": "+573004444440"},
    ]

    # -------------------------------------------------
    # 0. Limpiar datos demo previos (idempotencia)
    # -------------------------------------------------
    demo_contact_ids = [str(_u(ct["email"])) for ct in contact_templates]
    demo_thread_ids = []
    for ct in contact_templates:
        for t in range(2):
            demo_thread_ids.append(str(_u(f"{ct['email']}/thread/{t}")))

    def _delete(table, column, values):
        if not values:
            return
        try:
            for val in values:
                client.table(table).delete().eq(column, val).execute()
        except Exception as e:
            print(f"[SeedDemo] (limpieza) {table} {column}={val}: {e}")

    # Borrar hijos primero
    _delete("analytics_events", "thread_id", demo_thread_ids)
    _delete("messages", "session_id", demo_thread_ids)  # session_id no es thread_id, pero no importa; borramos por session luego
    _delete("memory_summaries", "thread_id", demo_thread_ids)
    # Borrar sessions por thread_id
    for tid in demo_thread_ids:
        try:
            client.table("conversation_sessions").delete().eq("thread_id", tid).execute()
        except Exception:
            pass
    _delete("conversation_threads", "id", demo_thread_ids)
    # Borrar channel_identities y contact_companies por contact_id
    for cid in demo_contact_ids:
        try:
            client.table("channel_identities").delete().eq("contact_id", cid).execute()
            client.table("contact_companies").delete().eq("contact_id", cid).execute()
        except Exception:
            pass
    _delete("contacts", "id", demo_contact_ids)
    # Borrar company (solo la demo)
    try:
        client.table("companies").delete().eq("id", str(company_id)).execute()
    except Exception:
        pass
    # Borrar legacy clients/sesiones por cedula
    for lc in legacy_clients:
        try:
            existing = client.table("clientes").select("id").eq("cedula", lc["cedula"]).execute()
            for row in existing.data or []:
                client.table("sesiones").delete().eq("cliente_id", row["id"]).execute()
                client.table("clientes").delete().eq("id", row["id"]).execute()
        except Exception:
            pass

    # -------------------------------------------------
    # 1. Compania demo
    # -------------------------------------------------
    try:
        client.table("companies").insert({
            "id": str(company_id),
            "name": "GoToCloud Demo Corp",
            "settings": {"industry": "cloud", "region": "LATAM"},
        }).execute()
        print("[SeedDemo] [OK] Compania demo insertada")
    except Exception as e:
        print(f"[SeedDemo] ERROR en companies: {e}")

    # -------------------------------------------------
    # 2. Contactos + channel_identities
    # -------------------------------------------------
    contacts_map = {}
    channel_identities_map = {}

    for ct in contact_templates:
        contact_id = _u(ct["email"])
        contacts_map[ct["email"]] = contact_id
        try:
            client.table("contacts").insert({
                "id": str(contact_id),
                "name": ct["name"],
                "emails": [ct["email"]],
                "phones": [ct["phone"]],
                "metadata": {"role": ct["role"], "source": "seed_demo"},
            }).execute()

            webchat_identity = _u(f"{ct['email']}/webchat")
            channel_identities_map.setdefault(ct["email"], {})["webchat"] = webchat_identity
            client.table("channel_identities").insert({
                "id": str(webchat_identity),
                "contact_id": str(contact_id),
                "channel_type": "webchat",
                "external_id": f"webchat_demo_{ct['email'].split('@')[0]}",
                "profile_data": {"browser": "Chrome"},
            }).execute()

            voice_identity = _u(f"{ct['email']}/voice")
            channel_identities_map[ct["email"]]["voice"] = voice_identity
            client.table("channel_identities").insert({
                "id": str(voice_identity),
                "contact_id": str(contact_id),
                "channel_type": "voice",
                "external_id": ct["phone"],
                "profile_data": {"carrier": "Claro"},
            }).execute()

            client.table("contact_companies").insert({
                "contact_id": str(contact_id),
                "company_id": str(company_id),
                "role": ct["role"],
            }).execute()

            print(f"[SeedDemo] [OK] Contacto {ct['name']} creado")
        except Exception as e:
            print(f"[SeedDemo] ERROR en contacto {ct['name']}: {e}")

    # -------------------------------------------------
    # 3. Clientes legacy
    # -------------------------------------------------
    legacy_client_ids = {}
    for lc in legacy_clients:
        try:
            result = client.table("clientes").insert({
                "nombre": lc["nombre"],
                "cedula": lc["cedula"],
                "empresa": lc["empresa"],
                "telefono": lc["telefono"],
            }).execute()
            inserted_id = result.data[0]["id"]
            legacy_client_ids[lc["cedula"]] = inserted_id
            print(f"[SeedDemo] [OK] Cliente legacy {lc['nombre']} creado (id={inserted_id})")
        except Exception as e:
            try:
                existing = client.table("clientes").select("id").eq("cedula", lc["cedula"]).execute()
                if existing.data:
                    legacy_client_ids[lc["cedula"]] = existing.data[0]["id"]
                    print(f"[SeedDemo] [OK] Cliente legacy {lc['nombre']} ya existia (id={existing.data[0]['id']})")
                else:
                    print(f"[SeedDemo] ERROR insertando/recuperando cliente legacy {lc['nombre']}: {e}")
            except Exception as e2:
                print(f"[SeedDemo] ERROR insertando/recuperando cliente legacy {lc['nombre']}: {e} / {e2}")

    # -------------------------------------------------
    # 4. Sesiones legacy
    # -------------------------------------------------
    intentions = ["fria", "calida", "caliente"]
    servicios = ["cloud_computing", "seguridad", "datos", "modernizacion_apps", "servicios_administrados"]
    recomendaciones_list = [
        "Contactar en 24h para demo de Azure",
        "Enviar propuesta de seguridad",
        "Agendar llamada con arquitecto cloud",
        "Enviar caso de exito de OASIS AI",
        "Seguimiento en 48h",
        "Escalar a equipo comercial",
    ]

    now = datetime.now(timezone.utc)
    for cedula, client_id in legacy_client_ids.items():
        for i in range(random.randint(1, 3)):
            started = now - timedelta(days=random.randint(0, 2), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            duracion = random.randint(60, 900)
            ended = started + timedelta(seconds=duracion)
            intention = random_choice(intentions)
            score_lead = random.randint(30, 95) if intention == "fria" else random.randint(50, 100)
            servicios_interes = random.sample(servicios, k=random.randint(1, 3))
            recomendacion = random_choice(recomendaciones_list)

            try:
                client.table("sesiones").insert({
                    "cliente_id": client_id,
                    "started_at": started.isoformat(),
                    "ended_at": ended.isoformat(),
                    "duracion_segundos": duracion,
                    "resumen": f"Llamada de demo sobre {', '.join(servicios_interes)}",
                    "intention": intention,
                    "score_lead": score_lead,
                    "servicios_interes": servicios_interes,
                    "recomendaciones": recomendacion,
                }).execute()
            except Exception as e:
                print(f"[SeedDemo] ERROR sesion legacy cliente {client_id}: {e}")

    print("[SeedDemo] [OK] Sesiones legacy insertadas")

    # -------------------------------------------------
    # 5. Conversation threads + sessions + messages + analytics_events
    # -------------------------------------------------
    channels = ["webchat", "voice", "whatsapp"]
    topics = ["Consulta Azure", "Demo OASIS AI", "Soporte seguridad", "Migracion cloud", "FinOps"]

    for email, contact_id in contacts_map.items():
        for t in range(random.randint(1, 2)):
            thread_id = _u(f"{email}/thread/{t}")
            topic = random_choice(topics)
            try:
                client.table("conversation_threads").insert({
                    "id": str(thread_id),
                    "company_id": str(company_id),
                    "contact_id": str(contact_id),
                    "status": "active",
                    "topic": topic,
                    "metadata": {"campaign": "seed_demo"},
                }).execute()
            except Exception as e:
                print(f"[SeedDemo] ERROR thread {thread_id}: {e}")
                continue

            for s in range(random.randint(1, 2)):
                session_id = _u(f"{email}/thread/{t}/session/{s}")
                channel = random_choice(channels)
                channel_identity_id = channel_identities_map.get(email, {}).get(channel)
                started = now - timedelta(days=random.randint(0, 1), hours=random.randint(0, 23))
                ended = started + timedelta(minutes=random.randint(5, 45))
                status = "completed"

                try:
                    client.table("conversation_sessions").insert({
                        "id": str(session_id),
                        "thread_id": str(thread_id),
                        "channel_type": channel,
                        "channel_identity_id": str(channel_identity_id) if channel_identity_id else None,
                        "status": status,
                        "started_at": started.isoformat(),
                        "ended_at": ended.isoformat(),
                    }).execute()
                except Exception as e:
                    print(f"[SeedDemo] ERROR session {session_id}: {e}")
                    continue

                num_messages = random.randint(5, 15)
                msg_time = started
                for m in range(num_messages):
                    sender = "user" if m % 2 == 0 else "agent"
                    content = f"Mensaje de demo #{m+1} en sesion {str(session_id)[:8]}"
                    sentiment = random_choice(["positive", "negative", "neutral"])
                    metadata = {"sentiment": sentiment, "seed": True}
                    msg_time += timedelta(seconds=random.randint(10, 60))

                    try:
                        client.table("messages").insert({
                            "id": str(uuid.uuid4()),
                            "session_id": str(session_id),
                            "sender": sender,
                            "content": content,
                            "metadata": metadata,
                            "created_at": msg_time.isoformat(),
                        }).execute()
                    except Exception as e:
                        print(f"[SeedDemo] ERROR message: {e}")

                for ev in range(random.randint(1, 3)):
                    event_type = random_choice(["session_end", "rating", "feedback", "escalation"])
                    payload = {}
                    if event_type == "rating":
                        payload = {"csat": random.randint(3, 5), "comment": "Buen servicio"}
                    elif event_type == "feedback":
                        payload = {"rating": random.randint(3, 5)}
                    else:
                        payload = {"reason": random_choice(topics)}

                    try:
                        client.table("analytics_events").insert({
                            "id": str(uuid.uuid4()),
                            "thread_id": str(thread_id),
                            "session_id": str(session_id),
                            "event_type": event_type,
                            "payload": payload,
                            "created_at": (started + timedelta(minutes=random.randint(1, 30))).isoformat(),
                        }).execute()
                    except Exception as e:
                        print(f"[SeedDemo] ERROR analytics_event: {e}")

    print("[SeedDemo] [OK] Threads, sessions, messages y analytics insertados")

    # -------------------------------------------------
    # 6. Memory summaries
    # -------------------------------------------------
    try:
        threads_result = client.table("conversation_threads").select("id").execute()
        for row in threads_result.data or []:
            client.table("memory_summaries").insert({
                "id": str(uuid.uuid4()),
                "thread_id": row["id"],
                "summary_text": f"Resumen de thread {row['id'][:8]}: conversacion sobre {random_choice(topics)}.",
            }).execute()
        print("[SeedDemo] [OK] Memory summaries insertadas")
    except Exception as e:
        print(f"[SeedDemo] ERROR memory_summaries: {e}")

    # -------------------------------------------------
    # Verificacion final
    # -------------------------------------------------
    print("\n[SeedDemo] Verificando counts...")
    tables = [
        "companies", "contacts", "contact_companies", "channel_identities",
        "conversation_threads", "conversation_sessions", "messages",
        "memory_summaries", "analytics_events", "clientes", "sesiones"
    ]
    total_rows = 0
    for tbl in tables:
        try:
            count_result = client.table(tbl).select("*", count="exact").limit(0).execute()
            count = count_result.count or 0
            total_rows += count
            print(f"  - {tbl}: {count} row(s)")
        except Exception as e:
            print(f"  - {tbl}: ERROR {e}")

    print(f"\n[SeedDemo] [OK] Seed completado. Total filas demo: {total_rows}")


if __name__ == "__main__":
    seed_demo()
