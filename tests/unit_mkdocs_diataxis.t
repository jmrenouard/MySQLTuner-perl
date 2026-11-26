#!/usr/bin/env perl
# ===========================================================================
# Test:        tests/unit_mkdocs_diataxis.t
# Description: Hermetic unit and integration verification suite for the
#              Diataxis documentation tree, MkDocs Material configuration,
#              lifecycle hooks, STE/governance validator, Apache .htaccess,
#              and GitHub Actions CI/CD workflows.
# Author:      Jean-Marie Renouard / Antigravity
# Project:     MySQLTuner-perl
# ===========================================================================
use strict;
use warnings;
use Test::More;
use FindBin;
use File::Spec;
use File::Temp qw(tempdir tempfile);
use Cwd qw(abs_path);
use JSON::PP qw(decode_json);

my $PROJECT_ROOT = abs_path( File::Spec->catdir( $FindBin::Bin, '..' ) );

sub slurp_raw {
    my ($path) = @_;
    open my $fh, '<:raw', $path or die "Cannot read $path: $!";
    local $/;
    my $data = <$fh>;
    close $fh;
    return $data;
}

sub has_lf_only {
    my ($path) = @_;
    my $raw = slurp_raw($path);
    return index( $raw, "\r" ) == -1 ? 1 : 0;
}

sub has_binary {
    my ($bin) = @_;
    for my $dir ( File::Spec->path() ) {
        my $candidate = File::Spec->catfile( $dir, $bin );
        return $candidate if -f $candidate && -x $candidate;
    }
    return undef;
}

sub find_python_bin {
    my $venv_py = File::Spec->catfile( $PROJECT_ROOT, '.venv-docs', 'bin', 'python' );
    return $venv_py if -f $venv_py && -x $venv_py;
    return has_binary('python3');
}

sub python_has_yaml {
    my ($py_bin) = @_;
    return 0 unless defined $py_bin;
    my $rc = system( $py_bin, '-B', '-c', 'import yaml' );
    return ( $rc >> 8 ) == 0 ? 1 : 0;
}

sub run_py_script {
    my ( $py_bin, $script_body, @args ) = @_;
    my ( $fh, $script_path ) = tempfile( SUFFIX => '.py', UNLINK => 1 );
    binmode( $fh, ':raw' );
    print {$fh} $script_body;
    close $fh;

    my $quoted_args = join ' ', map { qq{"$_"} } ( $py_bin, '-B', $script_path, @args );
    my $out         = qx($quoted_args 2>&1);
    my $exit_code   = $? >> 8;
    return ( $exit_code, $out );
}

my $PYTHON_BIN = find_python_bin();
my $HAS_YAML   = python_has_yaml($PYTHON_BIN);

# ===========================================================================
# Subtest 1: Config files, LF endings, JSON/YAML schema, mike redirect, site_url
# ===========================================================================
subtest 'Subtest 1: Config files LF endings and JSON/YAML schema' => sub {
    my @config_files = (
        'mkdocs.yml',
        'requirements-docs.txt',
        '.markdownlint.json',
        '.vale.ini',
        File::Spec->catfile( 'build', 'docs_htaccess' ),
    );

    for my $rel (@config_files) {
        my $full = File::Spec->catfile( $PROJECT_ROOT, $rel );
        ok( -f $full, "$rel exists" );
        ok( has_lf_only($full), "$rel uses Unix LF line endings" );
    }

    my $req_txt = slurp_raw( File::Spec->catfile( $PROJECT_ROOT, 'requirements-docs.txt' ) );
    like( $req_txt, qr/mkdocs-material>=9\.5,<10/, 'requirements-docs.txt pins mkdocs-material>=9.5,<10' );
    like( $req_txt, qr/mike>=2\.1,<3/,            'requirements-docs.txt pins mike>=2.1,<3' );

    my $mdl_raw = slurp_raw( File::Spec->catfile( $PROJECT_ROOT, '.markdownlint.json' ) );
    my $mdl     = eval { decode_json($mdl_raw) };
    ok( defined $mdl && !$@, '.markdownlint.json parses as valid JSON' );
    is( $mdl->{MD013}{line_length}, 80, 'MD013 line_length is 80' );
    ok( !$mdl->{MD013}{code_blocks}, 'MD013 code_blocks disabled' );
    ok( !$mdl->{MD013}{tables},      'MD013 tables disabled' );
    ok( exists $mdl->{MD013}{headings} && !$mdl->{MD013}{headings}, 'MD013 headings disabled' );
    ok( $mdl->{MD024}{siblings_only}, 'MD024 siblings_only enabled' );
    ok( $mdl->{MD041},                'MD041 enabled' );
    is( $mdl->{MD046}{style}, 'fenced', 'MD046 style is fenced' );
    ok( exists $mdl->{MD060} && !$mdl->{MD060}, 'MD060 disabled' );

    my $vale_ini = slurp_raw( File::Spec->catfile( $PROJECT_ROOT, '.vale.ini' ) );
    like( $vale_ini, qr/StylesPath\s*=\s*\.vale\/styles/, 'Vale StylesPath configured' );
    like( $vale_ini, qr/Packages\s*=\s*Google/,           'Vale Packages configured with Google' );
    like( $vale_ini, qr/Vocab\s*=\s*MySQLTuner/,          'Vale Vocab configured with MySQLTuner' );
    like( $vale_ini, qr{\[docs/02-how-to-guides/\*\*/\*\.md\]}, 'Vale targets 02-how-to-guides' );
    unlike( $vale_ini, qr/STE-Procedural/, 'Vale does not reference missing STE-Procedural style' );
    unlike( $vale_ini, qr/ASD-STE100/,     'Vale config contains no ASD-STE100 reference' );

    my $vocab = File::Spec->catfile(
        $PROJECT_ROOT, '.vale', 'styles', 'config', 'vocabularies', 'MySQLTuner', 'accept.txt'
    );
    ok( -f $vocab, 'Vale MySQLTuner vocabulary accept.txt exists' );

  SKIP: {
        skip 'Python3 with PyYAML required for mkdocs.yml YAML validation', 2 unless $HAS_YAML;

        my $py_check = <<'PY';
import pathlib
import sys
import yaml

root = pathlib.Path(sys.argv[1])

class MkDocsSafeLoader(yaml.SafeLoader):
    pass

def _python_name_constructor(loader, suffix, node):
    return f"python/name:{suffix}"

MkDocsSafeLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:",
    _python_name_constructor,
)

cfg = yaml.load((root / "mkdocs.yml").read_text(encoding="utf-8"), Loader=MkDocsSafeLoader)
assert isinstance(cfg, dict), "mkdocs.yml must load as dict"
assert cfg.get("site_url") == "https://mysqltuner.lightpath.fr/", f"bad site_url: {cfg.get('site_url')}"
assert cfg.get("docs_dir") == "docs", f"bad docs_dir: {cfg.get('docs_dir')}"
assert cfg.get("theme", {}).get("name") == "material", "theme.name must be material"
assert cfg.get("extra", {}).get("version", {}).get("provider") == "mike", "version provider must be mike"
assert cfg.get("extra", {}).get("version", {}).get("default") == "latest", "default version must be latest"
assert cfg.get("extra", {}).get("version", {}).get("alias") is True, "version alias must be true"

exclude_raw = cfg.get("exclude_docs")
exclude_text = (
    exclude_raw
    if isinstance(exclude_raw, str)
    else "\n".join(str(x) for x in (exclude_raw or []))
)
for required_excl in (
    "ACTION_LOGBOOK.md",
    "RCA_REGISTER.md",
    "fr/",
    "*.fr.md",
    "*_fr.md",
    "01-tutoriels/",
    "02-guides-pratiques/",
    "03-reference-fr/",
    "04-explications/",
):
    assert required_excl in exclude_text, f"exclude_docs missing {required_excl}"

ext_names = []
for ext in cfg.get("markdown_extensions", []):
    if isinstance(ext, str):
        ext_names.append(ext)
    elif isinstance(ext, dict):
        ext_names.extend(str(k) for k in ext.keys())
for banned_ext in ("pymdownx.snippets", "pymdownx.tabbed"):
    assert banned_ext not in ext_names, f"disallowed markdown extension present: {banned_ext}"

plugins = cfg.get("plugins", [])
mike_cfg = None
for entry in plugins:
    if isinstance(entry, dict) and "mike" in entry:
        mike_cfg = entry["mike"]
assert isinstance(mike_cfg, dict), "mike plugin entry must exist"
assert mike_cfg.get("alias_type") == "redirect", f"mike alias_type must be redirect, got {mike_cfg.get('alias_type')}"
assert mike_cfg.get("canonical_version") == "latest", "mike canonical_version must be latest"
assert "build/mkdocs_hooks.py" in cfg.get("hooks", []), "hooks must include build/mkdocs_hooks.py"

docs_dir = root / "docs"
assert (docs_dir / cfg["theme"]["logo"]).is_file(), "theme logo missing"
assert (docs_dir / cfg["theme"]["favicon"]).is_file(), "theme favicon missing"

def iter_nav_paths(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from iter_nav_paths(item)
    elif isinstance(node, dict):
        for val in node.values():
            yield from iter_nav_paths(val)

nav_paths = list(iter_nav_paths(cfg.get("nav", [])))
assert len(nav_paths) >= 24, f"expected >=24 nav paths, got {len(nav_paths)}"
for rel in nav_paths:
    assert (docs_dir / rel).is_file(), f"nav target missing on disk: {rel}"

print("MKDOCS_YML_OK")
PY

        my ( $rc, $out ) = run_py_script( $PYTHON_BIN, $py_check, $PROJECT_ROOT );
        is( $rc, 0, "mkdocs.yml schema, mike redirect, site_url, and nav paths verified: $out" );
        like( $out, qr/MKDOCS_YML_OK/, 'mkdocs.yml verification marker emitted' );
    }
};

# ===========================================================================
# Subtest 2: Documentation structure, links, section governance, and STE validator
# ===========================================================================
subtest 'Subtest 2: Documentation structure, relative links, governance, and STE' => sub {
    my $validator = File::Spec->catfile( $PROJECT_ROOT, 'build', 'check_diataxis_docs.py' );
    ok( -f $validator, 'build/check_diataxis_docs.py exists' );
    ok( has_lf_only($validator), 'build/check_diataxis_docs.py uses Unix LF line endings' );

  SKIP: {
        skip 'python3 required to execute build/check_diataxis_docs.py', 11 unless defined $PYTHON_BIN;

        my $tmp_pyc_dir = tempdir( CLEANUP => 1 );
        my $pyc_out     = File::Spec->catfile( $tmp_pyc_dir, 'check_diataxis_docs.pyc' );
        my $compile_py  = <<'PY';
import py_compile, sys
py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)
print("COMPILE_OK")
PY
        my ( $crc, $cout ) = run_py_script( $PYTHON_BIN, $compile_py, $validator, $pyc_out );
        is( $crc, 0, "build/check_diataxis_docs.py compiles cleanly: $cout" );

        my $docs_dir   = File::Spec->catdir( $PROJECT_ROOT, 'docs' );
        my $mkdocs_cfg = File::Spec->catfile( $PROJECT_ROOT, 'mkdocs.yml' );
        my $vout       = qx("$PYTHON_BIN" -B "$validator" "$docs_dir" --strict --mkdocs-config "$mkdocs_cfg" 2>&1);
        my $vrc        = $? >> 8;
        is( $vrc, 0, "check_diataxis_docs.py docs --strict --mkdocs-config mkdocs.yml exits 0: $vout" );
        like(
            $vout,
            qr/Summary:\s*0\s+error\(s\),\s*0\s+warning\(s\)/,
            'check_diataxis_docs.py reports 0 error(s), 0 warning(s)'
        );

        # Adversarial negative fixture in isolated temp directory (never mutates docs/)
        my $bad_docs = File::Spec->catdir( $tmp_pyc_dir, 'bad_docs' );
        for my $q ( '', '01-tutorials', '02-how-to-guides', '03-reference', '04-explanation' ) {
            my $dir = $q eq '' ? $bad_docs : File::Spec->catdir( $bad_docs, $q );
            mkdir $dir or die "mkdir $dir: $!";
            my $idx = File::Spec->catfile( $dir, 'index.md' );
            open my $fh, '>:raw', $idx or die "open $idx: $!";
            print {$fh} "# Index\n\nPlaceholder index.\n";
            close $fh;
        }
        my $bad_howto = File::Spec->catfile( $bad_docs, '02-how-to-guides', 'bad-guide.md' );
        open my $bfh, '>:raw', $bad_howto or die "open $bad_howto: $!";
        print {$bfh} "# Bad Guide\n\nSee [Missing](missing_target.md).\n\n"
          . "This Diataxis guide contains a prose line that intentionally exceeds eighty characters in length.\n\n"
          . "1. You shouldn't do this.\n";
        close $bfh;

        my $bad_mkdocs = File::Spec->catfile( $tmp_pyc_dir, 'bad_mkdocs.yml' );
        open my $mfh, '>:raw', $bad_mkdocs or die "open $bad_mkdocs: $!";
        print {$mfh} "site_name: Bad Docs\n"
          . "markdown_extensions:\n"
          . "  - pymdownx.snippets\n"
          . "  - pymdownx.superfences:\n"
          . "      custom_fences:\n"
          . "        - name: mermaid\n"
          . "          class: mermaid\n"
          . "          format: !!python/name:pymdownx.superfences.fence_code_format\n"
          . "extra:\n"
          . "  version:\n"
          . "    provider: mike\n"
          . "    alias: true\n";
        close $mfh;

        my $neg_out = qx("$PYTHON_BIN" -B "$validator" "$bad_docs" --strict --mkdocs-config "$bad_mkdocs" 2>&1);
        my $neg_rc  = $? >> 8;
        is( $neg_rc, 1, 'check_diataxis_docs.py rejects broken link, STE error, methodology ref, >80 char line, and bad mkdocs.yml' );
        like( $neg_out, qr/Broken relative link target/, 'Negative test detects broken relative link' );
        like( $neg_out, qr/STE Rule/,                    'Negative test detects STE violation' );
        like( $neg_out, qr/missing a rollback/i,         'Strict mode promotes missing rollback to ERROR' );
        like( $neg_out, qr/Forbidden methodology reference/i, 'Negative test detects methodology reference' );
        like( $neg_out, qr/Line exceeds 80 characters/,  'Negative test detects >80 char prose line' );
        like( $neg_out, qr/exclude ACTION_LOGBOOK\.md and RCA_REGISTER\.md via exclude_docs/, 'Negative test detects missing exclude_docs' );
        like( $neg_out, qr/must not enable 'pymdownx\.snippets'/, 'Negative test detects disallowed pymdownx.snippets' );
    }
};

# ===========================================================================
# Subtest 3: build/mkdocs_hooks.py unit tests
# ===========================================================================
subtest 'Subtest 3: build/mkdocs_hooks.py unit tests' => sub {
    my $hooks_file = File::Spec->catfile( $PROJECT_ROOT, 'build', 'mkdocs_hooks.py' );
    ok( -f $hooks_file, 'build/mkdocs_hooks.py exists' );
    ok( has_lf_only($hooks_file), 'build/mkdocs_hooks.py uses Unix LF line endings' );

  SKIP: {
        skip 'python3 required to execute build/mkdocs_hooks.py tests', 3 unless defined $PYTHON_BIN;

        my $tmp_pyc_dir = tempdir( CLEANUP => 1 );
        my $pyc_out     = File::Spec->catfile( $tmp_pyc_dir, 'mkdocs_hooks.pyc' );
        my $compile_py  = <<'PY';
import py_compile, sys
py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)
print("COMPILE_OK")
PY
        my ( $crc, $cout ) = run_py_script( $PYTHON_BIN, $compile_py, $hooks_file, $pyc_out );
        is( $crc, 0, "build/mkdocs_hooks.py compiles cleanly: $cout" );

        my $py_hooks = <<'PY';
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "build"))
import mkdocs_hooks as hooks

# 1. semver_key descending sort
versions = ["v2.8.41.md", "v2.10.0.md", "v2.9.4.md", "v1.9.9.md"]
desc = sorted(versions, key=hooks.semver_key, reverse=True)
assert desc == ["v2.10.0.md", "v2.9.4.md", "v2.8.41.md", "v1.9.9.md"], desc

# 2. sanitize_legacy_markdown without modifying disk releases/v*.md
rel_files = sorted((root / "releases").glob("v*.md"))
assert rel_files, "releases/v*.md must exist"
pre_hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in rel_files}

sample = (
    "See [script](file:///home/jmren/GIT_REPOS/MySQLTuner-perl/mysqltuner.pl) "
    "and [changelog](../Changelog) and [sibling](v2.9.3.md) "
    "and [docs](../docs/index.md) and `[code](file:///secret)`.\n\n"
    "```markdown\n[fenced](file:///unchanged)\n```\n"
)
sanitized = hooks.sanitize_legacy_markdown(sample, rel_source_dir="releases")
assert "https://github.com/major/MySQLTuner-perl/blob/master/mysqltuner.pl" in sanitized, sanitized
assert "https://github.com/major/MySQLTuner-perl/blob/master/Changelog" in sanitized, sanitized
assert "[sibling](v2.9.3.md)" in sanitized, sanitized
assert "[docs](../docs/index.md)" in sanitized, sanitized
assert "`[code](file:///secret)`" in sanitized, sanitized
assert "[fenced](file:///unchanged)" in sanitized, sanitized

# 3. on_page_markdown token expansions
cfg = {"docs_dir": str(root / "docs")}
curr_ver = (root / "CURRENT_VERSION.txt").read_text(encoding="utf-8").strip()
rendered_ver = hooks.on_page_markdown(
    "Version: <!-- CURRENT_VERSION --> and `<!-- CURRENT_VERSION -->`",
    None,
    cfg,
    [],
)
assert f"Version: {curr_ver} and `<!-- CURRENT_VERSION -->`" == rendered_ver, rendered_ver

table_md = hooks.on_page_markdown("<!-- AUTO_RELEASES_TABLE -->", None, cfg, [])
assert "| Version | Release Date | Release Notes |" in table_md, table_md
assert f"[v{curr_ver}](v{curr_ver}.md)" in table_md, table_md

for allowed in ("mysql_support.md", "mariadb_support.md", "FEATURES.md", "USAGE.md", "SECURITY.md"):
    inc_md = hooks.on_page_markdown(f"<!-- INCLUDE_SOURCE: {allowed} -->", None, cfg, [])
    assert len(inc_md.strip()) > 40, f"empty include for {allowed}"
    assert not inc_md.lstrip().startswith("# "), f"leading H1 not stripped for {allowed}"

# 4. Path traversal and non-whitelisted INCLUDE_SOURCE rejection
for bad_target in (
    "../etc/passwd",
    "../../mysqltuner.pl",
    "mysqltuner.pl",
    "README.md",
    "docs/index.md",
    "./SECURITY.md",
):
    raised = False
    try:
        hooks.on_page_markdown(f"<!-- INCLUDE_SOURCE: {bad_target} -->", None, cfg, [])
    except ValueError:
        raised = True
    assert raised, f"Expected ValueError for disallowed INCLUDE_SOURCE '{bad_target}'"

# 5. on_config registers virtual release pages into nav without modifying disk
nav_cfg = {
    "docs_dir": str(root / "docs"),
    "nav": [{"Reference": [{"Releases Archive": ["03-reference/releases/index.md"]}]}],
}
hooks.on_config(nav_cfg)
archive_nav = nav_cfg["nav"][0]["Reference"][0]["Releases Archive"]
assert any(
    isinstance(item, dict) and f"03-reference/releases/v{curr_ver}.md" in item.values()
    for item in archive_nav
), archive_nav

post_hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in rel_files}
assert pre_hashes == post_hashes, "releases/v*.md must remain unmodified on disk"

print("HOOKS_UNIT_OK")
PY
        my ( $hrc, $hout ) = run_py_script( $PYTHON_BIN, $py_hooks, $PROJECT_ROOT );
        is( $hrc, 0, "mkdocs_hooks.py unit suite exited 0: $hout" );
        like( $hout, qr/HOOKS_UNIT_OK/, 'All mkdocs_hooks.py assertions passed' );
    }
};

# ===========================================================================
# Subtest 4: GitHub Actions workflows YAML, 40-char SHA pinning, and deploy guards
# ===========================================================================
subtest 'Subtest 4: GitHub Actions workflows SHA pinning and deploy guards' => sub {
    my $ci_wf     = File::Spec->catfile( $PROJECT_ROOT, '.github', 'workflows', 'docs-ci.yml' );
    my $deploy_wf = File::Spec->catfile( $PROJECT_ROOT, '.github', 'workflows', 'docs-deploy.yml' );

    ok( -f $ci_wf,                '.github/workflows/docs-ci.yml exists' );
    ok( has_lf_only($ci_wf),      'docs-ci.yml uses Unix LF line endings' );
    ok( -f $deploy_wf,            '.github/workflows/docs-deploy.yml exists' );
    ok( has_lf_only($deploy_wf),  'docs-deploy.yml uses Unix LF line endings' );

  SKIP: {
        skip 'Python3 with PyYAML required for workflow YAML validation', 2 unless $HAS_YAML;

        my $py_wf = <<'PY';
import pathlib
import re
import sys
import yaml

root = pathlib.Path(sys.argv[1])
sha_re = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[0-9a-f]{40}$")

def collect_uses(node, found):
    if isinstance(node, dict):
        if "uses" in node:
            found.append(str(node["uses"]))
        for v in node.values():
            collect_uses(v, found)
    elif isinstance(node, list):
        for item in node:
            collect_uses(item, found)

ci_path = root / ".github" / "workflows" / "docs-ci.yml"
deploy_path = root / ".github" / "workflows" / "docs-deploy.yml"

ci = yaml.safe_load(ci_path.read_text(encoding="utf-8"))
deploy = yaml.safe_load(deploy_path.read_text(encoding="utf-8"))

assert isinstance(ci, dict) and "jobs" in ci, "docs-ci.yml missing jobs"
assert isinstance(deploy, dict) and "jobs" in deploy, "docs-deploy.yml missing jobs"
assert ci.get("permissions", {}).get("contents") == "read", "docs-ci must enforce contents: read"

for wf_name, wf_data in (("docs-ci.yml", ci), ("docs-deploy.yml", deploy)):
    uses_list = []
    collect_uses(wf_data, uses_list)
    assert len(uses_list) >= 3, f"{wf_name} expected >=3 uses entries"
    for ref in uses_list:
        assert sha_re.match(ref), f"{wf_name} uses unpinned action '{ref}'"

ci_on = ci.get("on") if "on" in ci else ci.get(True, {})
assert isinstance(ci_on, dict), "docs-ci.yml missing on: trigger"
required_ci_paths = (
    ".github/workflows/docs-deploy.yml",
    "tests/unit_mkdocs_diataxis.t",
    "tests/unit_docs_tutorials_howtos.t",
    "tests/unit_docs_tutorials_howtos.py",
)
for trigger in ("pull_request", "push"):
    trig_paths = ci_on.get(trigger, {}).get("paths", [])
    assert isinstance(trig_paths, list), f"docs-ci.yml {trigger}.paths missing"
    for req_p in required_ci_paths:
        assert req_p in trig_paths, f"docs-ci.yml {trigger}.paths missing {req_p}"

ci_steps = ci["jobs"]["docs-quality"]["steps"]
ci_runs = "\n".join(str(s.get("run", "")) for s in ci_steps)
assert "build/check_diataxis_docs.py docs --strict --mkdocs-config mkdocs.yml" in ci_runs, (
    "docs-ci must run check_diataxis_docs.py with --mkdocs-config mkdocs.yml"
)
assert "mkdocs build --strict" in ci_runs, "docs-ci must run mkdocs build --strict"
assert "prove -v tests/unit_mkdocs_diataxis.t tests/unit_docs_tutorials_howtos.t" in ci_runs, (
    "docs-ci must run prove -v tests/unit_mkdocs_diataxis.t tests/unit_docs_tutorials_howtos.t"
)
assert any(
    "markdownlint-cli2-action@" in str(s.get("uses", ""))
    for s in ci_steps
), "docs-ci must run markdownlint-cli2-action"
assert any(
    str(s.get("uses", "")).startswith("vale-cli/vale-action@")
    for s in ci_steps
), "docs-ci must run vale-cli/vale-action"

deploy_on = deploy.get("on") if "on" in deploy else deploy.get(True, {})
assert isinstance(deploy_on, dict), "docs-deploy.yml missing on: trigger"
deploy_push_paths = deploy_on.get("push", {}).get("paths", [])
assert isinstance(deploy_push_paths, list) and len(deploy_push_paths) > 0, (
    "docs-deploy.yml on.push must define non-empty paths: filter"
)

assert deploy.get("concurrency", {}).get("group") == "docs-deploy", "docs-deploy concurrency group missing"
assert deploy.get("concurrency", {}).get("cancel-in-progress") is False, "cancel-in-progress must be false"

verify_job = deploy["jobs"]["verify"]
assert verify_job.get("permissions", {}).get("contents") == "read", "verify job needs contents: read"

deploy_job = deploy["jobs"]["deploy"]
assert deploy_job.get("needs") == "verify", "deploy job must depend on verify"
assert (
    deploy_job.get("if") == "github.repository == 'jmrenouard/MySQLTuner-perl'"
), f"deploy repo guard mismatch: {deploy_job.get('if')}"
assert deploy_job.get("permissions", {}).get("contents") == "write", "deploy job needs contents: write"

steps = deploy_job["steps"]
check_creds = next((s for s in steps if s.get("id") == "check_creds"), None)
assert check_creds is not None, "check_creds step missing"
creds_run = str(check_creds.get("run", ""))
for secret_var in ("IONOS_FTP_SERVER", "IONOS_FTP_USERNAME", "IONOS_FTP_PASSWORD", "IONOS_REMOTE_PATH"):
    assert secret_var in str(check_creds.get("env", {})), f"{secret_var} missing in check_creds env"
    assert not re.search(rf"\becho\b.*{secret_var}", creds_run), f"check_creds echoes {secret_var}"
    assert not re.search(rf"\bprintf\b.*{secret_var}", creds_run), f"check_creds prints {secret_var}"

all_deploy_runs = "\n".join(str(s.get("run", "")) for s in steps)
assert 'VERSION="dev"' in all_deploy_runs, "dev version handling missing"
assert "latest" in all_deploy_runs, "latest alias handling missing"
assert "RELEASE_TAG#v" in all_deploy_runs, "release version tag handling missing"
assert "mike deploy --branch docs-site" in all_deploy_runs, "mike deploy command missing"
assert "mike set-default --branch docs-site" in all_deploy_runs, "mike set-default command missing"
assert "git fetch origin +refs/heads/docs-site:refs/heads/docs-site" in all_deploy_runs, "idempotent docs-site fetch missing"
assert "cp build/docs_htaccess _site_deploy/.htaccess" in all_deploy_runs, ".htaccess staging missing"

sftp_steps = [
    s for s in steps
    if str(s.get("uses", "")).startswith("wlixcc/SFTP-Deploy-Action@")
]
assert len(sftp_steps) == 2, f"expected 2 SFTP-Deploy-Action steps (site + .htaccess), got {len(sftp_steps)}"
local_paths = [s.get("with", {}).get("local_path") for s in sftp_steps]
assert "./_site_deploy/" in local_paths, "site SFTP deploy step missing"
assert "./_site_deploy/.htaccess" in local_paths, "explicit .htaccess SFTP deploy step missing"
for s in sftp_steps:
    w = s.get("with", {})
    assert w.get("sftp_only") is True, "SFTP deploy must set sftp_only: true"
    assert "IONOS_REMOTE_PATH" in str(w.get("remote_path", "")), "remote_path must use IONOS_REMOTE_PATH"

print("WORKFLOWS_OK")
PY

        my ( $wrc, $wout ) = run_py_script( $PYTHON_BIN, $py_wf, $PROJECT_ROOT );
        is( $wrc, 0, "GitHub Actions workflows validation exited 0: $wout" );
        like( $wout, qr/WORKFLOWS_OK/, 'All CI/deploy workflow assertions passed' );
    }
};

# ===========================================================================
# Subtest 5: build/docs_htaccess static routing and security directives
# ===========================================================================
subtest 'Subtest 5: build/docs_htaccess routing and security directives' => sub {
    my $htaccess_path = File::Spec->catfile( $PROJECT_ROOT, 'build', 'docs_htaccess' );
    ok( -f $htaccess_path, 'build/docs_htaccess exists' );
    my $raw = slurp_raw($htaccess_path);

    my $active = join "\n", grep { !/^\s*#/ } split /\n/, $raw;

    like( $active, qr/^\s*DirectoryIndex\s+index\.html\b/m, 'Sets DirectoryIndex index.html' );
    like( $active, qr/^\s*Options\s+[^\n]*-Indexes\b/m,    'Disables directory listing via Options -Indexes' );
    like( $active, qr/^\s*ErrorDocument\s+404\s+\/latest\/404\.html\b/m, 'Configures 404 page at /latest/404.html' );
    like( $active, qr/RewriteEngine\s+On/i,                 'Enables mod_rewrite' );
    like( $active, qr/RewriteCond\s+%\{HTTPS\}\s+!=on/,     'Redirects HTTP to HTTPS' );
    like(
        $active,
        qr{RewriteRule\s+\^\s+https://%\{HTTP_HOST\}%\{REQUEST_URI\}\s+\[R=301,L\]},
        'Preserves HTTP_HOST on HTTPS redirect without forcing www.'
    );
    unlike( $active, qr/\bwww\./i,                          'Does not force www. redirect' );
    unlike( $active, qr/index\.php/i,                       'Contains no legacy index.php directives' );
    like( $active, qr/Strict-Transport-Security/,           'Sets Strict-Transport-Security header' );
    like( $active, qr/X-Content-Type-Options\s+"nosniff"/,  'Sets X-Content-Type-Options nosniff' );
    like( $active, qr/X-Frame-Options\s+"SAMEORIGIN"/,      'Sets X-Frame-Options SAMEORIGIN' );
    like( $active, qr/<Files\s+"versions\.json">[\s\S]*?no-cache/m, 'Disables caching on versions.json' );
    like( $active, qr/<Files\s+"index\.html">[\s\S]*?no-cache/m, 'Disables caching on index.html via <Files>' );
    unlike( $active, qr/<If\s+/i, 'Avoids <If> expression blocks for shared Apache AllowOverride compatibility' );
};

# ===========================================================================
# Subtest 6: Live mkdocs build --strict smoke test (graceful skip in chroot)
# ===========================================================================
subtest 'Subtest 6: Live mkdocs build --strict smoke test' => sub {
    my $venv_mkdocs = File::Spec->catfile( $PROJECT_ROOT, '.venv-docs', 'bin', 'mkdocs' );
    my $mkdocs_bin  = ( -f $venv_mkdocs && -x $venv_mkdocs ) ? $venv_mkdocs : has_binary('mkdocs');

  SKIP: {
        skip 'mkdocs not available in test environment (chroot/sbuild safe skip)', 11 unless defined $mkdocs_bin;

        my $tmp_site = tempdir( CLEANUP => 1 );
        my $config   = File::Spec->catfile( $PROJECT_ROOT, 'mkdocs.yml' );

        local $ENV{NO_MKDOCS_2_WARNING} = '1';
        my $out = qx("$mkdocs_bin" build --strict --config-file "$config" --site-dir "$tmp_site" 2>&1);
        my $rc  = $? >> 8;

        is( $rc, 0, "mkdocs build --strict exits 0: $out" );
        unlike( $out, qr/^(?:WARNING|ERROR)\s+-/m, 'mkdocs build --strict emits zero WARNING/ERROR lines' );

        my @expected_pages = (
            'index.html',
            File::Spec->catfile( '01-tutorials',     'index.html' ),
            File::Spec->catfile( '02-how-to-guides', 'index.html' ),
            File::Spec->catfile( '03-reference',     'index.html' ),
            File::Spec->catfile( '04-explanation',   'index.html' ),
            File::Spec->catfile( '03-reference',     'releases', 'index.html' ),
            File::Spec->catfile( '03-reference',     'releases', 'v2.9.4', 'index.html' ),
        );

        for my $page (@expected_pages) {
            my $target = File::Spec->catfile( $tmp_site, $page );
            ok( -f $target && -s $target > 0, "Built page exists and is non-empty: $page" );
        }

        my $home_html = slurp_raw( File::Spec->catfile( $tmp_site, 'index.html' ) );
        my $rel_html  = slurp_raw( File::Spec->catfile( $tmp_site, '03-reference', 'releases', 'index.html' ) );
        my $curr_ver  = slurp_raw( File::Spec->catfile( $PROJECT_ROOT, 'CURRENT_VERSION.txt' ) );
        $curr_ver =~ s/^\s+|\s+$//g;

        like( $home_html, qr/\Q$curr_ver\E/, 'Root index.html renders CURRENT_VERSION value' );
        unlike(
            $home_html . $rel_html,
            qr/<!--\s*(?:CURRENT_VERSION|AUTO_RELEASES_TABLE|INCLUDE_SOURCE:)/,
            'No unexpanded hook tokens remain in built HTML'
        );
    }
};

done_testing();
