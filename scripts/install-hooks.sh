#!/bin/sh
# install-hooks.sh — installs QAP git hooks into .git/hooks/
# Run once after cloning: ./scripts/install-hooks.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="${REPO_ROOT}/.git/hooks"
SOURCE_DIR="${REPO_ROOT}/automation/scripts"

install_hook() {
  name="$1"
  src="${SOURCE_DIR}/${name}"
  dst="${HOOKS_DIR}/${name}"

  if [ ! -f "$src" ]; then
    echo "⚠️  Hook source not found: $src"
    return
  fi

  cp "$src" "$dst"
  chmod +x "$dst"
  echo "✅  Installed ${name} → .git/hooks/${name}"
}

install_hook "pre-commit"

echo ""
echo "Git hooks installed. Every commit will now:"
echo "  1. Block .feature files without a matching .steps.ts"
echo "  2. Run Cucumber --dry-run to catch Undefined steps"
