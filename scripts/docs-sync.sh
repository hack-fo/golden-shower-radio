#!/usr/bin/env bash
# docs-sync.sh — re-publish the repo documentation to the GitHub Wiki.
#
# The canonical docs live in the repo (README.md, docs/ARCHITECTURE.md,
# docs/components/*.md). The GitHub Wiki is a generated mirror. Run this after
# any docs change to keep the wiki in sync. Idempotent: a no-op if nothing changed.
#
# Usage:  bash scripts/docs-sync.sh [--dry-run]
# Requires: gh (authenticated with `repo` scope), git.
set -euo pipefail

REPO_SLUG="hack-fo/golden-shower-radio"
WIKI_URL_PATH="${REPO_SLUG}.wiki.git"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WIKI_DIR="$(mktemp -d)"
DRY_RUN="${1:-}"

cleanup() { rm -rf "$WIKI_DIR"; }
trap cleanup EXIT

# docs/components/<slug>.md  ->  <Wiki-Page>.md  (hyphens render as spaces in titles)
declare -A PAGES=(
  [acquisition]=Acquisition
  [analysis]=Analysis
  [curation-director]=Curation-Director
  [enrichment]=Enrichment
  [knowledge-research]=Knowledge-Research
  [library-ingestion]=Library-Ingestion
  [persistence]=Persistence
  [playout]=Playout
  [runtime-config]=Runtime-Config
  [voice-talk]=Voice-Talk
  [website]=Website
)

token="$(gh auth token)"
git clone -q "https://x-access-token:${token}@github.com/${WIKI_URL_PATH}" "$WIKI_DIR"

cp "$PROJECT_DIR/docs/ARCHITECTURE.md" "$WIKI_DIR/Architecture.md"
cp "$PROJECT_DIR/docs/Home.md" "$WIKI_DIR/Home.md"
for slug in "${!PAGES[@]}"; do
  cp "$PROJECT_DIR/docs/components/${slug}.md" "$WIKI_DIR/${PAGES[$slug]}.md"
done

cd "$WIKI_DIR"
git add -A
if git diff --cached --quiet; then
  echo "docs-sync: wiki already up to date — nothing to publish."
  exit 0
fi
if [[ "$DRY_RUN" == "--dry-run" ]]; then
  echo "docs-sync: --dry-run — would publish these changes:"
  git diff --cached --stat
  exit 0
fi
git -c user.name=charlie -c user.email=guscha@gmail.com \
  commit -q -m "docs(wiki): sync architecture + subsystem pages from repo docs"
git push -q origin master
echo "docs-sync: wiki published."
