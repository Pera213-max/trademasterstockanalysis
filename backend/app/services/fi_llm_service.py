"""
Finnish disclosure/news LLM analysis service.

Uses Claude (Anthropic) for all analysis:
- Summary + reasoning (Finnish)
- Impact scoring
- Structured extraction
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import anthropic
except Exception:  # pragma: no cover - optional dependency
    anthropic = None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _truncate(text: str, max_chars: int = 12000) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3) :]
    return f"{head}\n...\n{tail}"


class FiLLMAnalyzer:
    def __init__(self) -> None:
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip()

        self._anthropic_client = None

        if self.anthropic_key and anthropic is not None:
            try:
                self._anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
                logger.info("Claude LLM analyzer initialized with model: %s", self.anthropic_model)
            except Exception as exc:
                logger.warning("Anthropic client init failed: %s", exc)

    def is_enabled(self) -> bool:
        # Temporarily disabled - set ENABLE_LLM=true to re-enable
        if not os.getenv("ENABLE_LLM", "").lower() == "true":
            return False
        return bool(self._anthropic_client)

    def analyze_event(self, event: Dict[str, Any], language: str = "fi") -> Dict[str, Any]:
        title = event.get("title", "")
        body = event.get("body", "")
        event_type = event.get("event_type", "NEWS")
        source = event.get("source", "Unknown")

        payload_text = _truncate(f"Otsikko: {title}\nLähde: {source}\nTyyppi: {event_type}\n\n{body}")

        claude_result = self._analyze_with_claude(payload_text, event_type, language)

        analysis: Dict[str, Any] = {
            "title_fi": None,
            "summary": None,
            "what_changed": None,
            "bullets": [],
            "impact": None,
            "sentiment": None,
            "key_metrics": [],
            "risks": [],
            "watch_items": [],
            "insider": None,
            "providers": {},
            "language": language,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        if claude_result:
            analysis["title_fi"] = claude_result.get("title_fi") or analysis["title_fi"]
            analysis["summary"] = claude_result.get("summary") or analysis["summary"]
            analysis["what_changed"] = claude_result.get("what_changed") or analysis["what_changed"]
            analysis["bullets"] = claude_result.get("bullets") or analysis["bullets"]
            analysis["impact"] = claude_result.get("impact") or analysis["impact"]
            analysis["sentiment"] = claude_result.get("sentiment") or analysis["sentiment"]
            analysis["key_metrics"] = claude_result.get("key_metrics") or analysis["key_metrics"]
            analysis["risks"] = claude_result.get("risks") or analysis["risks"]
            analysis["watch_items"] = claude_result.get("watch_items") or analysis["watch_items"]
            analysis["insider"] = claude_result.get("insider") or analysis["insider"]
            analysis["providers"]["claude"] = {
                "model": self.anthropic_model,
                "ok": True,
            }
        elif self._anthropic_client:
            analysis["providers"]["claude"] = {"model": self.anthropic_model, "ok": False}

        # Simple fallback summary
        if not analysis["summary"]:
            analysis["summary"] = (body or title or "").strip()[:400] or None

        return analysis

    def _analyze_with_claude(self, content: str, event_type: str, language: str) -> Optional[Dict[str, Any]]:
        if not self._anthropic_client:
            return None

        system_prompt = (
            "Olet kokenut suomalaisen pörssitiedotteen analyytikko. "
            "Palauta VAIN JSON. Älä lisää selityksiä."
        )
        user_prompt = (
            "Analysoi seuraava tiedote/uutinen. Palauta JSON muodossa:\n"
            "{\n"
            '  "title_fi": "otsikko käännettynä suomeksi (lyhyt, max 100 merkkiä)",\n'
            '  "summary": "1-3 virkkeen yhteenveto suomeksi",\n'
            '  "what_changed": "mikä muuttui verrattuna aiempaan",\n'
            '  "impact": "POSITIVE|NEUTRAL|NEGATIVE|MIXED",\n'
            '  "sentiment": "POSITIVE|NEUTRAL|NEGATIVE|MIXED",\n'
            '  "bullets": ["3-6 tärkeintä pointtia suomeksi"],\n'
            '  "key_metrics": [{"label": "Liikevaihto", "value": "123", "unit": "EUR"}],\n'
            '  "risks": ["1-5 riskiä suomeksi"],\n'
            '  "watch_items": ["mitä seurata seuraavaksi"],\n'
            '  "insider": {"action": "BUY/SELL", "person": "", "role": "", "shares": "", "price": "", "value": "", "currency": ""}\n'
            "}\n\n"
            "Huom: impact ja sentiment ovat arvioita siitä, onko uutinen positiivinen, negatiivinen, neutraali vai sekalainen osakkeelle.\n"
            "Jos kyseessä on sisäpiirikauppa (managers transactions), täytä insider-kenttä.\n"
            "title_fi: käännä otsikko ytimekkäästi suomeksi.\n\n"
            f"Tyyppi: {event_type}\n"
            f"Kieli: {language}\n\n"
            f"{content}"
        )

        try:
            message = self._anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = ""
            if message and message.content:
                if isinstance(message.content, list):
                    text = "".join(block.text for block in message.content if hasattr(block, "text"))
                else:
                    text = str(message.content)
            return _extract_json(text)
        except Exception as exc:
            logger.warning("Claude analysis failed: %s", exc)
            return None
