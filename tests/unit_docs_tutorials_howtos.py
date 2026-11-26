#!/usr/bin/env python3
"""Executable validation suite for MySQLTuner tutorials, STE how-tos, diagrams, math, and i18n."""

from __future__ import annotations

import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - standard test images include PyYAML; fallback below if absent
    yaml = None

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

EXPECTED_MCP_TOOLS = {
    "get_latest_audit",
    "run_audit",
    "analyze_buffer_pool",
    "diagnose_replication_lag",
    "detect_fragmented_tables",
    "apply_recommendation",
    "rollback_recommendation",
}

EXPECTED_MCP_RESOURCES = {
    "mysqltuner://reports/latest.json",
    "mysqltuner://reports/latest.html",
}

MERMAID_HEADER_PATTERNS = (
    re.compile(r"^\s*flowchart(?:-elk)?(?:\s+(?:TD|TB|LR|RL|BT))?\s*$"),
    re.compile(r"^\s*flowchart(?:-elk)?\s+(?:TD|TB|LR|RL|BT)\b"),
    re.compile(r"^\s*graph\s+(?:TD|TB|LR|RL|BT)\b"),
    re.compile(r"^\s*sequenceDiagram\b"),
    re.compile(r"^\s*stateDiagram(?:-v2)?\b"),
    re.compile(r"^\s*classDiagram\b"),
    re.compile(r"^\s*erDiagram\b"),
    re.compile(r"^\s*gantt\s*$"),
    re.compile(r"^\s*pie(?:\s+showData)?(?:\s+title\s+\S.*)?\s*$"),
    re.compile(r"^\s*gitGraph(?:\s+(?:LR|TB|BT))?\s*:?\s*$"),
    re.compile(r"^\s*mindmap\s*$"),
    re.compile(r"^\s*timeline\s*$"),
    re.compile(r"^\s*xychart-beta\b"),
)

BOX_CORNER_RE = re.compile(r"[┌┐┘╔╗╚╝]")
ASCII_BOX_EDGE_RE = re.compile(r"\+[-=]{2,}\+")
TREE_BRANCH_RE = re.compile(r"[├└]─")
UNICODE_ARROW_RE = re.compile(r"─+>|▼|▲")
ASCII_FLOW_TOKENS = ("-->", "<--", "==>")
TABLE_RULE_RE = re.compile(r"^[+┌├└╠╞╚][─━═\-=+:┬┼┴╦╬╩]+[+┐┤┘╗╣╝]$")
MULTI_COL_RULE_RE = re.compile(r"(?:[┬┼┴╦╬╩]|^\+[^+]*\+[^+]*\+)")
CLI_TABLE_FOOTER_RE = re.compile(
    r"^(?:\(\d+\s+rows?\)|\d+\s+rows?\s+in\s+set\b.*|Empty set\b.*)$",
    re.IGNORECASE,
)

FR_PATH_RE = re.compile(
    r"(?:^|/)(?:fr|01-tutoriels|02-guides-pratiques|03-reference-fr|04-explications)(?:/|$)|"
    r"(?:_fr|-fr|\.fr)\.(?:md|html)$",
    re.IGNORECASE,
)


def _perl_cmd(*args: str) -> tuple[list[str], Path | None]:
    """Build Perl invocation supporting native Linux/macOS and Windows WSL."""
    perl_bin = shutil.which("perl")
    if perl_bin:
        return [perl_bin, *args], REPO_ROOT
    if os.name == "nt" and shutil.which("wsl"):
        wsl_root = subprocess.check_output(
            ["wsl", "wslpath", "-a", REPO_ROOT.as_posix()],
            text=True,
        ).strip()
        cmd_str = " ".join(f"'{a}'" for a in args)
        return ["wsl", "bash", "-lc", f"cd '{wsl_root}' && perl {cmd_str}"], None
    raise RuntimeError("Perl interpreter is unavailable in PATH or WSL")


def _parse_fenced_blocks(lines: list[str]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    in_fence = False
    fchar = ""
    flen = 0
    open_line = 0
    open_indent = ""
    open_lang = ""
    body: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if not in_fence:
            m = re.match(r"^([ \t]*)(`{3,}|~{3,})(.*)$", line)
            if not m:
                continue
            indent, fence, info = m.groups()
            if fence[0] == "`" and "`" in info:
                continue
            in_fence = True
            fchar = fence[0]
            flen = len(fence)
            open_line = idx
            open_indent = indent
            stripped = info.strip()
            open_lang = stripped.split()[0].lower().lstrip(".") if stripped else ""
            body = []
        else:
            if re.match(rf"^[ \t]*{re.escape(fchar)}{{{flen},}}[ \t]*$", line):
                blocks.append(
                    {
                        "open_line": open_line,
                        "indent": open_indent,
                        "lang": open_lang,
                        "body": "\n".join(body),
                    }
                )
                in_fence = False
            else:
                body.append(line)
    return blocks


def _strip_comments_and_bars(body: str) -> str:
    """Remove HTML comments (including --!>) and progress bars without HTML tag regexes."""
    out: list[str] = []
    pos = 0
    while pos < len(body):
        start = body.find("<!--", pos)
        if start == -1:
            out.append(body[pos:])
            break
        out.append(body[pos:start])
        end_std = body.find("-->", start + 4)
        end_bang = body.find("--!>", start + 4)
        ends = [idx for idx in (end_std, end_bang) if idx != -1]
        if not ends:
            out.append(" ")
            break
        end = min(ends)
        end_len = 4 if end == end_bang else 3
        out.append(" ")
        pos = end + end_len
    return re.sub(r"\[[=\->\s]+\]", " ", "".join(out))


def _has_flow_arrow(cleaned: str) -> bool:
    if UNICODE_ARROW_RE.search(cleaned):
        return True
    return any(tok in cleaned for tok in ASCII_FLOW_TOKENS)


def _is_tabular_or_tree(body: str, lang: str) -> bool:
    if lang in {"diff", "patch"}:
        return True
    if TREE_BRANCH_RE.search(body) and not BOX_CORNER_RE.search(body) and not ASCII_BOX_EDGE_RE.search(body):
        return True
    cleaned = _strip_comments_and_bars(body)
    if _has_flow_arrow(cleaned):
        return False
    non_empty = [ln.strip() for ln in body.splitlines() if ln.strip()]
    while non_empty and CLI_TABLE_FOOTER_RE.match(non_empty[-1]):
        non_empty.pop()
    if not non_empty:
        return False
    has_border = any(TABLE_RULE_RE.match(ln) for ln in non_empty) or bool(ASCII_BOX_EDGE_RE.search(body))
    if not has_border:
        return False
    pipe_lines = sum(1 for ln in non_empty if ln.startswith(("|", "│")))
    if pipe_lines / len(non_empty) > 0.45:
        return True
    all_grid = all(
        TABLE_RULE_RE.match(ln) or (ln.startswith("|") and ln.endswith("|")) or (ln.startswith("│") and ln.endswith("│"))
        for ln in non_empty
    )
    has_multi_col = any(MULTI_COL_RULE_RE.search(ln) for ln in non_empty)
    return bool(all_grid and (has_multi_col or lang in {"sql", "mysql", "psql"}))


class TestDocsTutorialsAndHowTos(unittest.TestCase):
    def test_diataxis_validator_and_required_pages(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "build" / "check_diataxis_docs.py"),
                str(DOCS_DIR),
                "--strict",
                "--mkdocs-config",
                str(REPO_ROOT / "mkdocs.yml"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Summary: 0 error(s), 0 warning(s)", proc.stdout)

        expected_files = [
            DOCS_DIR / "index.md",
            DOCS_DIR / "01-tutorials" / "index.md",
            DOCS_DIR / "01-tutorials" / "01-first-audit-sandbox.md",
            DOCS_DIR / "01-tutorials" / "02-ai-mcp-sandbox-lab.md",
            DOCS_DIR / "02-how-to-guides" / "index.md",
            DOCS_DIR / "02-how-to-guides" / "deployment" / "run-remote-and-container-audit.md",
            DOCS_DIR / "02-how-to-guides" / "deployment" / "publish-versioned-docs.md",
            DOCS_DIR / "02-how-to-guides" / "operations" / "tune-innodb-buffer-pool.md",
            DOCS_DIR / "02-how-to-guides" / "operations" / "run-offline-verification.md",
            DOCS_DIR / "02-how-to-guides" / "incident-response" / "diagnose-replication-lag.md",
            DOCS_DIR / "02-how-to-guides" / "security" / "audit-tls-and-auth-plugins.md",
        ]
        for path in expected_files:
            self.assertTrue(path.is_file(), f"Missing Diataxis document: {path}")

    def test_mkdocs_english_isolation_and_superfences(self) -> None:
        mkdocs_text = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(r"^\s*language:\s*en\b", mkdocs_text, re.M))
        self.assertIn("exclude_docs:", mkdocs_text)
        for pattern in ("fr/", "*.fr.md", "*_fr.md", "01-tutoriels/", "02-guides-pratiques/"):
            self.assertIn(pattern, mkdocs_text)
        self.assertIn("pymdownx.superfences", mkdocs_text)
        self.assertIn("name: mermaid", mkdocs_text)

        if yaml is not None:
            class _Loader(yaml.SafeLoader):
                pass

            _Loader.add_multi_constructor("tag:yaml.org,2002:python/", lambda loader, suffix, node: str(suffix))
            cfg = yaml.load(mkdocs_text, Loader=_Loader)
            self.assertEqual(cfg["theme"]["language"], "en")

            def _iter_nav(node: object) -> list[tuple[str, str]]:
                out: list[tuple[str, str]] = []
                if isinstance(node, list):
                    for item in node:
                        out.extend(_iter_nav(item))
                elif isinstance(node, dict):
                    for k, v in node.items():
                        if isinstance(v, str):
                            out.append((str(k), v))
                        else:
                            out.extend(_iter_nav(v))
                elif isinstance(node, str):
                    out.append(("", node))
                return out

            for title, rel in _iter_nav(cfg.get("nav", [])):
                self.assertFalse(FR_PATH_RE.search(rel), f"French path in EN nav: {rel}")
                self.assertFalse(re.match(r"^(?:FR\s*[-:]|\[FR\])", title, re.I), f"French nav title: {title}")
                self.assertTrue((DOCS_DIR / rel).is_file(), f"Missing nav target on disk: {rel}")

        for md_file in DOCS_DIR.rglob("*.md"):
            rel = md_file.relative_to(DOCS_DIR).as_posix()
            self.assertFalse(FR_PATH_RE.search(rel), f"Unexpected French file inside docs/: {rel}")

    def test_mermaid_and_zero_ascii_diagrams(self) -> None:
        mermaid_total = 0
        for md_file in sorted(REPO_ROOT.rglob("*.md")):
            if any(part in {".git", "node_modules", ".venv-docs", "site"} for part in md_file.parts):
                continue
            lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
            for blk in _parse_fenced_blocks(lines):
                lang = str(blk["lang"])
                body = str(blk["body"])
                if lang == "mermaid":
                    mermaid_total += 1
                    self.assertEqual(blk["indent"], "", f"Indented mermaid fence in {md_file}:{blk['open_line']}")
                    self.assertTrue(body.strip(), f"Empty mermaid block in {md_file}:{blk['open_line']}")
                    continue
                if lang not in {"diff", "patch", "markdown", "md"}:
                    first_lines = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
                    if first_lines:
                        for pat in MERMAID_HEADER_PATTERNS:
                            self.assertIsNone(
                                pat.match(first_lines[0]),
                                f"Untagged Mermaid block in {md_file}:{blk['open_line']} (lang={lang!r})",
                            )
                if not _is_tabular_or_tree(body, lang) and lang not in {"diff", "patch"}:
                    cleaned = _strip_comments_and_bars(body)
                    has_box = bool(BOX_CORNER_RE.search(body)) or bool(ASCII_BOX_EDGE_RE.search(body))
                    has_flow = _has_flow_arrow(cleaned)
                    if lang not in {"sql", "mysql", "psql"}:
                        self.assertFalse(
                            has_box or has_flow,
                            f"ASCII diagram found in {md_file}:{blk['open_line']} (lang={lang!r})",
                        )

        self.assertGreaterEqual(mermaid_total, 12)
        for tut in ("01-first-audit-sandbox.md", "02-ai-mcp-sandbox-lab.md"):
            tut_text = (DOCS_DIR / "01-tutorials" / tut).read_text(encoding="utf-8")
            self.assertIn("```mermaid", tut_text, f"Tutorial missing Mermaid diagram: {tut}")

    def test_executable_cli_flags_makefile_and_mcp_contracts(self) -> None:
        cmd_syntax, cwd = _perl_cmd("-c", "mysqltuner.pl")
        res_syntax = subprocess.run(cmd_syntax, cwd=cwd, capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(res_syntax.returncode, 0, res_syntax.stdout + res_syntax.stderr)
        self.assertIn("syntax OK", res_syntax.stdout + res_syntax.stderr)

        cmd_help, cwd = _perl_cmd("mysqltuner.pl", "--help")
        res_help = subprocess.run(cmd_help, cwd=cwd, capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(res_help.returncode, 0, res_help.stdout + res_help.stderr)
        self.assertNotIn("Use of uninitialized value", res_help.stdout + res_help.stderr)

        cmd_ind, cwd = _perl_cmd("mysqltuner.pl", "--list-indicators")
        res_ind = subprocess.run(cmd_ind, cwd=cwd, capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(res_ind.returncode, 0, res_ind.stderr)
        indicators = json.loads(res_ind.stdout)
        curr_ver = (REPO_ROOT / "CURRENT_VERSION.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(indicators.get("version"), curr_ver)
        self.assertGreaterEqual(len(indicators.get("cli_options", {})), 77)
        self.assertGreater(indicators.get("summary", {}).get("total", 0), 1000)

        # Build full valid option + alias + negation set from %CLI_METADATA
        valid_flags = set(indicators["cli_options"].keys())
        pl_text = (REPO_ROOT / "mysqltuner.pl").read_text(encoding="utf-8", errors="replace")
        meta_match = re.search(r"our %CLI_METADATA = \((.*?)\n\);", pl_text, re.S)
        self.assertIsNotNone(meta_match)
        for spec_m in re.finditer(r"^\s*['\"]([^'\"]+)['\"]\s*=>\s*\{([^}]*)\}", meta_match.group(1), re.M):
            spec, body = spec_m.groups()
            is_neg = ("!" in spec) or ("'!'" in body)
            for part in spec.split("|"):
                opt = re.sub(r"[!+=:].*$", "", part)
                valid_flags.add(opt)
                if is_neg:
                    valid_flags.add("no" + opt)
                    valid_flags.add("no-" + opt)

        # Every flag passed to mysqltuner.pl in tutorials/how-tos must exist in %CLI_METADATA
        for folder in ("01-tutorials", "02-how-to-guides"):
            for md_file in sorted((DOCS_DIR / folder).rglob("*.md")):
                txt = md_file.read_text(encoding="utf-8")
                for blk in re.findall(r"```bash\n(.*?)```", txt, re.S):
                    joined = blk.replace("\\\n", " ")
                    for line in joined.splitlines():
                        if "mysqltuner.pl" in line:
                            for flag in re.findall(r"(?<![A-Za-z0-9_])--([a-z][a-z0-9_-]*)", line):
                                self.assertIn(flag, valid_flags, f"Unknown mysqltuner.pl flag --{flag} in {md_file}")

        # Ensure phantom --version flag is not documented as an offline flag
        for doc_rel in (
            "03-reference/cli-and-scripts/cli-options.md",
            "04-explanation/architecture-overview/diagnostic-pipeline.md",
        ):
            self.assertNotIn("--version", (DOCS_DIR / doc_rel).read_text(encoding="utf-8"))

        # Verify every make <target> in tutorials/how-tos exists in Makefile
        make_targets = set(re.findall(r"^([A-Za-z0-9_-]+):", (REPO_ROOT / "Makefile").read_text(encoding="utf-8"), re.M))
        for folder in ("01-tutorials", "02-how-to-guides"):
            for md_file in sorted((DOCS_DIR / folder).rglob("*.md")):
                txt = md_file.read_text(encoding="utf-8")
                for blk in re.findall(r"```bash\n(.*?)```", txt, re.S):
                    for target in re.findall(r"\bmake\s+([A-Za-z0-9_-]+)", blk):
                        self.assertIn(target, make_targets, f"Unknown Makefile target `make {target}` in {md_file}")

        # Verify Python scripts compile, mcp_server --help and JSON-RPC stdio contracts match docs
        for py_rel in ("build/mcp_server.py", "build/check_diataxis_docs.py", "build/mkdocs_hooks.py"):
            py_compile.compile(str(REPO_ROOT / py_rel), doraise=True)

        with tempfile.TemporaryDirectory() as tmp_cache:
            env = os.environ.copy()
            env["CACHE_DIR"] = tmp_cache
            env["READ_ONLY"] = "true"
            env["MYSQLTUNER_PL"] = str(Path(tmp_cache) / "nonexistent_mysqltuner.pl")
            mcp_help = subprocess.run(
                [sys.executable, str(REPO_ROOT / "build" / "mcp_server.py"), "--help"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(mcp_help.returncode, 0, mcp_help.stdout + mcp_help.stderr)

            rpc_in = (
                '{"jsonrpc":"2.0","method":"initialize","id":1}\n'
                '{"jsonrpc":"2.0","method":"tools/list","id":2}\n'
                '{"jsonrpc":"2.0","method":"resources/list","id":3}\n'
            )
            rpc_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "build" / "mcp_server.py")],
                input=rpc_in,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(rpc_proc.returncode, 0, rpc_proc.stderr)
            responses = [json.loads(line) for line in rpc_proc.stdout.splitlines() if line.strip()]
            self.assertEqual(len(responses), 3)
            self.assertEqual(responses[0]["result"]["serverInfo"]["version"], curr_ver)
            tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
            resource_uris = {r["uri"] for r in responses[2]["result"]["resources"]}
            self.assertEqual(tool_names, EXPECTED_MCP_TOOLS)
            self.assertEqual(resource_uris, EXPECTED_MCP_RESOURCES)

        for rel in (
            "README.md",
            "README.fr.md",
            "README.it.md",
            "README.ru.md",
            "AGENT.md",
            "documentation/mcp_ai_integration_guide.md",
            "documentation/mcp_ai_integration_guide.fr.md",
            "docs/03-reference/cli-and-scripts/mcp-server-api.md",
        ):
            self.assertNotIn("mysqltuner://indicators/summary.json", (REPO_ROOT / rel).read_text(encoding="utf-8"))

        for df_name in ("Dockerfile", "Dockerfile.mcp"):
            df_text = (REPO_ROOT / df_name).read_text(encoding="utf-8")
            self.assertRegex(df_text, r"FROM\s+\S+@sha256:[0-9a-f]{64}")
            for m in re.finditer(r"^\s*COPY\s+(\S+)\s+", df_text, re.M):
                src = m.group(1).lstrip("./")
                self.assertTrue((REPO_ROOT / src).exists(), f"Missing COPY source {src} in {df_name}")

    def test_latex_display_math_formatting(self) -> None:
        targets = [
            REPO_ROOT / "documentation" / "REFERENCES.md",
            REPO_ROOT / "documentation" / "specifications" / "issue_1003_skill_analyze_buffer_pool.md",
            REPO_ROOT / "documentation" / "specifications" / "issue_1007_skill_detect_fragmented_tables.md",
            REPO_ROOT / "documentation" / "specifications" / "performance_schema_audit.md",
            REPO_ROOT / "documentation" / "specifications" / "roadmap_phase_v_innodb.md",
            REPO_ROOT / ".agent" / "skills" / "detect-fragmented-tables" / "SKILL.md",
        ]
        for path in targets:
            lines = path.read_text(encoding="utf-8").splitlines()
            for idx, ln in enumerate(lines, start=1):
                self.assertNotIn(r"\operatorname", ln, f"Disallowed \\operatorname in {path}:{idx}")
                if "$$" in ln:
                    self.assertEqual(ln, "$$", f"Display math delimiter must be column-0 '$$' alone at {path}:{idx}: {ln!r}")

    def test_markdownlint_line_length_in_docs(self) -> None:
        fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
        heading_re = re.compile(r"^#{1,6}\s")
        table_re = re.compile(r"^\s*\|")
        hr_re = re.compile(r"^\s*(?:[-*_]\s*){3,}$")
        link_ref_re = re.compile(r"^\s*\[[^\]]+\]:\s")
        link_full_re = re.compile(r"(!?\[[^\]]*\])\(([^)\n]+)\)")
        bare_url_re = re.compile(r"https?://[^\s)>]+")

        def _is_long_url_exempt(line: str) -> bool:
            tokens: list[str] = []

            def _strip_link(match: re.Match[str]) -> str:
                tokens.append(match.group(2).strip())
                return f"{match.group(1)}()"

            without_links = link_full_re.sub(_strip_link, line)

            def _strip_url(match: re.Match[str]) -> str:
                tokens.append(match.group(0))
                return ""

            stripped = bare_url_re.sub(_strip_url, without_links)
            return len(stripped) <= 80 and sum(1 for tok in tokens if len(tok) > 40) == 1

        for md_file in sorted(DOCS_DIR.rglob("*.md")):
            fence_char: str | None = None
            fence_len = 0
            for idx, ln in enumerate(md_file.read_text(encoding="utf-8").splitlines(), start=1):
                if fence_char is not None:
                    if re.match(rf"^\s*{re.escape(fence_char)}{{{fence_len},}}\s*$", ln):
                        fence_char = None
                        fence_len = 0
                    continue
                fence_match = fence_re.match(ln)
                if fence_match:
                    marker = fence_match.group(1)
                    fence_char = marker[0]
                    fence_len = len(marker)
                    continue
                if heading_re.match(ln) or table_re.match(ln) or hr_re.match(ln) or link_ref_re.match(ln):
                    continue
                if len(ln) > 80 and _is_long_url_exempt(ln):
                    continue
                self.assertLessEqual(
                    len(ln),
                    80,
                    f"MD013 line length > 80 ({len(ln)} chars) at {md_file}:{idx}: {ln}",
                )


if __name__ == "__main__":
    unittest.main()
