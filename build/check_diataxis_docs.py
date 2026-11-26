#!/usr/bin/env python3
# ===========================================================================
# Script:      build/check_diataxis_docs.py
# Description: Zero-dependency validator for 4-section documentation layout,
#              internal relative links, section governance, MkDocs config,
#              line-length/paragraph readability, Git-native GFM checks, and
#              procedural rules in 02-how-to-guides/.
# Author:      Jean-Marie Renouard / Antigravity
# Usage:       python3 build/check_diataxis_docs.py docs [--strict] [--mkdocs-config mkdocs.yml]
# ===========================================================================

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REQUIRED_QUADRANTS = (
    "01-tutorials",
    "02-how-to-guides",
    "03-reference",
    "04-explanation",
)

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
LINK_FULL_RE = re.compile(r"(!?\[[^\]]*\])\(([^)\n]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
PARAGRAPH_HEADING_RE = re.compile(r"^#{1,6}\s")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
PARAGRAPH_TABLE_RE = re.compile(r"^\s*\|")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S+")
PARAGRAPH_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
HR_RE = re.compile(r"^\s*(?:[-*_]\s*){3,}$")
LINK_REF_DEF_RE = re.compile(r"^\s*\[[^\]]+\]:\s")
BLOCKQUOTE_RE = re.compile(r"^\s*>")
BARE_URL_RE = re.compile(r"https?://[^\s)>]+")
ABBREV_RE = re.compile(r"\b(?:e\.g|i\.e|etc|vs|cf)\.", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<!\.)[.!?]+(?:['\")\]]*)(?=\s|$)")
ADMONITION_START_RE = re.compile(r"^(?:!!!|\?\?\?\+?)\s+([A-Za-z0-9_-]+)(?:\s+.*)?$")
EXTERNAL_SCHEME_RE = re.compile(r"^(?:https?|mailto|ftp|tel|data|javascript):", re.IGNORECASE)

LOCALE_DIR_RE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")

METHODOLOGY_REF_RE = re.compile(
    r"\b(?:di[aá]taxis|asd[-\s]?st[ef]100|st[ef][-\s]?100|simplified\s+technical\s+english|fran[cç]ais\s+technique\s+simplifi[eé]|quadrants?)\b",
    re.IGNORECASE,
)

INTERNAL_REGISTER_FILENAMES = frozenset({"action_logbook.md", "rca_register.md"})
INTERNAL_REGISTER_REF_RE = re.compile(
    r"\b(?:"
    r"ACTION_LOGBOOK(?:\.md)?"
    r"|RCA_REGISTER(?:\.md)?"
    r"|ACT-\d+"
    r"|RCA-\d+"
    r"|IMP-\d+"
    r"|APP-\d+"
    r"|IDEA-\d+"
    r"|action\s+log(?:book)?"
    r"|rca\s+register"
    r"|registre\s+(?:des\s+)?rca"
    r"|journal\s+(?:d['’]|des\s+)actions"
    r")\b",
    re.IGNORECASE,
)

MKDOCS_ADMONITION_RE = re.compile(r"^\s*!!!\s+")
MKDOCS_COLLAPSIBLE_RE = re.compile(r"^\s*\?\?\?\+?\s+")
MKDOCS_TABBED_RE = re.compile(r'^\s*===\s+"')
MKDOCS_SNIPPET_TOKEN = "--8<--"

HOWTO_VALIDATION_RE = re.compile(
    r"\b(?:validat(?:e|es|ed|ing|ion)|verif(?:y|ies|ied|ication)|vérif(?:ier|ication)|contrôle)\b",
    re.IGNORECASE,
)
HOWTO_HEADING_CHECK_RE = re.compile(r"\bcheck\b", re.IGNORECASE)
HOWTO_ROLLBACK_RE = re.compile(
    r"\b(?:rollback|revert|backout|back-out|undo|retour\s+arrière|annulation)\b",
    re.IGNORECASE,
)
HOWTO_THEORY_HEADING_RE = re.compile(
    r"\b(?:why|architecture|theory|théorie|explication|explanation|context|contexte|background|pourquoi)\b",
    re.IGNORECASE,
)

REF_TUTORIAL_PHRASING_RE = re.compile(
    r"(?:\bin\s+this\s+tutorial\b|\blet['’]?s\b|\blet\s+us\b|\bstep\s+1\b|\bdans\s+ce\s+tutoriel\b|\bétape\s+1\b)",
    re.IGNORECASE,
)

EXPLANATION_PROCEDURAL_HEADING_RE = re.compile(
    r"\b(?:step\s+\d+|rollback|remediation|prerequisites|prérequis|étape\s+\d+|procédure)\b",
    re.IGNORECASE,
)

# Procedural writing checks for 02-how-to-guides/
ING_APPROVED = frozenset(
    {
        "mating",
        "missing",
        "remaining",
        "lighting",
        "opening",
        "routing",
        "servicing",
        "something",
        "during",
    }
)

ING_NOT_SUFFIX = frozenset(
    {
        "ring",
        "spring",
        "string",
        "king",
        "thing",
        "wing",
        "sing",
        "bring",
        "sting",
        "swing",
        "nothing",
        "anything",
        "everything",
        "something",
        "bearing",
        "ceiling",
        "morning",
        "evening",
    }
)

BANNED_MODALS = frozenset({"should", "would", "may", "might", "shall", "ought"})

NON_PARTICIPLE_ED_EN = frozenset(
    {
        "bed",
        "between",
        "bleed",
        "breed",
        "citizen",
        "creed",
        "deed",
        "even",
        "exceed",
        "feed",
        "fifteen",
        "fourteen",
        "golden",
        "greed",
        "green",
        "heed",
        "hundred",
        "linen",
        "men",
        "naked",
        "need",
        "often",
        "open",
        "proceed",
        "red",
        "reed",
        "screen",
        "seed",
        "seven",
        "seventeen",
        "shed",
        "sixteen",
        "sled",
        "speed",
        "steed",
        "succeed",
        "sudden",
        "ten",
        "then",
        "thirteen",
        "wed",
        "weed",
        "when",
        "wicked",
        "women",
        "wooden",
    }
)

# Past participles permitted after 'be' ONLY when describing a state/condition
CONDITION_ADJECTIVES = frozenset(
    {
        "absent",
        "active",
        "aligned",
        "allowed",
        "attached",
        "available",
        "based",
        "broken",
        "clean",
        "closed",
        "completed",
        "configured",
        "connected",
        "damaged",
        "dedicated",
        "defined",
        "depleted",
        "deprecated",
        "detached",
        "disabled",
        "disconnected",
        "documented",
        "dropped",
        "empty",
        "enabled",
        "encrypted",
        "established",
        "exceeded",
        "excluded",
        "exhausted",
        "finished",
        "fixed",
        "found",
        "halted",
        "inactive",
        "included",
        "installed",
        "invalid",
        "isolated",
        "known",
        "limited",
        "listed",
        "loaded",
        "locked",
        "masked",
        "missed",
        "mounted",
        "needed",
        "open",
        "paused",
        "permitted",
        "present",
        "protected",
        "reached",
        "ready",
        "recorded",
        "related",
        "removed",
        "required",
        "saturated",
        "set",
        "shown",
        "started",
        "stopped",
        "supported",
        "synced",
        "synchronized",
        "unknown",
        "unlocked",
        "unused",
        "used",
        "valid",
    }
)

CONTRACTION_RE = re.compile(
    r"\b\w+n['’]t\b|\b\w+['’](?:re|ll|ve|m|d)\b|"
    r"\b(?:it|that|there|what|let|who|here|he|she|where|when|how)['’]s\b",
    re.IGNORECASE,
)

_IRREGULAR_PARTICIPLES = (
    "been|done|made|gone|put|set|cut|kept|held|taken|given|found|left|lost|"
    "meant|sent|shown|told|built|become|begun|broken|brought|come|fallen|"
    "felt|got|gotten|grown|known|read|run|seen|spoken|thrown|worn|written|sold"
)

_PASSIVE_PARTICIPLE = (
    r"(?:[a-z]{2,}(?:ed|en)|done|made|held|kept|sent|built|found|left|lost|"
    r"shown|known|sold|told|put|set|cut|run|broken|taken|given|written|seen|worn)"
)

HAVE_PARTICIPLE_RE = re.compile(
    rf"\b(?:has|have|had)\s+(?:(?:not|never|already|always)\s+)?(?:[a-z]{{2,}}ed|{_IRREGULAR_PARTICIPLES})\b",
    re.IGNORECASE,
)

COMPLEX_PASSIVE_RE = re.compile(
    rf"\b(?:can|will|must|could|would|should|may|might|shall)\s+"
    rf"(?:not\s+)?be\s+{_PASSIVE_PARTICIPLE}\b|"
    rf"\b(?:is|are|was|were)\s+to\s+be\s+{_PASSIVE_PARTICIPLE}\b",
    re.IGNORECASE,
)

PASSIVE_BE_RE = re.compile(
    rf"\b(?:is|are|was|were|be|been|being)\s+(?:(?:not|never|already|always)\s+)?({_PASSIVE_PARTICIPLE})\b",
    re.IGNORECASE,
)

BE_ING_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|am)\s+([a-z]+ing)\b",
    re.IGNORECASE,
)

LATIN_ABBREV_RE = re.compile(
    r"(?<![A-Za-z])(?:e\.g\.|i\.e\.|etc\.)(?![A-Za-z])",
    re.IGNORECASE,
)

HTML_ENTITY_RE = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|#[0-9]+|#x[0-9A-Fa-f]+);")

_UNIT_ALT = (
    r"degrees?\s+(?:Celsius|Fahrenheit|Kelvin)"
    r"|°[CFK]|deg[CF]|°"
    r"|a\.m\.|p\.m\.|AM|PM"
    r"|kilograms?|milligrams?|kilometers?|kilometres?|millimeters?|millimetres?"
    r"|centimeters?|centimetres?|meters?|metres?|microseconds?|milliseconds?"
    r"|seconds?|minutes?|hours?|liters?|litres?|gallons?"
    r"|pounds?|ounces?|tonnes?|tons?|inches|inch|feet|foot|yards?|miles?"
    r"|degrees?|percent|ohms?|ohm|psia|psig|psi|mbar|bar|atm|kPa|MPa|GPa|hPa|Pa"
    r"|kN|Nm|N·m|N-m|lbf|VDC|VAC|kVA|VA|kWh|MWh|Wh|kW|MW|GW|mW|kV|mV|kA|mA|uA|µA"
    r"|GHz|MHz|kHz|Hz|kΩ|MΩ|Ω|Ω|mF|uF|µF|nF|pF|mH|kJ|MJ|dBA|dBm|dB"
    r"|KiB|MiB|GiB|TiB|Gbps|Mbps|kbps|bps|KB|MB|GB|TB|PB"
    r"|kg|mg|ug|µg|mm|cm|km|nm|um|µm|ft|yd|mi|mL|ml|cc|gal|rpm|RPM|mph|kph|rad"
    r"|sec|secs|min|mins|hr|hrs|ms|us|µs|ns|deg|ppm|ppb|px|pt|dpi|fps|FPS|lbs|lb|oz"
    r"|A|V|W|J|N|F|H|K|L|B|g|m|s|h|l|%"
)
_RATE_DENOM = r"(?:/(?:s|sec|second|min|minute|h|hr|hour|day|m|cm|mm|kg|L|l))?"
NUMBER_UNIT_RE = re.compile(
    rf"(?<![A-Za-z0-9_])[+-]?\d+(?:[.,:]\d+)*(?:-[+-]?\d+(?:[.,:]\d+)*)?"
    rf"\s*(?:{_UNIT_ALT}){_RATE_DENOM}(?![A-Za-z0-9_])"
)

SENT_SPLIT_RE = re.compile(
    r"(?<!No\.)(?<!e\.g\.)(?<!i\.e\.)(?<!etc\.)(?<!a\.m\.)(?<!p\.m\.)(?<=[.!?:])\s+"
    r"|(?<=(?:a\.m\.|p\.m\.|etc\.))\s+(?=[A-Z0-9])"
    r"|(?<=No\.)\s+(?=[A-Z])"
)
WORDISH_RE = re.compile(r"[A-Za-z0-9]+(?:[.'&/’-][A-Za-z0-9]+)*")


@dataclass(frozen=True)
class Finding:
    """Validation error or governance warning."""

    severity: str
    path: Path
    line: int
    message: str

    def format(self) -> str:
        """Render finding in standard CLI format."""
        loc = f"{self.path}:{self.line}" if self.line > 0 else str(self.path)
        return f"[{self.severity}] {loc}: {self.message}"


if yaml is not None:

    class _MkDocsSafeLoader(yaml.SafeLoader):
        """Safe YAML loader supporting MkDocs !!python/name: tags."""

    def _construct_python_name(
        loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node
    ) -> str:
        return tag_suffix

    _MkDocsSafeLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/name:", _construct_python_name
    )


def _load_mkdocs_yaml(path: Path) -> dict[str, Any]:
    """Load mkdocs.yml safely, resolving !!python/name: tags to their suffix strings."""
    if yaml is None:
        raise RuntimeError("PyYAML is unavailable")
    raw = path.read_text(encoding="utf-8")
    data = yaml.load(raw, Loader=_MkDocsSafeLoader)
    return data if isinstance(data, dict) else {}


def _extract_top_level_blocks(raw_text: str) -> dict[str, list[str]]:
    """Split top-level YAML sections for zero-dependency fallback checking."""
    blocks: dict[str, list[str]] = {}
    current_key: str | None = None
    for raw_line in raw_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw_line[0].isspace():
            m = re.match(r"^([A-Za-z0-9_.-]+)\s*:(.*)$", raw_line)
            if m:
                current_key = m.group(1)
                blocks.setdefault(current_key, [])
                rest = m.group(2).strip()
                if rest and rest != "|":
                    blocks[current_key].append(rest)
            else:
                current_key = None
        elif current_key is not None:
            blocks[current_key].append(raw_line)
    return blocks


def strip_inline_code(line: str) -> str:
    """Replace CommonMark inline code spans with single spaces."""
    if "`" not in line:
        return line

    out: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] != "`":
            out.append(line[i])
            i += 1
            continue

        tick_len = 0
        while i + tick_len < n and line[i + tick_len] == "`":
            tick_len += 1

        search_pos = i + tick_len
        close_pos = -1
        while search_pos < n:
            if line[search_pos] != "`":
                search_pos += 1
                continue
            run_len = 0
            while search_pos + run_len < n and line[search_pos + run_len] == "`":
                run_len += 1
            if run_len == tick_len:
                close_pos = search_pos + run_len
                break
            search_pos += run_len

        if close_pos != -1:
            out.append(" ")
            i = close_pos
        else:
            out.append(line[i : i + tick_len])
            i += tick_len

    return "".join(out)


def extract_non_code_lines(text: str) -> list[tuple[int, str]]:
    """Return 1-based (lineno, line_without_inline_code) outside fenced code blocks."""
    result: list[tuple[int, str]] = []
    fence_char: str | None = None
    fence_len = 0

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        if fence_char is not None:
            if re.match(rf"^\s*{re.escape(fence_char)}{{{fence_len},}}\s*$", raw_line):
                fence_char = None
                fence_len = 0
            continue

        fence_match = FENCE_RE.match(raw_line)
        if fence_match:
            marker = fence_match.group(1)
            fence_char = marker[0]
            fence_len = len(marker)
            continue

        result.append((lineno, strip_inline_code(raw_line)))

    return result


def check_required_structure(docs_dir: Path) -> list[Finding]:
    """Verify docs/index.md and all four section directories and index files."""
    findings: list[Finding] = []
    root_index = docs_dir / "index.md"
    if not root_index.is_file():
        findings.append(
            Finding("ERROR", root_index, 0, "Missing required documentation portal index.md.")
        )

    for quadrant in REQUIRED_QUADRANTS:
        quadrant_dir = docs_dir / quadrant
        if not quadrant_dir.is_dir():
            findings.append(
                Finding("ERROR", quadrant_dir, 0, f"Missing required section directory '{quadrant}'.")
            )
            continue
        quadrant_index = quadrant_dir / "index.md"
        if not quadrant_index.is_file():
            findings.append(
                Finding("ERROR", quadrant_index, 0, f"Missing required '{quadrant}/index.md'.")
            )

    return findings


def normalize_link_target(raw_target: str) -> str:
    """Extract file path part from a Markdown link target."""
    target = raw_target.strip()
    if not target:
        return ""
    if target.startswith("<"):
        end_idx = target.find(">")
        if end_idx != -1:
            target = target[1:end_idx].strip()
    else:
        target = target.split()[0]

    if not target or target.startswith("#"):
        return ""
    if EXTERNAL_SCHEME_RE.match(target) or target.startswith("//"):
        return ""

    target = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(target.strip())


def _resolve_link_target(md_file: Path, docs_dir: Path, target: str) -> Path:
    """Resolve a normalized Markdown link path to an absolute filesystem path."""
    if target.startswith("/"):
        return (docs_dir / target.lstrip("/")).resolve()
    return (md_file.parent / target).resolve()


def check_relative_links(
    md_file: Path,
    docs_dir: Path,
    non_code_lines: list[tuple[int, str]],
) -> list[Finding]:
    """Verify every relative Markdown link resolves to an existing file inside docs/."""
    findings: list[Finding] = []
    docs_root = docs_dir.resolve()

    for lineno, line in non_code_lines:
        for match in LINK_RE.finditer(line):
            target = normalize_link_target(match.group(1))
            if not target:
                continue

            resolved = _resolve_link_target(md_file, docs_root, target)

            try:
                resolved.relative_to(docs_root)
            except ValueError:
                findings.append(
                    Finding(
                        "ERROR",
                        md_file,
                        lineno,
                        f"Relative link escapes docs root '{match.group(1).strip()}' (resolved to {resolved}).",
                    )
                )
                continue

            target_exists = resolved.is_file() or (
                resolved.is_dir() and (resolved / "index.md").is_file()
            )
            if not target_exists:
                findings.append(
                    Finding(
                        "ERROR",
                        md_file,
                        lineno,
                        f"Broken relative link target '{match.group(1).strip()}' (resolved to {resolved}).",
                    )
                )
    return findings


def check_no_methodology_references(md_file: Path, text: str) -> list[Finding]:
    """Ensure Markdown documents contain zero banned methodology references."""
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = METHODOLOGY_REF_RE.search(line)
        if match:
            findings.append(
                Finding(
                    "ERROR",
                    md_file,
                    lineno,
                    f"Forbidden methodology reference '{match.group(0)}' is not allowed in documentation.",
                )
            )
    return findings


def check_no_internal_register_references(md_file: Path, text: str) -> list[Finding]:
    """Ensure published MkDocs pages contain zero Action Log or RCA Register references."""
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = INTERNAL_REGISTER_REF_RE.search(line)
        if match:
            findings.append(
                Finding(
                    "ERROR",
                    md_file,
                    lineno,
                    f"Forbidden internal register reference '{match.group(0)}' is not allowed in published MkDocs documentation.",
                )
            )
    return findings


def _is_long_url_exempt(line: str) -> bool:
    """Allow lines > 80 chars only when stripping one long URL/link target (> 40 chars) leaves <= 80 chars."""
    tokens: list[str] = []

    def _strip_link_target(match: re.Match[str]) -> str:
        tokens.append(match.group(2).strip())
        return f"{match.group(1)}()"

    without_md_targets = LINK_FULL_RE.sub(_strip_link_target, line)

    def _strip_bare_url(match: re.Match[str]) -> str:
        tokens.append(match.group(0))
        return ""

    stripped = BARE_URL_RE.sub(_strip_bare_url, without_md_targets)
    return len(stripped) <= 80 and sum(1 for tok in tokens if len(tok) > 40) == 1


def _count_sentences(paragraph_lines: list[str]) -> int:
    """Count sentences in a paragraph while avoiding false splits on decimals and inline code."""
    para_text = " ".join(line.strip() for line in paragraph_lines)
    cleaned = strip_inline_code(para_text)
    cleaned = LINK_FULL_RE.sub(r"\1()", cleaned)
    cleaned = ABBREV_RE.sub(lambda m: m.group(0).replace(".", ""), cleaned)
    parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(cleaned) if s.strip()]
    return len(parts)


def check_line_length_and_paragraphs(md_file: Path, text: str) -> list[Finding]:
    """Flag lines exceeding 80 chars (with single long-URL exemption) and dense paragraphs."""
    findings: list[Finding] = []
    fence_char: str | None = None
    fence_len = 0
    paragraph_lines: list[str] = []
    paragraph_start = 0

    def _flush_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_start
        if not paragraph_lines:
            return
        if len(paragraph_lines) > 4 or _count_sentences(paragraph_lines) > 3:
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    paragraph_start,
                    "Dense paragraph (wall of text): split into short paragraphs (<= 3 sentences / <= 4 lines) or use bullet points.",
                )
            )
        paragraph_lines = []
        paragraph_start = 0

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        if fence_char is not None:
            if re.match(rf"^\s*{re.escape(fence_char)}{{{fence_len},}}\s*$", raw_line):
                fence_char = None
                fence_len = 0
            continue

        fence_match = FENCE_RE.match(raw_line)
        if fence_match:
            _flush_paragraph()
            marker = fence_match.group(1)
            fence_char = marker[0]
            fence_len = len(marker)
            continue

        is_blank = not raw_line.strip()
        is_heading = bool(PARAGRAPH_HEADING_RE.match(raw_line))
        is_table = bool(PARAGRAPH_TABLE_RE.match(raw_line))
        is_hr = bool(HR_RE.match(raw_line))
        is_link_ref = bool(LINK_REF_DEF_RE.match(raw_line))
        is_list = bool(PARAGRAPH_LIST_RE.match(raw_line))
        is_blockquote = bool(BLOCKQUOTE_RE.match(raw_line))

        if not (is_heading or is_table or is_hr or is_link_ref):
            if len(raw_line) > 80 and not _is_long_url_exempt(raw_line):
                findings.append(
                    Finding(
                        "WARN",
                        md_file,
                        lineno,
                        f"Line exceeds 80 characters ({len(raw_line)} > 80).",
                    )
                )

        if is_blank or is_heading or is_list or is_blockquote or is_table or is_hr or is_link_ref:
            _flush_paragraph()
        else:
            if not paragraph_lines:
                paragraph_start = lineno
            paragraph_lines.append(raw_line)

    _flush_paragraph()
    return findings


def check_git_readability(
    md_file: Path,
    non_code_lines: list[tuple[int, str]],
) -> list[Finding]:
    """Flag MkDocs-only syntax and non-Git-native internal Markdown links."""
    findings: list[Finding] = []
    for lineno, line in non_code_lines:
        if MKDOCS_ADMONITION_RE.match(line):
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    lineno,
                    "MkDocs admonition syntax ('!!!') is not Git-native GFM; use **NOTE:**/**CAUTION:**/**WARNING:**.",
                )
            )
        if MKDOCS_COLLAPSIBLE_RE.match(line):
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    lineno,
                    "MkDocs collapsible block syntax ('???') is not Git-native GFM.",
                )
            )
        if MKDOCS_TABBED_RE.match(line):
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    lineno,
                    "MkDocs tabbed syntax ('===') is not Git-native GFM.",
                )
            )
        if MKDOCS_SNIPPET_TOKEN in line:
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    lineno,
                    "MkDocs snippet include ('--8<--') is not Git-native GFM.",
                )
            )

        for match in LINK_RE.finditer(line):
            raw_target = match.group(1).strip()
            target = normalize_link_target(raw_target)
            if not target:
                continue
            if target.startswith("/"):
                findings.append(
                    Finding(
                        "WARN",
                        md_file,
                        lineno,
                        f"Root-absolute internal link '{raw_target}' is not Git-native; use a relative .md path.",
                    )
                )
                continue

            suffix = Path(target.rstrip("/")).suffix.lower()
            if target.endswith("/") or not suffix or suffix in {".html", ".htm"}:
                findings.append(
                    Finding(
                        "WARN",
                        md_file,
                        lineno,
                        f"Internal link '{raw_target}' should target an explicit .md file for Git-native readability.",
                    )
                )
    return findings


def _iter_yaml_strings(value: Any) -> list[str]:
    """Collect all string scalars recursively from nested YAML structures."""
    items: list[str] = []
    if isinstance(value, str):
        items.append(value)
    elif isinstance(value, list):
        for entry in value:
            items.extend(_iter_yaml_strings(entry))
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                items.append(k)
            items.extend(_iter_yaml_strings(v))
    return items


def _check_mkdocs_config_fallback(mkdocs_path: Path, raw_text: str) -> list[Finding]:
    """Fallback mkdocs.yml validator when PyYAML is unavailable in minimal chroot."""
    findings: list[Finding] = []
    blocks = _extract_top_level_blocks(raw_text)

    for key in ("site_name", "site_description", "nav"):
        block_text = "\n".join(blocks.get(key, []))
        m_ref = METHODOLOGY_REF_RE.search(block_text)
        if m_ref:
            findings.append(
                Finding(
                    "ERROR",
                    mkdocs_path,
                    0,
                    f"mkdocs.yml '{key}' contains forbidden methodology reference '{m_ref.group(0)}'.",
                )
            )
        r_ref = INTERNAL_REGISTER_REF_RE.search(block_text)
        if r_ref:
            findings.append(
                Finding(
                    "ERROR",
                    mkdocs_path,
                    0,
                    f"mkdocs.yml '{key}' contains forbidden internal register reference '{r_ref.group(0)}'.",
                )
            )

    exclude_text = "\n".join(blocks.get("exclude_docs", []))
    if "ACTION_LOGBOOK.md" not in exclude_text or "RCA_REGISTER.md" not in exclude_text:
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must exclude ACTION_LOGBOOK.md and RCA_REGISTER.md via exclude_docs.",
            )
        )

    ext_text = "\n".join(blocks.get("markdown_extensions", []))
    has_mermaid = (
        "pymdownx.superfences" in ext_text
        and "custom_fences:" in ext_text
        and re.search(r"\bname:\s*mermaid\b", ext_text) is not None
        and re.search(r"\bclass:\s*mermaid\b", ext_text) is not None
        and "fence_code_format" in ext_text
    )
    if not has_mermaid:
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must configure pymdownx.superfences custom_fences for Mermaid (name: mermaid, class: mermaid, format: !!python/name:pymdownx.superfences.fence_code_format).",
            )
        )

    for banned_ext in ("pymdownx.snippets", "pymdownx.tabbed"):
        if re.search(rf"^\s*-\s*{re.escape(banned_ext)}(?:\s*:|\s*$)", ext_text, re.M):
            findings.append(
                Finding(
                    "ERROR",
                    mkdocs_path,
                    0,
                    f"mkdocs.yml must not enable '{banned_ext}' (breaks Git-native GFM readability).",
                )
            )

    extra_text = "\n".join(blocks.get("extra", []))
    if not re.search(r"\bprovider:\s*mike\b", extra_text):
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must configure extra.version.provider: mike.",
            )
        )
    if not re.search(r"\balias:\s*true\b", extra_text):
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must configure extra.version.alias: true.",
            )
        )

    return findings


def check_mkdocs_config(
    mkdocs_path: Path,
    expected_locales: list[str] | None = None,
) -> list[Finding]:
    """Validate mkdocs.yml against methodology-free, register-free, Mermaid, mike, and GFM contracts."""
    if not mkdocs_path.is_file():
        return [
            Finding("ERROR", mkdocs_path, 0, f"MkDocs config file not found: {mkdocs_path}")
        ]

    raw_text = mkdocs_path.read_text(encoding="utf-8")
    if yaml is None:
        return _check_mkdocs_config_fallback(mkdocs_path, raw_text)

    try:
        cfg = _load_mkdocs_yaml(mkdocs_path)
    except Exception as exc:  # noqa: BLE001
        return [
            Finding("ERROR", mkdocs_path, 0, f"Failed to parse MkDocs YAML: {exc}")
        ]

    findings: list[Finding] = []

    # (a) Zero banned methodology or internal register references in metadata and nav.
    for key in ("site_name", "site_description"):
        val = cfg.get(key)
        if isinstance(val, str):
            match = METHODOLOGY_REF_RE.search(val)
            if match:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        f"mkdocs.yml '{key}' contains forbidden methodology reference '{match.group(0)}'.",
                    )
                )
            reg_match = INTERNAL_REGISTER_REF_RE.search(val)
            if reg_match:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        f"mkdocs.yml '{key}' contains forbidden internal register reference '{reg_match.group(0)}'.",
                    )
                )

    nav_cfg = cfg.get("nav")
    if nav_cfg is not None:
        for nav_str in _iter_yaml_strings(nav_cfg):
            meth_match = METHODOLOGY_REF_RE.search(nav_str)
            if meth_match:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        f"mkdocs.yml 'nav' contains forbidden methodology reference '{meth_match.group(0)}'.",
                    )
                )
            reg_match = INTERNAL_REGISTER_REF_RE.search(nav_str)
            if reg_match:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        f"mkdocs.yml 'nav' contains forbidden internal register reference '{reg_match.group(0)}'.",
                    )
                )

    exclude_raw = cfg.get("exclude_docs")
    if isinstance(exclude_raw, str):
        exclude_text = exclude_raw
    elif isinstance(exclude_raw, list):
        exclude_text = "\n".join(str(item) for item in exclude_raw)
    else:
        exclude_text = ""

    if "ACTION_LOGBOOK.md" not in exclude_text or "RCA_REGISTER.md" not in exclude_text:
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must exclude ACTION_LOGBOOK.md and RCA_REGISTER.md via exclude_docs.",
            )
        )

    # (b) Mermaid custom_fences and ban on non-GFM extensions (pymdownx.snippets, pymdownx.tabbed).
    extensions = cfg.get("markdown_extensions")
    has_mermaid_fence = False
    banned_extensions = {"pymdownx.snippets", "pymdownx.tabbed"}
    if isinstance(extensions, list):
        for ext in extensions:
            ext_names: list[str] = []
            if isinstance(ext, str):
                ext_names.append(ext)
            elif isinstance(ext, dict):
                ext_names.extend(str(k) for k in ext.keys())

            for ext_name in ext_names:
                if ext_name in banned_extensions:
                    findings.append(
                        Finding(
                            "ERROR",
                            mkdocs_path,
                            0,
                            f"mkdocs.yml must not enable '{ext_name}' (breaks Git-native GFM readability).",
                        )
                    )

            if not (isinstance(ext, dict) and "pymdownx.superfences" in ext):
                continue
            superfences_cfg = ext.get("pymdownx.superfences")
            if not isinstance(superfences_cfg, dict):
                continue
            custom_fences = superfences_cfg.get("custom_fences")
            if not isinstance(custom_fences, list):
                continue
            for fence in custom_fences:
                if not isinstance(fence, dict):
                    continue
                if (
                    fence.get("name") == "mermaid"
                    and fence.get("class") == "mermaid"
                    and "fence_code_format" in str(fence.get("format", ""))
                ):
                    has_mermaid_fence = True
                    break

    if not has_mermaid_fence:
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must configure pymdownx.superfences custom_fences for Mermaid (name: mermaid, class: mermaid, format: !!python/name:pymdownx.superfences.fence_code_format).",
            )
        )

    # (c) Version navigator provider must be mike with alias: true.
    extra = cfg.get("extra")
    version_cfg = extra.get("version") if isinstance(extra, dict) else None
    provider = version_cfg.get("provider") if isinstance(version_cfg, dict) else None
    alias_val = version_cfg.get("alias") if isinstance(version_cfg, dict) else None
    if provider != "mike":
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must configure extra.version.provider: mike.",
            )
        )
    if alias_val is not True:
        findings.append(
            Finding(
                "ERROR",
                mkdocs_path,
                0,
                "mkdocs.yml must configure extra.version.alias: true.",
            )
        )

    # (d) Multilingual i18n plugin contract when expected_locales is provided.
    if expected_locales:
        plugins = cfg.get("plugins")
        i18n_cfg: dict[str, Any] | None = None
        if isinstance(plugins, list):
            for plugin in plugins:
                if isinstance(plugin, dict) and isinstance(plugin.get("i18n"), dict):
                    i18n_cfg = plugin["i18n"]
                    break
        elif isinstance(plugins, dict) and isinstance(plugins.get("i18n"), dict):
            i18n_cfg = plugins["i18n"]

        if i18n_cfg is None:
            findings.append(
                Finding(
                    "ERROR",
                    mkdocs_path,
                    0,
                    "Multilingual mkdocs.yml must configure the i18n plugin.",
                )
            )
        else:
            if i18n_cfg.get("docs_structure") != "folder":
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        "mkdocs.yml i18n plugin must set docs_structure: folder.",
                    )
                )
            if i18n_cfg.get("fallback_to_default") is not False:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        "mkdocs.yml i18n plugin must set fallback_to_default: false.",
                    )
                )
            if i18n_cfg.get("reconfigure_material") is not True:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        "mkdocs.yml i18n plugin must set reconfigure_material: true.",
                    )
                )

            configured_locales: set[str] = set()
            languages = i18n_cfg.get("languages")
            if isinstance(languages, list):
                for entry in languages:
                    if isinstance(entry, dict) and entry.get("locale"):
                        configured_locales.add(str(entry["locale"]))
            elif isinstance(languages, dict):
                configured_locales.update(str(k) for k in languages.keys())

            missing_locales = [loc for loc in expected_locales if loc not in configured_locales]
            if missing_locales:
                findings.append(
                    Finding(
                        "ERROR",
                        mkdocs_path,
                        0,
                        f"mkdocs.yml i18n.languages is missing locale(s): {', '.join(missing_locales)}.",
                    )
                )

    return findings


def detect_locale_dirs(docs_dir: Path) -> list[Path]:
    """Detect isolated locale subdirectories under docs_dir for multilingual trees."""
    if (docs_dir / "index.md").is_file() or not docs_dir.is_dir():
        return []
    candidates = sorted(
        child
        for child in docs_dir.iterdir()
        if child.is_dir() and LOCALE_DIR_RE.match(child.name)
    )
    if not candidates:
        return []
    if len(candidates) >= 2 or any((c / "01-tutorials").is_dir() for c in candidates):
        return candidates
    return []


def check_cross_locale_links(
    md_file: Path,
    current_locale: Path,
    locale_dirs: list[Path],
    non_code_lines: list[tuple[int, str]],
) -> list[Finding]:
    """Ensure relative links inside one locale tree never resolve inside another locale tree."""
    findings: list[Finding] = []
    current_resolved = current_locale.resolve()
    other_locales = [ld.resolve() for ld in locale_dirs if ld.resolve() != current_resolved]
    if not other_locales:
        return findings

    for lineno, line in non_code_lines:
        for match in LINK_RE.finditer(line):
            target = normalize_link_target(match.group(1))
            if not target:
                continue
            resolved = _resolve_link_target(md_file, current_locale, target)
            for other_locale in other_locales:
                if resolved == other_locale or resolved.is_relative_to(other_locale):
                    findings.append(
                        Finding(
                            "ERROR",
                            md_file,
                            lineno,
                            f"Cross-locale link '{match.group(1).strip()}' crosses from '{current_locale.name}/' into '{other_locale.name}/'.",
                        )
                    )
                    break
    return findings


def check_locale_parity(locale_dirs: list[Path]) -> list[Finding]:
    """Warn when a page exists in one locale directory but is missing in another."""
    if len(locale_dirs) < 2:
        return []

    structural_indexes = {"index.md", *(f"{section}/index.md" for section in REQUIRED_QUADRANTS)}
    locale_files: dict[Path, set[str]] = {}
    all_paths: set[str] = set()
    for locale_dir in locale_dirs:
        rel_set = {
            path.relative_to(locale_dir).as_posix()
            for path in locale_dir.rglob("*.md")
            if path.name.lower() not in INTERNAL_REGISTER_FILENAMES
        }
        locale_files[locale_dir] = rel_set
        all_paths.update(rel_set)

    findings: list[Finding] = []
    for locale_dir in locale_dirs:
        present = locale_files[locale_dir]
        for rel_path in sorted(all_paths):
            if rel_path in structural_indexes:
                continue
            if rel_path not in present:
                findings.append(
                    Finding(
                        "WARN",
                        locale_dir / rel_path,
                        0,
                        f"Locale parity mismatch: '{rel_path}' exists in another locale but is missing in '{locale_dir.name}/'.",
                    )
                )
    return findings


def check_quadrant_governance(
    md_file: Path,
    docs_dir: Path,
    non_code_lines: list[tuple[int, str]],
) -> list[Finding]:
    """Check genre separation heuristics on non-index section pages."""
    if md_file.name.lower() == "index.md":
        return []

    rel_parts = md_file.relative_to(docs_dir).parts
    if len(rel_parts) < 2:
        return []

    quadrant = rel_parts[0]
    findings: list[Finding] = []
    headings: list[tuple[int, str]] = []
    for lineno, line in non_code_lines:
        h_match = HEADING_RE.match(line)
        if h_match:
            headings.append((lineno, h_match.group(1)))

    full_text = "\n".join(line for _, line in non_code_lines)

    if quadrant == "02-how-to-guides":
        has_validation = bool(HOWTO_VALIDATION_RE.search(full_text)) or any(
            HOWTO_HEADING_CHECK_RE.search(heading) for _, heading in headings
        )
        if not has_validation:
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    0,
                    "How-To / Runbook is missing a verification or validation heading/keyword.",
                )
            )
        if not HOWTO_ROLLBACK_RE.search(full_text):
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    0,
                    "How-To / Runbook is missing a rollback or revert heading/keyword.",
                )
            )
        for lineno, heading in headings:
            if HOWTO_THEORY_HEADING_RE.search(heading):
                findings.append(
                    Finding(
                        "WARN",
                        md_file,
                        lineno,
                        f"Theoretical heading '## {heading}' belongs in 04-explanation/, not 02-how-to-guides/.",
                    )
                )

    elif quadrant == "03-reference":
        has_table = any(TABLE_ROW_RE.match(line) for _, line in non_code_lines)
        has_list = any(LIST_ITEM_RE.match(line) for _, line in non_code_lines)
        if not (has_table or has_list):
            findings.append(
                Finding(
                    "WARN",
                    md_file,
                    0,
                    "Reference document lacks a structured Markdown table or structured list.",
                )
            )
        for lineno, line in non_code_lines:
            match = REF_TUTORIAL_PHRASING_RE.search(line)
            if match:
                findings.append(
                    Finding(
                        "WARN",
                        md_file,
                        lineno,
                        f"Tutorial phrasing '{match.group(0)}' does not belong in 03-reference/.",
                    )
                )

    elif quadrant == "04-explanation":
        for lineno, heading in headings:
            if EXPLANATION_PROCEDURAL_HEADING_RE.search(heading):
                findings.append(
                    Finding(
                        "WARN",
                        md_file,
                        lineno,
                        f"Procedural heading '## {heading}' belongs in 02-how-to-guides/, not 04-explanation/.",
                    )
                )

    return findings


def _strip_ste_noise(text: str) -> str:
    """Mask non-prose Markdown constructs prior to procedural prose analysis."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\A---\n.*?\n---(?:\n|\Z)", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.DOTALL)
    text = re.sub(r"``[^`\n]+``|`[^`\n]+`", " CODE ", text)
    text = re.sub(r"!\[([^\]]*)\]\((?:[^()]|\([^)]*\))*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\((?:[^()]|\([^)]*\))*\)", r"\1", text)
    text = re.sub(r"https?://\S+?(?=[.,;:!?)]*(?:\s|$))", " URL ", text)
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”', " QUOTED ", text)
    return text


def _count_ste_words(sentence: str) -> int:
    """Count words in a procedural sentence."""
    s = sentence
    for _ in range(3):
        updated = re.sub(r"\([^()]*\)", " PAREN ", s)
        if updated == s:
            break
        s = updated
    s = NUMBER_UNIT_RE.sub(" NUMUNIT ", s)
    s = re.sub(r"\*\*|__|#+|\*|(?<!\w)_|_(?!\w)", " ", s)
    return len(WORDISH_RE.findall(s))


def _iter_sentences(block: str) -> list[str]:
    """Split block into non-empty sentences."""
    sents: list[str] = []
    for part in SENT_SPLIT_RE.split(block):
        part = part.strip()
        if part and WORDISH_RE.search(part):
            sents.append(part)
    return sents


def _is_note_prefix(text: str) -> bool:
    """Return True when block begins with a descriptive NOTE marker."""
    cleaned = re.sub(r"^[\s>*#_-]+", "", text).strip()
    return bool(re.match(r"^(?:\*\*)?NOTE(?:\*\*)?\s*:", cleaned, re.IGNORECASE))


def _check_ste_sentence(
    sent: str,
    md_file: Path,
    lineno: int,
    is_descriptive: bool,
    findings: list[Finding],
) -> None:
    """Validate one sentence against procedural writing constraints."""
    max_words = 25 if is_descriptive else 20
    word_count = _count_ste_words(sent)
    head = sent if len(sent) <= 60 else sent[:57] + "..."
    if word_count > max_words:
        kind = "Descriptive/NOTE" if is_descriptive else "Procedural"
        findings.append(
            Finding(
                "ERROR",
                md_file,
                lineno,
                f"STE Rule 5.1/5.5: {kind} sentence has {word_count} words (max {max_words}): \"{head}\".",
            )
        )

    sent_no_entities = HTML_ENTITY_RE.sub(" ", sent)
    if ";" in sent_no_entities:
        findings.append(
            Finding("ERROR", md_file, lineno, f'STE Rule 8.1: semicolon found in "{head}".')
        )

    clean = re.sub(r"\*\*|__|(?<!\w)_|_(?!\w)|\*", "", sent)

    lat_match = LATIN_ABBREV_RE.search(clean)
    if lat_match:
        findings.append(
            Finding(
                "ERROR",
                md_file,
                lineno,
                f'STE GR-6: disallowed Latin abbreviation "{lat_match.group(0)}".',
            )
        )

    contr_match = CONTRACTION_RE.search(clean)
    if contr_match:
        findings.append(
            Finding(
                "ERROR",
                md_file,
                lineno,
                f'STE Rule 4.2: disallowed contraction "{contr_match.group(0)}".',
            )
        )

    be_ing_match = BE_ING_RE.search(clean)
    if be_ing_match:
        tail = be_ing_match.group(1).lower()
        if tail not in ING_APPROVED and tail not in ING_NOT_SUFFIX:
            findings.append(
                Finding(
                    "ERROR",
                    md_file,
                    lineno,
                    f'STE Rule 3.5: progressive form "{be_ing_match.group(0)}".',
                )
            )

    if not is_descriptive:
        have_match = HAVE_PARTICIPLE_RE.search(clean)
        if have_match and have_match.group(0).split()[-1].lower() not in NON_PARTICIPLE_ED_EN:
            findings.append(
                Finding(
                    "ERROR",
                    md_file,
                    lineno,
                    f'STE Rule 3.4: compound tense "{have_match.group(0)}"; use simple past.',
                )
            )

        comp_match = COMPLEX_PASSIVE_RE.search(clean)
        if comp_match and comp_match.group(0).split()[-1].lower() not in NON_PARTICIPLE_ED_EN:
            findings.append(
                Finding(
                    "ERROR",
                    md_file,
                    lineno,
                    f'STE Rule 3.4/3.6: passive construction "{comp_match.group(0)}".',
                )
            )

        for pass_match in PASSIVE_BE_RE.finditer(clean):
            participle = pass_match.group(1).lower()
            if participle in NON_PARTICIPLE_ED_EN:
                continue
            trailing = clean[pass_match.end() :].lstrip()
            is_by_agent = trailing.lower().startswith("by ")
            if is_by_agent or participle not in CONDITION_ADJECTIVES:
                findings.append(
                    Finding(
                        "ERROR",
                        md_file,
                        lineno,
                        f'STE Rule 3.6: passive form "{pass_match.group(0)}"; use active voice.',
                    )
                )

    for token in re.findall(r"[A-Za-z0-9_'-]+", clean):
        if "_" in token or any(ch.isdigit() for ch in token) or token.isupper():
            continue
        for word in re.findall(r"[A-Za-z]+", token):
            lw = word.lower()
            if lw in BANNED_MODALS:
                findings.append(
                    Finding(
                        "ERROR",
                        md_file,
                        lineno,
                        f'STE Rule 3.2: weak modal "{word}" is disallowed.',
                    )
                )
            elif lw.endswith("ing") and len(lw) > 4 and not word.isupper():
                if lw not in ING_APPROVED and lw not in ING_NOT_SUFFIX:
                    findings.append(
                        Finding(
                            "ERROR",
                            md_file,
                            lineno,
                            f'STE Rule 3.5: non-approved -ing form "{word}".',
                        )
                    )


def check_ste_procedural(md_file: Path, raw_text: str) -> list[Finding]:
    """Validate non-index files under 02-how-to-guides/ against procedural rules."""
    findings: list[Finding] = []
    stripped = _strip_ste_noise(raw_text)

    # Filter out headings, table rows, horizontal rules, and admonition marker lines
    filtered_lines: list[tuple[int, str, bool]] = []
    admonition_note = False
    for lineno, line in enumerate(stripped.splitlines(), start=1):
        s = line.strip()
        if not s:
            admonition_note = False
            filtered_lines.append((lineno, "", False))
            continue

        adm = ADMONITION_START_RE.match(s)
        if adm:
            admonition_note = adm.group(1).lower() == "note"
            continue

        if re.match(r"^(?:#.*|\|.*|---+|\*\*\*+|___+|===+)$", s):
            continue

        # Normalize blockquote prefix while tracking GitHub [!NOTE] callouts
        is_quote = s.startswith(">")
        if is_quote:
            s = re.sub(r"^>\s*", "", s)
            if re.match(r"^\[!NOTE\]$", s, re.IGNORECASE):
                admonition_note = True
                continue
            if re.match(r"^\[!(?:CAUTION|WARNING|IMPORTANT|TIP)\]$", s, re.IGNORECASE):
                admonition_note = False
                continue

        is_desc = admonition_note or _is_note_prefix(s)
        if re.match(r"^(?:\*\*)?(?:CAUTION|WARNING)(?:\*\*)?\s*:", s, re.IGNORECASE):
            is_desc = False
        filtered_lines.append((lineno, s, is_desc))

    # Group into blank-line-separated paragraphs
    paragraphs: list[list[tuple[int, str, bool]]] = []
    cur: list[tuple[int, str, bool]] = []
    for item in filtered_lines:
        if item[1] == "":
            if cur:
                paragraphs.append(cur)
                cur = []
        else:
            cur.append(item)
    if cur:
        paragraphs.append(cur)

    bullet_re = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
    for par_lines in paragraphs:
        items: list[tuple[int, str, bool]] = []
        prose: list[tuple[int, str, bool]] = []
        for lineno, line, is_desc in par_lines:
            if bullet_re.match(line):
                items.append((lineno, bullet_re.sub("", line, count=1), is_desc))
            elif items and not prose:
                prev_ln, prev_txt, prev_desc = items[-1]
                items[-1] = (prev_ln, f"{prev_txt} {line}", prev_desc or is_desc)
            else:
                prose.append((lineno, line, is_desc))

        for lineno, item_text, is_desc in items:
            item_desc = is_desc or _is_note_prefix(item_text)
            for sent in _iter_sentences(item_text):
                _check_ste_sentence(sent, md_file, lineno, item_desc, findings)

        if prose:
            first_lineno = prose[0][0]
            prose_text = " ".join(txt for _, txt, _ in prose)
            prose_desc = any(desc for _, _, desc in prose) or _is_note_prefix(prose_text)
            sents = _iter_sentences(prose_text)
            if len(sents) > 6:
                findings.append(
                    Finding(
                        "ERROR",
                        md_file,
                        first_lineno,
                        f"STE Rule 6.6: paragraph has {len(sents)} sentences (max 6).",
                    )
                )
            for sent in sents:
                _check_ste_sentence(sent, md_file, first_lineno, prose_desc, findings)

    return findings


def _validate_markdown_file(
    md_file: Path,
    base_dir: Path,
    locale_dirs: list[Path] | None = None,
) -> list[Finding]:
    """Run all per-file validation checks on a single Markdown file."""
    text = md_file.read_text(encoding="utf-8")
    non_code_lines = extract_non_code_lines(text)
    file_findings: list[Finding] = []
    file_findings.extend(check_relative_links(md_file, base_dir, non_code_lines))
    if locale_dirs:
        file_findings.extend(
            check_cross_locale_links(md_file, base_dir, locale_dirs, non_code_lines)
        )
    file_findings.extend(check_quadrant_governance(md_file, base_dir, non_code_lines))
    file_findings.extend(check_no_methodology_references(md_file, text))
    file_findings.extend(check_no_internal_register_references(md_file, text))
    file_findings.extend(check_line_length_and_paragraphs(md_file, text))
    file_findings.extend(check_git_readability(md_file, non_code_lines))

    rel_parts = md_file.relative_to(base_dir).parts
    if (
        len(rel_parts) >= 2
        and rel_parts[0] == "02-how-to-guides"
        and md_file.name.lower() != "index.md"
    ):
        file_findings.extend(check_ste_procedural(md_file, text))

    return file_findings


def validate_docs(
    docs_dir: Path,
    strict: bool = False,
    mkdocs_config: Path | None = None,
) -> tuple[list[Finding], int]:
    """Run all structure, link, governance, readability, MkDocs config, and procedural checks."""
    findings: list[Finding] = []
    locale_dirs = detect_locale_dirs(docs_dir)
    expected_locales = [ld.name for ld in locale_dirs] if locale_dirs else None
    md_files = sorted(
        path
        for path in docs_dir.rglob("*.md")
        if path.name.lower() not in INTERNAL_REGISTER_FILENAMES
    )

    if locale_dirs:
        locale_map = {ld.resolve(): ld for ld in locale_dirs}
        for locale_dir in locale_dirs:
            findings.extend(check_required_structure(locale_dir))

        for md_file in md_files:
            resolved_md = md_file.resolve()
            owning_locale = next(
                (ld for ld_res, ld in locale_map.items() if resolved_md.is_relative_to(ld_res)),
                None,
            )
            base_dir = owning_locale if owning_locale is not None else docs_dir
            findings.extend(
                _validate_markdown_file(
                    md_file,
                    base_dir,
                    locale_dirs if owning_locale is not None else None,
                )
            )

        findings.extend(check_locale_parity(locale_dirs))
    else:
        findings.extend(check_required_structure(docs_dir))
        for md_file in md_files:
            findings.extend(_validate_markdown_file(md_file, docs_dir))

    target_mkdocs = mkdocs_config
    if target_mkdocs is None:
        candidate_mkdocs = docs_dir.parent / "mkdocs.yml"
        if candidate_mkdocs.is_file():
            target_mkdocs = candidate_mkdocs
    if target_mkdocs is not None:
        findings.extend(
            check_mkdocs_config(target_mkdocs, expected_locales=expected_locales)
        )

    if strict:
        findings = [
            Finding("ERROR", f.path, f.line, f.message) if f.severity == "WARN" else f
            for f in findings
        ]

    return findings, len(md_files)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Validate 4-section docs structure, links, governance, MkDocs config, and procedural rules."
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="Path to docs/ directory.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat governance and readability warnings as errors.",
    )
    parser.add_argument(
        "--mkdocs-config",
        type=Path,
        default=None,
        help="Path to mkdocs.yml to validate (auto-detected at <docs_dir>/../mkdocs.yml if omitted).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    if (
        getattr(sys.stdout, "encoding", None)
        and sys.stdout.encoding.lower() not in ("utf-8", "utf8")
        and hasattr(sys.stdout, "reconfigure")
    ):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)
    docs_dir = args.docs_dir.resolve()
    if not docs_dir.is_dir():
        print(f"[ERROR] Documentation directory does not exist: {docs_dir}", file=sys.stderr)
        return 1

    findings, file_count = validate_docs(
        docs_dir=docs_dir,
        strict=args.strict,
        mkdocs_config=args.mkdocs_config,
    )
    for finding in findings:
        print(finding.format())

    error_count = sum(1 for item in findings if item.severity == "ERROR")
    warn_count = sum(1 for item in findings if item.severity == "WARN")
    print(
        f"Summary: {error_count} error(s), {warn_count} warning(s) across {file_count} markdown file(s)."
    )
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
