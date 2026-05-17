"""Tests for T-106: SYSTEM_PROMPT conversion directives.

These tests verify that the SYSTEM_PROMPT contains the conversion-focused
directives added for PR slice #3:
- Post-registration qualification (calificar_necesidad)
- Hot lead detection and scheduling (agendar_cita, notificar_lead_caliente)
- Enhanced close with appointment confirmation and email follow-up
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path for service/ imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestSystemPromptConversionDirectives:
    """T-106: SYSTEM_PROMPT must contain conversion-focused directives."""

    @pytest.fixture(autouse=True)
    def load_system_prompt(self):
        from service.gotocloud_voicebot_tool import SYSTEM_PROMPT
        self.prompt = SYSTEM_PROMPT

    # ── Directive 1: Post-registration qualification ──────────────────────

    def test_prompt_mentions_calificar_necesidad_after_registration(self):
        """SYSTEM_PROMPT must instruct to use calificar_necesidad after registration."""
        assert "calificar_necesidad" in self.prompt

    def test_prompt_mentions_presupuesto_estimado(self):
        """SYSTEM_PROMPT must mention asking about budget."""
        assert "presupuesto" in self.prompt.lower()

    def test_prompt_mentions_timeline(self):
        """SYSTEM_PROMPT must mention asking about timeline."""
        assert "timeline" in self.prompt.lower()

    def test_prompt_has_post_registration_section(self):
        """SYSTEM_PROMPT must have a section about post-registration conversion."""
        assert "conversión" in self.prompt.lower() or "post-registro" in self.prompt.lower()

    def test_prompt_says_siempre_after_registration(self):
        """SYSTEM_PROMPT must use 'SIEMPRE' for post-registration qualification."""
        # Check that SIEMPRE appears in context of post-registration
        assert "SIEMPRE" in self.prompt

    # ── Directive 2: Hot lead detection and scheduling ────────────────────

    def test_prompt_mentions_agendar_cita_for_hot_leads(self):
        """SYSTEM_PROMPT must instruct to use agendar_cita when lead shows buying intent."""
        assert "agendar_cita" in self.prompt

    def test_prompt_mentions_notificar_lead_caliente(self):
        """SYSTEM_PROMPT must instruct to notify hot leads."""
        assert "notificar_lead_caliente" in self.prompt

    def test_prompt_mentions_score_threshold(self):
        """SYSTEM_PROMPT must reference the score_lead > 70 threshold."""
        assert "70" in self.prompt

    def test_prompt_mentions_intencion_caliente(self):
        """SYSTEM_PROMPT must reference 'caliente' intention for hot leads."""
        assert "caliente" in self.prompt.lower()

    def test_prompt_describes_hot_lead_signals(self):
        """SYSTEM_PROMPT must describe signals of buying intent (prices, urgency)."""
        prompt_lower = self.prompt.lower()
        # Must mention at least one buying intent signal
        hot_signals = ["precio", "urgencia", "compara", "cuánto cuesta", "timeline inmediato"]
        assert any(signal in prompt_lower for signal in hot_signals)

    def test_prompt_has_hot_lead_detection_section(self):
        """SYSTEM_PROMPT must have a section about hot lead detection."""
        assert "intención de compra" in self.prompt.lower() or "lead caliente" in self.prompt.lower()

    # ── Directive 3: Enhanced close ──────────────────────────────────────

    def test_prompt_mentions_appointment_confirmation_at_close(self):
        """SYSTEM_PROMPT must instruct to confirm appointment date/time at close."""
        prompt_lower = self.prompt.lower()
        assert "confirm" in prompt_lower or "confirma" in prompt_lower

    def test_prompt_mentions_email_followup(self):
        """SYSTEM_PROMPT must mention email follow-up for interested leads who didn't schedule."""
        assert "email" in self.prompt.lower() or "seguimiento" in self.prompt.lower()

    def test_prompt_close_section_has_four_steps(self):
        """CIERRE DE LLAMADA section must have step 3 (post-tool actions) and step 4 (farewell)."""
        assert "Después de recibir la confirmación de la tool" in self.prompt

    # ── Tone preservation ────────────────────────────────────────────────

    def test_prompt_still_has_camila_persona(self):
        """SYSTEM_PROMPT must still identify as Camila."""
        assert "Camila" in self.prompt

    def test_prompt_still_has_gotocloud_context(self):
        """SYSTEM_PROMPT must still mention GoToCloud."""
        assert "GoToCloud" in self.prompt

    def test_prompt_still_has_voice_tone_guidelines(self):
        """SYSTEM_PROMPT must still have voice tone guidelines."""
        assert "TONO" in self.prompt or "tono" in self.prompt

    def test_prompt_still_has_absolute_topic_rule(self):
        """SYSTEM_PROMPT must still have the single-topic rule."""
        assert "TEMA ÚNICO" in self.prompt or "TEMA UNICO" in self.prompt

    def test_prompt_still_has_mandatory_start(self):
        """SYSTEM_PROMPT must still have the mandatory call start."""
        assert "INICIO OBLIGATORIO" in self.prompt

    def test_prompt_still_has_security_rule(self):
        """SYSTEM_PROMPT must still have the security rule for sensitive data."""
        assert "SEGURIDAD" in self.prompt

    # ── Tool references consistency ──────────────────────────────────────

    def test_all_conversion_tools_mentioned_in_prompt(self):
        """All three conversion tools must be referenced in SYSTEM_PROMPT."""
        conversion_tools = ["calificar_necesidad", "agendar_cita", "notificar_lead_caliente"]
        for tool in conversion_tools:
            assert tool in self.prompt, f"Tool '{tool}' not found in SYSTEM_PROMPT"

    def test_prompt_not_pushy_tone(self):
        """SYSTEM_PROMPT should guide naturally, not be pushy."""
        prompt_lower = self.prompt.lower()
        # Should have natural language guidance
        assert "natural" in prompt_lower or "amable" in prompt_lower or "sin sonar" in prompt_lower
