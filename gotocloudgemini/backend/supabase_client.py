# Supabase client singleton para la base de conocimientos de GoToCloud

import os
import sys
from pathlib import Path

# Cargar variables de entorno desde backend/.env
from dotenv import load_dotenv

# Ruta al .env en backend/
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Singleton client — inicializado una sola vez al importar el módulo
supabase = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        print(f"[Supabase] Error al inicializar cliente: {e}")
        supabase = None
else:
    print("[Supabase] Advertencia: SUPABASE_URL o SUPABASE_ANON_KEY no configurados en .env")


def is_connected() -> bool:
    """Health check — retorna True si Supabase está accesible."""
    if supabase is None:
        return False
    try:
        supabase.table("clientes").select("id").limit(1).execute()
        return True
    except Exception:
        return False