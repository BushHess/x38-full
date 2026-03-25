#!/usr/bin/env bash
# reproduce_v10_full_backtest.sh
# Runs V10 baseline backtest across 3 cost scenarios (smart/base/harsh).
# Output: v10_full_backtest_summary.csv + v10_repro_run.log
#
# PASS criteria: run twice → diff <= 1e-9 on all numeric fields.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG="$OUTDIR/v10_repro_run.log"

echo "================================================================" | tee "$LOG"
echo "  V10 REPRO RUN — $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a "$LOG"
echo "================================================================" | tee -a "$LOG"
echo "Project root: $PROJECT_ROOT" | tee -a "$LOG"
echo "Output dir:   $OUTDIR" | tee -a "$LOG"
echo "Git commit:   $(cd "$PROJECT_ROOT" && git rev-parse HEAD 2>/dev/null || echo 'N/A')" | tee -a "$LOG"
echo "" | tee -a "$LOG"

cd "$PROJECT_ROOT"

# --- Run 1 ---
echo "[RUN 1] Starting..." | tee -a "$LOG"
python3 "$SCRIPT_DIR/reproduce_v10_full_backtest.py" 2>&1 | tee -a "$LOG"
cp "$OUTDIR/v10_full_backtest_summary.csv" "$OUTDIR/v10_full_backtest_summary_run1.csv"
echo "" | tee -a "$LOG"

# --- Run 2 ---
echo "[RUN 2] Starting (determinism check)..." | tee -a "$LOG"
python3 "$SCRIPT_DIR/reproduce_v10_full_backtest.py" 2>&1 | tee -a "$LOG"
cp "$OUTDIR/v10_full_backtest_summary.csv" "$OUTDIR/v10_full_backtest_summary_run2.csv"
echo "" | tee -a "$LOG"

# --- Diff check ---
echo "================================================================" | tee -a "$LOG"
echo "  DETERMINISM CHECK" | tee -a "$LOG"
echo "================================================================" | tee -a "$LOG"

DIFF_OUTPUT=$(diff "$OUTDIR/v10_full_backtest_summary_run1.csv" \
                   "$OUTDIR/v10_full_backtest_summary_run2.csv" || true)

if [ -z "$DIFF_OUTPUT" ]; then
    echo "PASS: Run 1 and Run 2 are IDENTICAL (byte-for-byte)." | tee -a "$LOG"
    VERDICT="PASS"
else
    echo "FAIL: Differences detected between Run 1 and Run 2:" | tee -a "$LOG"
    echo "$DIFF_OUTPUT" | tee -a "$LOG"
    VERDICT="FAIL"
fi

# Cleanup temp files
rm -f "$OUTDIR/v10_full_backtest_summary_run1.csv" \
      "$OUTDIR/v10_full_backtest_summary_run2.csv"

echo "" | tee -a "$LOG"
echo "================================================================" | tee -a "$LOG"
echo "  VERDICT: $VERDICT" | tee -a "$LOG"
echo "  Log: $LOG" | tee -a "$LOG"
echo "  CSV: $OUTDIR/v10_full_backtest_summary.csv" | tee -a "$LOG"
echo "================================================================" | tee -a "$LOG"

if [ "$VERDICT" = "FAIL" ]; then
    exit 1
fi
