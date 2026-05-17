# Script de seed para populate las tablas de Supabase con datos de GOTOCLOUD_KB
# Uso: python backend/seed_kb.py

import sys
import os
import json
from pathlib import Path

# Agregar project root al path para poder importar service/
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
load_dotenv(_project_root / "backend" / ".env")

from supabase import create_client
from service.gotocloud_voicebot_tool import GOTOCLOUD_KB


def seed():
    """Popula las tablas de Supabase con datos del KB en memoria."""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("[Seed] ERROR: SUPABASE_URL o SUPABASE_ANON_KEY no configurados")
        return
    
    client = create_client(supabase_url, supabase_key)
    kb = GOTOCLOUD_KB
    
    print("[Seed] Iniciando populate de tablas en Supabase...")
    
    # ─────────────────────────────────────────────
    # 1. Empresa (id=1)
    # ─────────────────────────────────────────────
    empresa_data = {
        "id": 1,
        "nombre": kb["empresa"]["nombre"],
        "descripcion": kb["empresa"]["descripcion"],
        "presencia": kb["empresa"]["presencia"],
        "propuesta_valor": json.dumps(kb["empresa"]["propuesta_valor"]),
        "clientes_destacados": json.dumps(kb["empresa"]["clientes_destacados"]),
        "partners": json.dumps(kb["empresa"]["partners"]),
        "reconocimientos": json.dumps(kb["empresa"]["reconocimientos"]),
        "contacto": json.dumps(kb["empresa"]["contacto"]),
    }
    
    try:
        client.table("empresa").upsert(empresa_data).execute()
        print("[Seed] ✓ Empresa insertada (id=1)")
    except Exception as e:
        print(f"[Seed] ERROR en empresa: {e}")
    
    # ─────────────────────────────────────────────
    # 2. Servicios (6 rows)
    # ─────────────────────────────────────────────
    servicios_count = 0
    for sid, sdata in kb["servicios"].items():
        row = {
            "id": sid,
            "nombre": sdata.get("nombre", ""),
            "descripcion": sdata.get("descripcion", ""),
        }
        
        # Agregar campos opcionales si existen
        if "categoria" in sdata:
            row["categoria"] = sdata["categoria"]
        if "subcategoria" in sdata:
            row["subcategoria"] = sdata["subcategoria"]
        if "beneficios" in sdata:
            row["beneficios"] = json.dumps(sdata["beneficios"])
        if "para_quien" in sdata:
            row["para_quien"] = json.dumps(sdata["para_quien"])
        if "pilares" in sdata:
            row["pilares"] = json.dumps(sdata["pilares"])
        if "metodologias" in sdata:
            row["metodologias"] = json.dumps(sdata["metodologias"])
        if "alcance" in sdata:
            row["alcance"] = json.dumps(sdata["alcance"])
        if "reportes" in sdata:
            row["reportes"] = json.dumps(sdata["reportes"])
        if "especializaciones" in sdata:
            row["especializaciones"] = json.dumps(sdata["especializaciones"])
        if "partners" in sdata:
            row["partners"] = json.dumps(sdata["partners"])
        
        try:
            client.table("servicios").upsert(row).execute()
            servicios_count += 1
        except Exception as e:
            print(f"[Seed] ERROR en servicio {sid}: {e}")
    
    print(f"[Seed] ✓ {servicios_count} servicios insertados")
    
    # ─────────────────────────────────────────────
    # 3. Productos SaaS (3 rows) — vienen de soluciones_saas.productos
    # ─────────────────────────────────────────────
    productos_count = 0
    productos_data = kb["servicios"].get("soluciones_saas", {}).get("productos", {})
    for pid, pdata in productos_data.items():
        row = {
            "id": pid,
            "nombre": pdata.get("nombre", ""),
            "descripcion": pdata.get("descripcion", ""),
            "para_quien": pdata.get("para_quien", ""),
        }
        if "funcionalidades" in pdata:
            row["funcionalidades"] = json.dumps(pdata["funcionalidades"])
        if "beneficios" in pdata:
            row["beneficios"] = json.dumps(pdata["beneficios"])
        if "seguridad" in pdata:
            row["seguridad"] = json.dumps(pdata["seguridad"])
        
        try:
            client.table("productos_saas").upsert(row).execute()
            productos_count += 1
        except Exception as e:
            print(f"[Seed] ERROR en producto {pid}: {e}")
    
    print(f"[Seed] ✓ {productos_count} productos SaaS insertados")
    
    # ─────────────────────────────────────────────
    # 4. Métricas (8 rows)
    # ─────────────────────────────────────────────
    metricas_count = 0
    for clave, valor in kb["metricas"].items():
        try:
            client.table("metricas").upsert({"clave": clave, "valor": valor}).execute()
            metricas_count += 1
        except Exception as e:
            print(f"[Seed] ERROR en métrica {clave}: {e}")
    
    print(f"[Seed] ✓ {metricas_count} métricas insertadas")
    
    # ─────────────────────────────────────────────
    # Verificar counts
    # ─────────────────────────────────────────────
    print("\n[Seed] Verificando counts...")
    try:
        empresa_count = client.table("empresa").select("id", count="exact").execute().count
        servicios_count_db = client.table("servicios").select("id", count="exact").execute().count
        metricas_count_db = client.table("metricas").select("clave", count="exact").execute().count
        productos_count_db = client.table("productos_saas").select("id", count="exact").execute().count
        
        print(f"[Seed] Resultados finales:")
        print(f"  - empresa: {empresa_count} row(s)")
        print(f"  - servicios: {servicios_count_db} row(s)")
        print(f"  - metricas: {metricas_count_db} row(s)")
        print(f"  - productos_saas: {productos_count_db} row(s)")
        
        if empresa_count >= 1 and servicios_count_db >= 6 and metricas_count_db >= 8 and productos_count_db >= 3:
            print("\n[Seed] ✓ Seed completado exitosamente!")
        else:
            print("\n[Seed] ADVERTENCIA: Algunos counts no alcanzaron el objetivo")
    except Exception as e:
        print(f"[Seed] ERROR al verificar counts: {e}")


if __name__ == "__main__":
    seed()