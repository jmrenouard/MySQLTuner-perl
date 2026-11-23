#!/usr/bin/env python3
# ===========================================================================
# Script:      build/mkdocs_hooks.py
# Description: MkDocs Material lifecycle hooks for MySQLTuner documentation.
#              Injects sanitized release notes, resolves version and include
#              tokens, and prevents strict-mode warnings on legacy links.
# Author:      Jean-Marie Renouard / Antigravity
# Usage:       Configured in mkdocs.yml via hooks: [build/mkdocs_hooks.py]
# ===========================================================================

from __future__ import annotations

import atexit
import posixpath
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

try:
    from mkdocs.structure.files import File
except ImportError:  # pragma: no cover - allows standalone unit imports without mkdocs
    File = None  # type: ignore[assignment]

GITHUB_BLOB_BASE = "https://github.com/major/MySQLTuner-perl/blob/master"
ALLOWED_INCLUDE_SOURCES = frozenset(
    {
        "mysql_support.md",
        "mariadb_support.md",
        "FEATURES.md",
        "USAGE.md",
        "SECURITY.md",
    }
)

_SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_LINK_RE = re.compile(r"(!?\[[^\]]*\])\(([^)\n]+)\)")
_CURRENT_VERSION_RE = re.compile(r"<!--\s*CURRENT_VERSION\s*-->")
_AUTO_RELEASES_TABLE_RE = re.compile(r"<!--\s*AUTO_RELEASES_TABLE\s*-->")
_INCLUDE_SOURCE_RE = re.compile(r"<!--\s*INCLUDE_SOURCE:\s*([^\n>]+?)\s*-->")
_RELEASE_DATE_RE = re.compile(r"^\*\*Date\*\*:\s*(\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
_CHANGELOG_HEADER_RE = re.compile(r"^\s*(\d+\.\d+\.\d+)\s+(\d{4}-\d{2}-\d{2})\s*$")
_EXTERNAL_SCHEME_RE = re.compile(r"^(?:https?|mailto|ftp|tel|data|javascript):", re.IGNORECASE)

_FALLBACK_TEMP_DIRS: list[Path] = []


def _cleanup_fallback_dirs() -> None:
    """Remove temporary directories created when File.generated is unavailable."""
    while _FALLBACK_TEMP_DIRS:
        tmp_dir = _FALLBACK_TEMP_DIRS.pop()
        shutil.rmtree(tmp_dir, ignore_errors=True)


atexit.register(_cleanup_fallback_dirs)


def semver_key(filename: str | Path) -> tuple[int, int, int]:
    """Parse vMAJOR.MINOR.PATCH.md into an integer tuple for semantic sorting."""
    name = Path(filename).name
    match = _SEMVER_RE.search(name)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _get_repo_root(config: dict[str, Any] | None = None) -> Path:
    """Resolve repository root from MkDocs config or fallback to script parent."""
    if config and config.get("docs_dir"):
        candidate = Path(str(config["docs_dir"])).resolve().parent
        if (candidate / "CURRENT_VERSION.txt").is_file() or (candidate / "releases").is_dir():
            return candidate
    return Path(__file__).resolve().parent.parent


def _transform_outside_code(text: str, transform_fn: Any) -> str:
    """Apply transform_fn only to Markdown segments outside code fences and inline code."""
    lines = text.splitlines(keepends=True)
    out_lines: list[str] = []
    fence_char: str | None = None
    fence_len = 0

    for line in lines:
        stripped = line.rstrip("\r\n")
        if fence_char is not None:
            out_lines.append(line)
            if re.match(rf"^\s*{re.escape(fence_char)}{{{fence_len},}}\s*$", stripped):
                fence_char = None
                fence_len = 0
            continue

        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            marker = fence_match.group(1)
            fence_char = marker[0]
            fence_len = len(marker)
            out_lines.append(line)
            continue

        if "`" not in line:
            out_lines.append(transform_fn(line))
            continue

        line_out: list[str] = []
        buf: list[str] = []
        i = 0
        n = len(line)
        while i < n:
            if line[i] != "`":
                buf.append(line[i])
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
                if buf:
                    line_out.append(transform_fn("".join(buf)))
                    buf.clear()
                line_out.append(line[i:close_pos])
                i = close_pos
            else:
                buf.append(line[i : i + tick_len])
                i += tick_len

        if buf:
            line_out.append(transform_fn("".join(buf)))
        out_lines.append("".join(line_out))

    return "".join(out_lines)


def _split_link_destination(raw_dest: str) -> tuple[str, str]:
    """Split Markdown link destination into (url, optional_title_suffix)."""
    dest = raw_dest.strip()
    if dest.startswith("<"):
        end_idx = dest.find(">")
        if end_idx != -1:
            return dest[1:end_idx].strip(), dest[end_idx + 1 :]
    parts = dest.split(None, 1)
    if len(parts) == 2:
        return parts[0], " " + parts[1]
    return dest, ""


def _rewrite_link_match(match: re.Match[str], rel_source_dir: str) -> str:
    """Rewrite legacy file:/// and out-of-docs links to GitHub master blob URLs."""
    prefix = match.group(1)
    raw_dest = match.group(2)
    url, title_suffix = _split_link_destination(raw_dest)

    if not url or url.startswith("#") or url.startswith("//") or _EXTERNAL_SCHEME_RE.match(url):
        return match.group(0)

    url_path, sep, fragment = url.partition("#")
    frag_suffix = f"#{fragment}" if sep else ""

    if url_path.lower().startswith("file://"):
        repo_path = re.sub(r"^file:///?", "", url_path, flags=re.IGNORECASE)
        repo_path = re.sub(r"^(?:.*/)?MySQLTuner-perl(?:-mkdocs)?/", "", repo_path)
        repo_path = repo_path.lstrip("/")
        return f"{prefix}({GITHUB_BLOB_BASE}/{repo_path}{frag_suffix}{title_suffix})"

    if url_path.startswith("/"):
        repo_path = url_path.lstrip("/")
        if repo_path.startswith("docs/"):
            return match.group(0)
        return f"{prefix}({GITHUB_BLOB_BASE}/{repo_path}{frag_suffix}{title_suffix})"

    norm_base = rel_source_dir.strip("/.")
    if norm_base:
        resolved = posixpath.normpath(posixpath.join(norm_base, url_path))
    else:
        resolved = posixpath.normpath(url_path)

    # Keep sibling release links inside the virtual 03-reference/releases/ tree
    if norm_base == "releases" and re.fullmatch(r"releases/v\d+\.\d+\.\d+\.md", resolved):
        return match.group(0)

    if resolved == "docs" or resolved.startswith("docs/"):
        return match.group(0)

    clean_repo_path = re.sub(r"^(?:\.\./)+", "", resolved)
    if clean_repo_path == ".":
        clean_repo_path = ""
    return f"{prefix}({GITHUB_BLOB_BASE}/{clean_repo_path}{frag_suffix}{title_suffix})"


def sanitize_legacy_markdown(text: str, rel_source_dir: str = "") -> str:
    """Rewrite file:/// and repo-relative links outside docs/ into GitHub blob URLs."""
    return _transform_outside_code(
        text,
        lambda segment: _LINK_RE.sub(
            lambda m: _rewrite_link_match(m, rel_source_dir),
            segment,
        ),
    )


def _list_release_files(repo_root: Path) -> list[Path]:
    """Return releases/v*.md sorted descending by semantic version."""
    releases_dir = repo_root / "releases"
    if not releases_dir.is_dir():
        return []
    return sorted(releases_dir.glob("v*.md"), key=semver_key, reverse=True)


def _parse_changelog_dates(repo_root: Path) -> dict[str, str]:
    """Extract version -> YYYY-MM-DD mapping from Changelog."""
    changelog = repo_root / "Changelog"
    if not changelog.is_file():
        return {}
    dates: dict[str, str] = {}
    for line in changelog.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _CHANGELOG_HEADER_RE.match(line)
        if match:
            dates[match.group(1)] = match.group(2)
    return dates


def _extract_release_date(release_path: Path, changelog_dates: dict[str, str]) -> str:
    """Parse release date from '**Date**: YYYY-MM-DD' or fall back to Changelog."""
    content = release_path.read_text(encoding="utf-8", errors="replace")
    match = _RELEASE_DATE_RE.search(content)
    if match:
        return match.group(1)
    ver_tuple = semver_key(release_path.name)
    if ver_tuple != (0, 0, 0):
        ver_str = f"{ver_tuple[0]}.{ver_tuple[1]}.{ver_tuple[2]}"
        if ver_str in changelog_dates:
            return changelog_dates[ver_str]
    return "N/A"


def _build_releases_table(repo_root: Path) -> str:
    """Render the Markdown table of all release notes sorted newest-first."""
    release_files = _list_release_files(repo_root)
    if not release_files:
        return "_No release notes found._"
    changelog_dates = _parse_changelog_dates(repo_root)
    rows = [
        "| Version | Release Date | Release Notes |",
        "| :--- | :--- | :--- |",
    ]
    for rel_path in release_files:
        version_label = rel_path.stem
        release_date = _extract_release_date(rel_path, changelog_dates)
        rows.append(f"| `{version_label}` | {release_date} | [{version_label}]({rel_path.name}) |")
    return "\n".join(rows)


def _find_releases_nav_list(nav: Any) -> list[Any] | None:
    """Locate Reference -> Releases Archive list inside MkDocs nav config."""
    if not isinstance(nav, list):
        return None
    for item in nav:
        if isinstance(item, dict) and "Reference" in item and isinstance(item["Reference"], list):
            for sub in item["Reference"]:
                if (
                    isinstance(sub, dict)
                    and "Releases Archive" in sub
                    and isinstance(sub["Releases Archive"], list)
                ):
                    return sub["Releases Archive"]
    return None


def _register_not_in_nav(config: dict[str, Any], pattern: str) -> None:
    """Ensure injected release pages are accepted as not_in_nav when absent from nav."""
    existing = config.get("not_in_nav")
    try:
        import pathspec  # type: ignore[import-not-found]

        if isinstance(existing, pathspec.PathSpec):
            combined = list(existing.patterns) + list(
                pathspec.PathSpec.from_lines("gitwildmatch", [pattern]).patterns
            )
            config["not_in_nav"] = pathspec.PathSpec(combined)
            return
        if existing is None:
            config["not_in_nav"] = pathspec.PathSpec.from_lines("gitwildmatch", [pattern])
            return
    except ImportError:
        pass

    if isinstance(existing, list):
        if pattern not in existing:
            existing.append(pattern)
    elif existing is None:
        config["not_in_nav"] = [pattern]


def on_config(config: dict[str, Any]) -> dict[str, Any]:
    """Register injected release notes in nav (or not_in_nav) to avoid strict warnings."""
    repo_root = _get_repo_root(config)
    release_files = _list_release_files(repo_root)
    if not release_files:
        return config

    releases_nav = _find_releases_nav_list(config.get("nav"))
    if releases_nav is not None:
        existing_uris = set()
        for entry in releases_nav:
            if isinstance(entry, str):
                existing_uris.add(entry)
            elif isinstance(entry, dict):
                existing_uris.update(str(v) for v in entry.values())

        for rel_path in release_files:
            uri = f"03-reference/releases/{rel_path.name}"
            if uri not in existing_uris:
                releases_nav.append({rel_path.stem: uri})
                existing_uris.add(uri)
    else:
        _register_not_in_nav(config, "03-reference/releases/v*.md")

    return config


def _create_virtual_file(config: dict[str, Any], uri: str, content: str) -> Any:
    """Create a virtual MkDocs File using File.generated with a safe temp-dir fallback."""
    if File is None:  # pragma: no cover
        raise RuntimeError("mkdocs.structure.files.File is not available")

    if hasattr(File, "generated"):
        return File.generated(config, uri, content=content)

    tmp_root = Path(tempfile.mkdtemp(prefix="mkdocs_hooks_"))
    _FALLBACK_TEMP_DIRS.append(tmp_root)
    target = tmp_root / uri
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return File(
        uri,
        str(tmp_root),
        config["site_dir"],
        bool(config.get("use_directory_urls", True)),
    )


def on_files(files: Any, config: dict[str, Any]) -> Any:
    """Inject sanitized releases/v*.md files virtually under 03-reference/releases/."""
    repo_root = _get_repo_root(config)
    release_files = _list_release_files(repo_root)
    if not release_files:
        return files

    for rel_path in release_files:
        raw_text = rel_path.read_text(encoding="utf-8", errors="replace")
        sanitized = sanitize_legacy_markdown(raw_text, rel_source_dir="releases")
        uri = f"03-reference/releases/{rel_path.name}"

        existing = files.get_file_from_path(uri) if hasattr(files, "get_file_from_path") else None
        if existing is not None and hasattr(files, "remove"):
            files.remove(existing)

        files.append(_create_virtual_file(config, uri, sanitized))

    return files


def _load_current_version(repo_root: Path) -> str:
    """Read and trim CURRENT_VERSION.txt."""
    version_file = repo_root / "CURRENT_VERSION.txt"
    if not version_file.is_file():
        return "unknown"
    return version_file.read_text(encoding="utf-8").strip()


def _load_whitelisted_source(repo_root: Path, rel_path: str) -> str:
    """Validate and load an explicitly whitelisted repository Markdown file."""
    cleaned = rel_path.strip()
    if cleaned not in ALLOWED_INCLUDE_SOURCES:
        raise ValueError(
            f"Disallowed INCLUDE_SOURCE path '{cleaned}'. "
            f"Allowed values: {sorted(ALLOWED_INCLUDE_SOURCES)}"
        )

    repo_resolved = repo_root.resolve()
    target_path = (repo_resolved / cleaned).resolve()
    if target_path.parent != repo_resolved or not target_path.is_file():
        raise ValueError(f"INCLUDE_SOURCE target does not exist inside repository root: '{cleaned}'")

    raw_text = target_path.read_text(encoding="utf-8")
    # Strip duplicate leading '# H1' so page heading hierarchy remains valid
    without_h1 = re.sub(r"\A(?:\ufeff)?\s*#\s+[^\n]*(?:\r?\n)+", "", raw_text)
    return sanitize_legacy_markdown(without_h1, rel_source_dir="")


def on_page_markdown(
    markdown: str,
    page: Any,
    config: dict[str, Any],
    files: Any,
) -> str:
    """Expand version, release table, and whitelisted include tokens outside code spans."""
    repo_root = _get_repo_root(config)

    def _replace_tokens(segment: str) -> str:
        if "<!--" not in segment:
            return segment

        if _CURRENT_VERSION_RE.search(segment):
            version = _load_current_version(repo_root)
            segment = _CURRENT_VERSION_RE.sub(lambda _: version, segment)

        if _AUTO_RELEASES_TABLE_RE.search(segment):
            table = _build_releases_table(repo_root)
            segment = _AUTO_RELEASES_TABLE_RE.sub(lambda _: table, segment)

        if _INCLUDE_SOURCE_RE.search(segment):
            segment = _INCLUDE_SOURCE_RE.sub(
                lambda m: _load_whitelisted_source(repo_root, m.group(1)),
                segment,
            )

        return segment

    return _transform_outside_code(markdown, _replace_tokens)
