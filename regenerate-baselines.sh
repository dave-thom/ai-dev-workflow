#!/usr/bin/env bash
# Regenerate baseline fixtures for Phase 9

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_PLATFORM="$SCRIPT_DIR"
BASELINE_DIR="$AI_PLATFORM/tests/fixtures/ai-role-baseline"

echo "Regenerating baseline fixtures in $BASELINE_DIR"

# Regenerate OpenCode baselines
echo "Generating baseline for o-dev: opencode implementer -m openrouter/deepseek/deepseek-v3.2"
(cd "$AI_PLATFORM" && AI_ROLE_DRYRUN=1 ./bin/ai-role opencode implementer -m openrouter/deepseek/deepseek-v3.2) > "$BASELINE_DIR/o-dev.txt"

echo "Generating baseline for o-debug: opencode debugger -m openrouter/deepseek/deepseek-v3.2"
(cd "$AI_PLATFORM" && AI_ROLE_DRYRUN=1 ./bin/ai-role opencode debugger -m openrouter/deepseek/deepseek-v3.2) > "$BASELINE_DIR/o-debug.txt"

echo "Generating baseline for o-git: opencode git -m openrouter/deepseek/deepseek-v4-flash"
(cd "$AI_PLATFORM" && AI_ROLE_DRYRUN=1 ./bin/ai-role opencode git -m openrouter/deepseek/deepseek-v4-flash) > "$BASELINE_DIR/o-git.txt"

echo "Generating baseline for o-sdebug: opencode debugger -m openrouter/deepseek/deepseek-v4-pro"
(cd "$AI_PLATFORM" && AI_ROLE_DRYRUN=1 ./bin/ai-role opencode debugger -m openrouter/deepseek/deepseek-v4-pro) > "$BASELINE_DIR/o-sdebug.txt"

echo "Generating baseline for o-devr1: opencode implementer -m openrouter/deepseek/deepseek-v4-pro"
(cd "$AI_PLATFORM" && AI_ROLE_DRYRUN=1 ./bin/ai-role opencode implementer -m openrouter/deepseek/deepseek-v4-pro) > "$BASELINE_DIR/o-devr1.txt"

echo "Generating baseline for o-sdev: opencode implementer -m openrouter/deepseek/deepseek-v4-pro"
(cd "$AI_PLATFORM" && AI_ROLE_DRYRUN=1 ./bin/ai-role opencode implementer -m openrouter/deepseek/deepseek-v4-pro) > "$BASELINE_DIR/o-sdev.txt"

echo ""
echo "Verifying baselines don't contain --auto:"

for file in "$BASELINE_DIR"/o-*.txt; do
    filename=$(basename "$file")
    if grep -q -- "--auto" "$file"; then
        echo "ERROR: $filename baseline contains --auto"
        exit 1
    fi
    echo "  ✓ $filename: no --auto"
done

echo ""
echo "All baselines regenerated successfully!"