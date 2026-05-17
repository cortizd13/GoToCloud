"""Tests para el sistema de metadata de llamadas (call-metadata).

Cubre:
- Tool `registrar_datos_cliente` con upsert por cédula única
- Tool `registrar_resumen_llamada` con validación de parámetros
- Cliente ya registrado vs nuevo
- Fallback timeout (lógica de defaults)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Mock Supabase inteligente ────────────────────────────────
# Necesitamos un mock que maneje el flujo:
#   1. select("id").eq("cedula", X).execute() → existente o vacío
#   2. insert(row).execute() → nuevo ID
#   3. update(row).eq("id", X).execute() → update existente


class _FakeQuery:
    """Simula una query chain de Supabase: table → select/insert/update → eq → execute."""

    def __init__(self, return_data=None):
        self._return_data = return_data or []

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._return_data)


class _FakeQueryLlamadas(_FakeQuery):
    """Query especializada para la tabla llamadas."""

    def __init__(self, fake_supabase: _FakeSupabase):
        super().__init__([])
        self._fake = fake_supabase
        self._method = None
        self._insert_data = None

    def select(self, *args, **kwargs):
        self._method = "select"
        return self

    def insert(self, data):
        self._method = "insert"
        self._insert_data = data
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        if self._method == "insert":
            lid = self._fake._next_llamada_id
            self._fake._next_llamada_id += 1
            self._fake._llamadas[lid] = dict(self._insert_data)
            return MagicMock(data=[{"id": lid}])
        return MagicMock(data=[])


class _FakeSupabase:
    """Simula supabase con estado interno para upsert."""

    def __init__(self):
        self._clientes: dict[str, dict] = {}
        self._llamadas: dict[str, dict] = {}
        self._next_id = 1
        self._next_llamada_id = 1

    def table(self, name: str) -> _FakeQuery:
        if name == "clientes":
            return _FakeQueryClientes(self)
        if name == "llamadas":
            return _FakeQueryLlamadas(self)
        return _FakeQuery([])


class _FakeQueryClientes(_FakeQuery):
    """Query especializada para la tabla clientes con upsert real."""

    def __init__(self, fake_supabase: _FakeSupabase):
        super().__init__([])
        self._fake = fake_supabase
        self._method = None
        self._eq_field = None
        self._eq_value = None
        self._insert_data = None
        self._update_data = None
        self._update_id = None

    def select(self, *args, **kwargs):
        self._method = "select"
        return self

    def insert(self, data):
        self._method = "insert"
        self._insert_data = data
        return self

    def update(self, data):
        self._method = "update"
        self._update_data = data
        return self

    def eq(self, field, value):
        if self._method == "select":
            self._eq_field = field
            self._eq_value = value
        elif self._method == "update":
            self._update_id = value
        return self

    def execute(self):
        if self._method == "select" and self._eq_field == "cedula":
            # Buscar por cédula
            for cid, rec in self._fake._clientes.items():
                if rec["cedula"] == self._eq_value:
                    return MagicMock(data=[{"id": cid}])
            return MagicMock(data=[])

        if self._method == "insert":
            cid = self._fake._next_id
            self._fake._next_id += 1
            self._fake._clientes[cid] = dict(self._insert_data)
            return MagicMock(data=[{"id": cid}])

        if self._method == "update" and self._update_id:
            if self._update_id in self._fake._clientes:
                self._fake._clientes[self._update_id].update(self._update_data)
            return MagicMock(data=[{"id": self._update_id}])

        return MagicMock(data=[])


# ── Configurar el mock ───────────────────────────────────────
_fake_supabase = _FakeSupabase()

_module_path = str(Path(__file__).parent.parent)
if _module_path not in sys.path:
    sys.path.insert(0, _module_path)

with patch.dict("sys.modules", {
    "backend.supabase_client": MagicMock(
        supabase=_fake_supabase,
        is_connected=lambda: True,
    )
}):
    from service.gotocloud_voicebot_tool import (
        _cliente_actual,
        ejecutar_tool,
    )


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _reset():
    """Limpia estado entre tests."""
    _cliente_actual.clear()
    _fake_supabase._clientes.clear()
    _fake_supabase._llamadas.clear()
    _fake_supabase._next_id = 1
    _fake_supabase._next_llamada_id = 1


def _registrar_cliente(**kwargs):
    """Helper: registra un cliente y devuelve el response."""
    data = {
        "nombre": "Juan Pérez",
        "cedula": "1234567890",
        "empresa": "Empresa SA",
        "telefono": "3001234567",
    }
    data.update(kwargs)
    return ejecutar_tool("registrar_datos_cliente", data)


# ═══════════════════════════════════════════════════════════════
#  registrar_datos_cliente — upsert por cédula
# ═══════════════════════════════════════════════════════════════

class TestRegistrarDatosCliente:
    def setup_method(self):
        _reset()

    def test_registra_cliente_nuevo(self):
        resp = _registrar_cliente()
        assert resp["registrado"] is True
        assert resp["ya_registrado"] is False  # ← nuevo!
        assert resp["nombre"] == "Juan Pérez"
        assert resp["cedula"] == "1234567890"
        assert resp["empresa"] == "Empresa SA"
        assert resp["telefono"] == "3001234567"

    def test_cliente_nuevo_recibe_mensaje_creacion(self):
        resp = _registrar_cliente()
        assert "registrados correctamente" in resp["mensaje"]

    def test_retorna_cliente_id(self):
        resp = _registrar_cliente()
        assert "cliente_id" in resp
        assert resp["cliente_id"] == 1  # primer ID

    def test_guarda_en_memoria(self):
        _registrar_cliente()
        assert _cliente_actual["nombre"] == "Juan Pérez"
        assert _cliente_actual["cedula"] == "1234567890"
        assert _cliente_actual["empresa"] == "Empresa SA"
        assert _cliente_actual["telefono"] == "3001234567"
        assert _cliente_actual["cliente_id"] == 1

    def test_funciona_solo_con_requeridos(self):
        _reset()
        resp = ejecutar_tool("registrar_datos_cliente", {
            "nombre": "Ana",
            "cedula": "9876543210",
        })
        assert resp["registrado"] is True
        assert resp["nombre"] == "Ana"
        assert resp["cedula"] == "9876543210"
        assert resp.get("empresa") == ""
        assert resp.get("telefono") == ""


# ═══════════════════════════════════════════════════════════════
#  registrar_datos_cliente — cliente existente (misma cédula)
# ═══════════════════════════════════════════════════════════════

class TestClienteYaRegistrado:
    def setup_method(self):
        _reset()
        # Registrar primera vez
        _registrar_cliente()

    def test_misma_cedula_detecta_existente(self):
        """Segundo registro con misma cédula → ya_registrado=True."""
        resp = _registrar_cliente()
        assert resp["ya_registrado"] is True

    def test_misma_cedula_devuelve_mismo_id(self):
        resp = _registrar_cliente()
        assert resp["cliente_id"] == 1  # mismo ID

    def test_misma_cedula_recibe_mensaje_actualizacion(self):
        resp = _registrar_cliente()
        assert "ya registrado" in resp["mensaje"].lower()
        assert "actualizados" in resp["mensaje"].lower()

    def test_misma_cedula_actualiza_datos(self):
        """Si cambia teléfono, se actualiza."""
        resp = _registrar_cliente(telefono="9998887777")
        assert resp["telefono"] == "9998887777"
        assert resp["ya_registrado"] is True

    def test_cedula_diferente_es_nuevo_cliente(self):
        """Cédula distinta → nuevo cliente, ID secuencial."""
        resp = _registrar_cliente(
            nombre="Maria Gomez",
            cedula="5555555555",
            empresa="Otra SA",
            telefono="3000000000",
        )
        assert resp["ya_registrado"] is False
        assert resp["cliente_id"] == 2  # ID nuevo


# ═══════════════════════════════════════════════════════════════
#  registrar_resumen_llamada
# ═══════════════════════════════════════════════════════════════

class TestRegistrarResumenLlamada:
    def setup_method(self):
        _reset()
        _registrar_cliente()

    def test_registra_resumen_valido(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Cliente interesado en cloud computing y seguridad.",
            "intention": "calida",
            "score_lead": 75,
            "servicios_interes": ["cloud_computing", "seguridad"],
            "recomendaciones": "Enviar propuesta de servicios administrados.",
        })
        assert resp["registrado"] is True
        assert "llamada_id" in resp

    def test_rechaza_score_menor_a_0(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": -1,
        })
        assert "error" in resp
        assert "score_lead" in resp["error"].lower()

    def test_rechaza_score_mayor_a_100(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "calida",
            "score_lead": 101,
        })
        assert "error" in resp
        assert "score_lead" in resp["error"].lower()

    def test_rechaza_intention_invalida(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "super_caliente",
            "score_lead": 50,
        })
        assert "error" in resp
        assert "intention" in resp["error"].lower()

    def test_acepta_intention_fria(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Solo preguntó precios.",
            "intention": "fria",
            "score_lead": 10,
        })
        assert resp["registrado"] is True

    def test_acepta_intention_caliente(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Quiere comprar ya.",
            "intention": "caliente",
            "score_lead": 95,
        })
        assert resp["registrado"] is True

    def test_sin_servicios_opcionales_no_falla(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Consulta general.",
            "intention": "fria",
            "score_lead": 5,
        })
        assert resp["registrado"] is True

    def test_resumen_de_llamada_vinculado_al_cliente(self):
        """El resumen se registra con el cliente_id de _cliente_actual."""
        _reset()
        _registrar_cliente(cedula="1111111111", nombre="Cliente A")
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Consulta sobre cloud.",
            "intention": "calida",
            "score_lead": 60,
        })
        assert resp["registrado"] is True
        assert "llamada_id" in resp


# ═══════════════════════════════════════════════════════════════
#  registrar_resumen_llamada — sin cliente registrado
# ═══════════════════════════════════════════════════════════════

class TestResumenSinCliente:
    def setup_method(self):
        _reset()

    def test_rechaza_sin_cliente(self):
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Test",
            "intention": "fria",
            "score_lead": 50,
        })
        assert "error" in resp
        assert "cliente" in resp["error"].lower()


# ═══════════════════════════════════════════════════════════════
#  Fallback timeout — defaults correctos
# ═══════════════════════════════════════════════════════════════

class TestFallbackDefaults:
    def setup_method(self):
        _reset()
        _registrar_cliente()

    def test_fallback_defaults_son_validos(self):
        """Los defaults del timeout fallback deben pasar validación."""
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "Llamada finalizada por tiempo de espera.",
            "intention": "calida",
            "score_lead": 50,
            "servicios_interes": [],
            "recomendaciones": "Cliente no completó la conversación.",
        })
        assert resp["registrado"] is True

    def test_fallback_con_resumen_vacio(self):
        """Resumen vacío debe ser aceptado (es válido)."""
        resp = ejecutar_tool("registrar_resumen_llamada", {
            "resumen": "",
            "intention": "calida",
            "score_lead": 50,
        })
        assert resp["registrado"] is True
