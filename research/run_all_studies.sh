#!/bin/bash
# Master runner: re-run all research studies
# Uses xargs -P for reliable parallel execution
CD="/var/www/trading-bots/btc-spot-dev"
LOG="$CD/research/results/run_logs"
mkdir -p "$LOG"

run_one() {
    local script="$1"
    local name=$(basename "$script" .py)
    echo "[$(date +%H:%M:%S)] START $name" >> "$LOG/master.log"
    if python3 "$CD/research/$script" > "$LOG/${name}.log" 2>&1; then
        echo "[$(date +%H:%M:%S)] DONE  $name" >> "$LOG/master.log"
    else
        echo "[$(date +%H:%M:%S)] FAIL  $name (rc=$?)" >> "$LOG/master.log"
    fi
}
export -f run_one
export CD LOG

echo "============================================" > "$LOG/master.log"
echo " RE-RUN ALL RESEARCH STUDIES" >> "$LOG/master.log"
echo " Started: $(date)" >> "$LOG/master.log"
echo "============================================" >> "$LOG/master.log"

# ── Batch 0: Quick (no bootstrap) ──
echo "" >> "$LOG/master.log"
echo "── Batch 0: Quick scripts ──" >> "$LOG/master.log"
printf '%s\n' \
    monthly_pnl.py \
    benchmark_compare.py \
    rcssb_diagnostics.py \
    vtrend_postmortem.py \
| xargs -P 4 -I{} bash -c 'run_one "$@"' _ {}

# ── Batch 1: Medium (500 paths, ~5 min each) ──
echo "" >> "$LOG/master.log"
echo "── Batch 1: Medium (500 paths) ──" >> "$LOG/master.log"
printf '%s\n' \
    creative_exploration.py \
    config_compare.py \
    trail_sweep.py \
    ema_ablation.py \
    ema_regime_fine.py \
    vtrend_param_sensitivity.py \
    multicoin_ema_regime.py \
    multicoin_200v120.py \
    multicoin_exit_variants.py \
    multicoin_diversification.py \
    e5r_test.py \
    e5_vcbb_test.py \
| xargs -P 4 -I{} bash -c 'run_one "$@"' _ {}

# ── Batch 2: Heavy (2000 paths, ~20 min each) ──
echo "" >> "$LOG/master.log"
echo "── Batch 2: Heavy (2000 paths) ──" >> "$LOG/master.log"
printf '%s\n' \
    timescale_robustness.py \
    v8_vs_vtrend_bootstrap.py \
    position_sizing.py \
    regime_sizing.py \
    cost_study.py \
    vexit_study.py \
    pe_study.py \
    pe_study_v2.py \
    e5_validation.py \
    validate_bootstrap.py \
    vcbb_vs_uniform.py \
    bootstrap_regime.py \
    binomial_correction.py \
    ema_regime_sweep.py \
    d1_ema200_filter.py \
    vdo_standalone_test.py \
| xargs -P 4 -I{} bash -c 'run_one "$@"' _ {}

# ── Batch 3: Very heavy (multi-phase, 30-60 min) ──
echo "" >> "$LOG/master.log"
echo "── Batch 3: Very heavy ──" >> "$LOG/master.log"
printf '%s\n' \
    pullback_strategy.py \
    vbreak_test.py \
    vcusum_test.py \
    vtwin_test.py \
    resolution_sweep.py \
    e6_staleness_study.py \
    e7_study.py \
| xargs -P 4 -I{} bash -c 'run_one "$@"' _ {}

# ── Batch 4: Heaviest (10K paths/perms) ──
echo "" >> "$LOG/master.log"
echo "── Batch 4: Heaviest ──" >> "$LOG/master.log"
printf '%s\n' \
    exit_family_study.py \
    multiple_comparison.py \
    true_wfo_compare.py \
| xargs -P 3 -I{} bash -c 'run_one "$@"' _ {}

# ── Batch 5: Meta-analysis (depends on above) ──
echo "" >> "$LOG/master.log"
echo "── Batch 5: Meta-analysis ──" >> "$LOG/master.log"
printf '%s\n' \
    roadmap_diagnostic.py \
    audit_phase1_3.py \
    audit_phase4.py \
| xargs -P 3 -I{} bash -c 'run_one "$@"' _ {}

# ── Summary ──
echo "" >> "$LOG/master.log"
echo "============================================" >> "$LOG/master.log"
echo " COMPLETE: $(date)" >> "$LOG/master.log"
PASSED=$(grep -c "^.* DONE" "$LOG/master.log" || true)
FAILED=$(grep -c "^.* FAIL" "$LOG/master.log" || true)
echo " Passed: $PASSED  Failed: $FAILED" >> "$LOG/master.log"
echo "============================================" >> "$LOG/master.log"

if [ "$FAILED" -gt 0 ]; then
    echo "" >> "$LOG/master.log"
    echo "FAILED scripts:" >> "$LOG/master.log"
    grep "FAIL" "$LOG/master.log" | grep -v "^FAILED" >> "$LOG/master.log" || true
fi

echo "DONE" >> "$LOG/master.log"
