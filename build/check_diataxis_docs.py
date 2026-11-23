#!/usr/bin/env python3
# ===========================================================================
# Script:      build/check_diataxis_docs.py
# Description: Zero-dependency validator for Diataxis documentation layout,
#              internal relative links, quadrant governance heuristics, and
#              ASD-STE100 Issue 9 procedural rules in 02-how-to-guides/.
# Author:      Jean-Marie Renouard / Antigravity
# Usage:       python3 build/check_diataxis_docs.py docs [--strict]
# ===========================================================================

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

REQUIRED_QUADRANTS = (
    "01-tutorials",
    "02-how-to-guides",
    "03-reference",
    "04-explanation",
)

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S+")
ADMONITION_START_RE = re.compile(r"^(?:!!!|\?\?\?\+?)\s+([A-Za-z0-9_-]+)(?:\s+.*)?$")
EXTERNAL_SCHEME_RE = re.compile(r"^(?:https?|mailto|ftp|tel|data|javascript):", re.IGNORECASE)

HOWTO_VALIDATION_RE = re.compile(
    r"\b(?:validat(?:e|es|ed|ing|ion)|verif(?:y|ies|ied|ication)|check)\b",
    re.IGNORECASE,
)
HOWTO_ROLLBACK_RE = re.compile(
    r"\b(?:rollback|revert|backout|back-out|undo)\b",
    re.IGNORECASE,
)
HOWTO_THEORY_HEADING_RE = re.compile(
    r"\b(?:why|architecture|theory|explanation|context|background)\b",
    re.IGNORECASE,
)

REF_TUTORIAL_PHRASING_RE = re.compile(
    r"(?:\bin\s+this\s+tutorial\b|\blet['’]?s\b|\blet\s+us\b|\bstep\s+1\b)",
    re.IGNORECASE,
)

EXPLANATION_PROCEDURAL_HEADING_RE = re.compile(
    r"\b(?:step\s+\d+|rollback|remediation|prerequisites|procedure)\b",
    re.IGNORECASE,
)

# ASD-STE100 Issue 9 procedural checks
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

# STE Rule 3.6 permits past participles after 'be' ONLY when describing a state/condition
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
    """Verify docs/index.md and all four Diataxis quadrant directories and index files."""
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
                Finding("ERROR", quadrant_dir, 0, f"Missing required quadrant directory '{quadrant}'.")
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

            if target.startswith("/"):
                resolved = (docs_root / target.lstrip("/")).resolve()
            else:
                resolved = (md_file.parent / target).resolve()

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


def check_quadrant_governance(
    md_file: Path,
    docs_dir: Path,
    non_code_lines: list[tuple[int, str]],
) -> list[Finding]:
    """Check Diataxis genre separation heuristics on non-index quadrant pages."""
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
        if not HOWTO_VALIDATION_RE.search(full_text):
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
    """Mask non-prose Markdown constructs prior to ASD-STE100 analysis."""
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
    """Count words using ASD-STE100 Issue 9 Section 8 rules."""
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
    """Validate one sentence against ASD-STE100 Issue 9 procedural constraints."""
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
    """Validate non-index files under 02-how-to-guides/ against ASD-STE100 Issue 9."""
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


def validate_docs(docs_dir: Path, strict: bool = False) -> tuple[list[Finding], int]:
    """Run all Diataxis structure, link, governance, and STE checks across docs_dir."""
    findings: list[Finding] = []
    findings.extend(check_required_structure(docs_dir))

    md_files = sorted(docs_dir.rglob("*.md"))
    for md_file in md_files:
        raw_text = md_file.read_text(encoding="utf-8")
        non_code_lines = extract_non_code_lines(raw_text)
        findings.extend(check_relative_links(md_file, docs_dir, non_code_lines))
        findings.extend(check_quadrant_governance(md_file, docs_dir, non_code_lines))

        rel_parts = md_file.relative_to(docs_dir).parts
        if (
            len(rel_parts) >= 2
            and rel_parts[0] == "02-how-to-guides"
            and md_file.name.lower() != "index.md"
        ):
            findings.extend(check_ste_procedural(md_file, raw_text))

    if strict:
        findings = [
            Finding("ERROR", f.path, f.line, f.message) if f.severity == "WARN" else f
            for f in findings
        ]

    return findings, len(md_files)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Validate Diataxis docs structure, relative links, governance, and STE compliance."
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="Path to docs/ directory.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat governance warnings as errors.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    docs_dir = args.docs_dir.resolve()
    if not docs_dir.is_dir():
        print(f"[ERROR] Documentation directory does not exist: {docs_dir}", file=sys.stderr)
        return 1

    findings, file_count = validate_docs(docs_dir=docs_dir, strict=args.strict)
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
