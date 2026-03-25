# VP1 (VTREND-P1) — Frozen Spec Audit

## 1. Audit verdict
**FAIL** for the received prior spec pack **v1.0**.

Reason:
- the prior pack was close, but not yet clean enough for independent rebuild without guesswork.
- several rules were explicit but still not separated sharply enough from lineage or benchmark-wrapper behavior.
- a few critical items were not blocker-ambiguous in strategy logic, but were blocker-ambiguous in **implementation truth**.

After applying the mandatory patch set in this pack, the resulting **spec v1.1** is standalone and executable.

## 2. Section-by-section audit status

### 2.1 Identity audit
| Item | Status | Notes |
|---|---|---|
| VP1 provenance = performance-dominant leader | EXECUTABLE | matches Phase 1 artifact |
| VP1 parent core = standard ATR + reversal ON + D1 ON | EXECUTABLE | matches candidate artifact |
| VP1 ID/name consistency | AMBIGUOUS | `D1ON` vs `D1on` (legacy) |
| Mixing with Baseline / old MBR line | UNSUPPORTED | lineage was used as justification in several places |

### 2.2 Frozen-facts consistency audit
| Item | Status | Notes |
|---|---|---|
| standard ATR | EXECUTABLE | consistent |
| reversal ON | EXECUTABLE | consistent |
| D1 ON | EXECUTABLE | consistent |
| slow=140 | EXECUTABLE | consistent |
| trail=2.5 | EXECUTABLE | consistent |
| vdo_threshold=0.0 | EXECUTABLE | consistent |
| d1_ema_period=28 | EXECUTABLE | consistent |
| next-open event accounting | EXECUTABLE | consistent |
| prevday D1 only | EXECUTABLE | consistent |
| long-only | EXECUTABLE | consistent |
| binary sizing | EXECUTABLE | consistent |

### 2.3 Data-contract audit
| Item | Status | Notes |
|---|---|---|
| required H4 columns | EXECUTABLE | explicit enough |
| required D1 columns | EXECUTABLE | explicit enough |
| open_time vs close_time semantics | EXECUTABLE | explicit |
| timezone assumptions | EXECUTABLE | UTC explicit |
| duplicate bars | AMBIGUOUS | prior pack chose hard fail but did not mark it as forced resolution |
| structural gaps | AMBIGUOUS | same issue |
| zero/negative values | AMBIGUOUS | same issue |
| absent taker column | EXECUTABLE | fallback-only globally chosen |
| partial taker missing | AMBIGUOUS | VDO carry semantics not fully locked in v1.0 |
| H4/D1 join | EXECUTABLE | prevday join explicit |

### 2.4 Clock-and-causality audit
| Item | Status | Notes |
|---|---|---|
| decision timestamp | EXECUTABLE | explicit |
| fill timestamp | EXECUTABLE | explicit |
| fill price | EXECUTABLE | explicit |
| valuation timestamp | EXECUTABLE | explicit |
| indicator timing on bar i | EXECUTABLE | explicit |
| D1 prevday mapping | EXECUTABLE | explicit |
| same-day D1 forbidden | EXECUTABLE | explicit |
| lookahead risk | EXECUTABLE | no residual blocker found |

### 2.5 Indicator math audit
| Item | Status | Notes |
|---|---|---|
| EMA fast/slow formulas | EXECUTABLE | explicit |
| fast period rule | EXECUTABLE | explicit but lineage-derived |
| ATR exact formula / period / seed | EXECUTABLE | explicit but lineage-derived |
| VDO primary path | EXECUTABLE | explicit |
| VDO fallback path | EXECUTABLE | explicit |
| VDO EMA seed | AMBIGUOUS | NaN-carry edge behavior not fully locked in v1.0 |
| D1 EMA seed | EXECUTABLE | explicit |
| threshold comparisons | EXECUTABLE | explicit |
| equality handling | EXECUTABLE | explicit |
| zero-volume / high==low handling | AMBIGUOUS | needed stricter statement on VDO current-bar finiteness |
| first legal feature bar | EXECUTABLE | sufficient for rebuild |

### 2.6 State-machine audit
| Item | Status | Notes |
|---|---|---|
| FLAT / LONG states | EXECUTABLE | explicit |
| internal variables | EXECUTABLE | explicit |
| peak price update rule | EXECUTABLE | explicit |
| persist vs reset | EXECUTABLE | explicit |
| state update order | EXECUTABLE | explicit |
| EOF while LONG | CONTRADICTORY | prior pack did not separate intrinsic strategy vs wrapper behavior sharply enough |

### 2.7 Entry/exit logic audit
| Item | Status | Notes |
|---|---|---|
| entry completeness | EXECUTABLE | explicit |
| exit completeness | EXECUTABLE | explicit |
| reversal ON condition | EXECUTABLE | explicit |
| trailing stop formula | EXECUTABLE | explicit |
| peak uses close not high | EXECUTABLE | explicit |
| exit priority | EXECUTABLE | explicit |
| equality cases | EXECUTABLE | explicit |
| D1/VDO entry-only | EXECUTABLE | explicit but lineage-derived |

### 2.8 Accounting-and-cost audit
| Item | Status | Notes |
|---|---|---|
| binary sizing meaning | EXECUTABLE | explicit |
| buy accounting | EXECUTABLE | explicit |
| sell accounting | EXECUTABLE | explicit |
| round-trip vs per-side | EXECUTABLE | explicit |
| spread/slippage/fee boundary | CONTRADICTORY | prior pack did not isolate strategy cost vs benchmark cost sharply enough |
| terminal open position handling | CONTRADICTORY | same as EOF issue |

### 2.9 Warmup-and-eligibility audit
| Item | Status | Notes |
|---|---|---|
| warmup length | EXECUTABLE | explicit but lineage-derived |
| first legal signal formula | EXECUTABLE | sufficient |
| no_trade before warmup | EXECUTABLE | explicit |
| feature NaN gating | EXECUTABLE | explicit |

### 2.10 Reference-trace audit
| Item | Status | Notes |
|---|---|---|
| real artifact-backed timestamps/prices | EXECUTABLE | yes |
| indicator-value trace as frozen truth | UNSUPPORTED | old trace mixed in recomputed values not preserved in artifact |

### 2.11 Acceptance-test audit
| Item | Status | Notes |
|---|---|---|
| Tier-2 trade count / first 3 fills | EXECUTABLE | artifact-backed |
| VDO fallback checks | EXECUTABLE | can be deterministic |
| prevday D1 checks | EXECUTABLE | deterministic |
| candidate-vs-baseline divergence checkpoints | UNSUPPORTED as trade-level gate | aggregate Tier-2 relation exists; trade-level baseline log not shipped |
| full-history first legal trade checkpoints | UNSUPPORTED | not artifact-backed |

## 3. Audit conclusion
The prior spec pack v1.0 fails as the final implementation truth source.
The patched v1.1 in this pack resolves the blockers and is suitable as the canonical rebuild spec.
