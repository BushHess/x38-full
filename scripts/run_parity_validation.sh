#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# PARITY VALIDATION: Run validation framework (all suites) for 6 strategies
# ═══════════════════════════════════════════════════════════════════════════
#
# Strategies: E0, E5, SM, LATCH, E0_ema21D1, E5_ema21D1
# Baseline: E0 (vtrend) for all comparisons
# Suite: all (13 suites + trade_level + dd_episodes + overlay)
#
# Usage: bash run_parity_validation.sh [strategy_name]
#   No argument = run all 6.
#   strategy_name = run just one (e.g. "vtrend_e5")
#

set -euo pipefail
cd "$(dirname "$0")"

BASELINE="vtrend"
BASELINE_CONFIG="configs/vtrend/vtrend_default.yaml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_BASE="results/parity_${TIMESTAMP}"

declare -A STRATEGIES
STRATEGIES[vtrend]="configs/vtrend/vtrend_default.yaml"
STRATEGIES[vtrend_e5]="configs/vtrend_e5/vtrend_e5_default.yaml"
STRATEGIES[vtrend_sm]="configs/vtrend_sm/vtrend_sm_default.yaml"
STRATEGIES[latch]="configs/latch/latch_default.yaml"
STRATEGIES[vtrend_ema21]="configs/vtrend_ema21/vtrend_ema21_default.yaml"
STRATEGIES[vtrend_ema21_d1]="configs/vtrend_ema21_d1/vtrend_ema21_d1_default.yaml"

# If argument provided, only run that one
if [ $# -ge 1 ]; then
    TARGET="$1"
    if [ -z "${STRATEGIES[$TARGET]+x}" ]; then
        echo "ERROR: Unknown strategy '$TARGET'"
        echo "Known: ${!STRATEGIES[@]}"
        exit 1
    fi
    STRATEGY_LIST=("$TARGET")
else
    STRATEGY_LIST=(vtrend vtrend_e5 vtrend_sm latch vtrend_ema21 vtrend_ema21_d1)
fi

mkdir -p "$RESULTS_BASE"

echo "═══════════════════════════════════════════════════════════════"
echo "  PARITY VALIDATION — ${#STRATEGY_LIST[@]} strategies"
echo "  Baseline: $BASELINE"
echo "  Output: $RESULTS_BASE"
echo "═══════════════════════════════════════════════════════════════"

for STRAT in "${STRATEGY_LIST[@]}"; do
    CONFIG="${STRATEGIES[$STRAT]}"
    OUTDIR="${RESULTS_BASE}/eval_${STRAT}_vs_e0"

    echo ""
    echo "────────────────────────────────────────────────────────────"
    echo "  [$STRAT] Starting validation (suite=all)"
    echo "  Config: $CONFIG"
    echo "  Output: $OUTDIR"
    echo "────────────────────────────────────────────────────────────"

    START_T=$(date +%s)

    python -m validation.cli \
        --strategy "$STRAT" \
        --baseline "$BASELINE" \
        --config "$CONFIG" \
        --baseline-config "$BASELINE_CONFIG" \
        --out "$OUTDIR" \
        --suite all \
        --bootstrap 2000 \
        --force \
        --trade-level on \
        --dd-episodes on \
        --overlay-test on \
        --selection-bias deflated \
        --sensitivity-grid \
        2>&1 | tee "${OUTDIR}/run_stdout.log" || true

    END_T=$(date +%s)
    ELAPSED=$(( END_T - START_T ))
    echo "  [$STRAT] Completed in ${ELAPSED}s"
    echo ""
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  PARITY VALIDATION COMPLETE"
echo "  Results: $RESULTS_BASE"
echo "═══════════════════════════════════════════════════════════════"

# Print summary
echo ""
echo "SUMMARY:"
for STRAT in "${STRATEGY_LIST[@]}"; do
    OUTDIR="${RESULTS_BASE}/eval_${STRAT}_vs_e0"
    if [ -f "${OUTDIR}/reports/decision.json" ]; then
        TAG=$(python -c "import json; d=json.load(open('${OUTDIR}/reports/decision.json')); print(d.get('tag','?'))" 2>/dev/null || echo "ERROR")
        echo "  $STRAT: $TAG"
    else
        echo "  $STRAT: NO OUTPUT"
    fi
done
