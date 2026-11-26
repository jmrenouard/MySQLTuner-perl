# Publish Versioned Documentation

Refer to [Release Notes Archive](../../03-reference/releases/index.md) for
current release versions before you start this procedure.

## Preconditions

Before you start this procedure, make sure that these conditions apply:

1. Python 3.8 or a newer version and Git exist on your workstation.
2. You have `markdownlint-cli2` on your workstation if you execute local lint
   checks.
3. For manual GitHub Actions deployment, you have repository write access and
   IONOS SFTP secrets.

## Safety Precautions

**CAUTION:** Run `make docs-check` and `mkdocs build --strict` before you
publish a version. Broken relative links or incorrect `mike` aliases break
documentation navigation.

**NOTE:** The `mkdocs.yml` file sets `mike` to `alias_type: redirect` for a
static Apache web server.

## Procedure

### Step 1: Install Documentation Dependencies

1. Create a virtual environment and install the documentation packages:

   ```bash
   make docs-install
   ```

### Step 2: Validate Structure, Style, and Strict Build

1. Run the documentation structure and link check in strict mode:

   ```bash
   make docs-check
   ```

2. Run `markdownlint-cli2` across all Markdown pages:

   ```bash
   npx markdownlint-cli2 "docs/**/*.md"
   ```

3. Run the strict MkDocs build to validate hooks, release injection, and
   navigation:

   ```bash
   make docs-build
   ```

### Step 3: Preview Locally

1. Start the local preview server and examine changes in your browser:

   ```bash
   make docs-serve
   ```

2. Stop the preview server with `Ctrl+C` when your examination finishes.

### Step 4: Publish a Versioned Release

#### Option A: Publish via GitHub Actions

1. Open the GitHub Actions tab and select `.github/workflows/docs-deploy.yml`.

2. Start `workflow_dispatch` with target `version` (for example `2.9.4`),
   `alias` (`latest`), and `set_default`.

3. Set `dry_run` to `true` for a rehearsal, or set `false` to push `docs-site`
   and upload to IONOS.

#### Option B: Deploy Manually with `mike`

1. Fetch the `docs-site` branch from `origin` and build the new versioned
   directory:

   ```bash
   git fetch origin docs-site:docs-site || true
   mike deploy --branch docs-site --update-aliases 2.9.4 latest
   mike set-default --branch docs-site latest
   ```

2. Preview the versioned `mike` site locally before you push:

   ```bash
   mike serve --branch docs-site
   ```

3. Push the `docs-site` branch to `origin`:

   ```bash
   git push origin docs-site
   ```

## Verification

1. Make sure that `make docs-check` and `make docs-build` exit with code `0`.

2. Examine `versions.json` on `docs-site` and make sure that the new version and
   `latest` alias exist:

   ```bash
   git show docs-site:versions.json
   ```

3. Open the site URL and make sure that the version selector switches between
   versions cleanly.

## Rollback

If an active documentation version contains errors, restore the previous version
alias immediately:

1. Delete the broken version directory from the `docs-site` branch:

   ```bash
   mike delete --branch docs-site 2.9.4
   ```

2. Point the `latest` alias back to the previous healthy version (for example
   `2.9.3`):

   ```bash
   mike deploy --branch docs-site --update-aliases 2.9.3 latest
   mike set-default --branch docs-site latest
   git push origin docs-site
   ```

3. Run `.github/workflows/docs-deploy.yml` again with `workflow_dispatch` to
   synchronize the static IONOS host.

## Related Topics

- Reference: [Release Notes Archive](../../03-reference/releases/index.md)
- Explanation:
  [ADR-002: Versioned Docs](../../04-explanation/design-decisions/adr-002-versioned-documentation-architecture.md)
