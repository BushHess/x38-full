# P0.2 Runtime Risk Tag Probe

## Verdict

- `PASS_RUNTIME_WARNING_PATH`
- Elapsed: `12.78s`

## Parity

- `X0`: fills=True, trades=True, summary=True, tag_match_rate=1.000
- `X0_E5EXIT`: fills=True, trades=True, summary=True, tag_match_rate=1.000

## Runtime Risk Distribution

- `X0` `low_non_chop`: trades=44, avg_pnl=2325.68 USD, net_pnl=102329.98 USD
- `X0` `medium_chop`: trades=78, avg_pnl=2137.34 USD, net_pnl=166712.57 USD
- `X0` `high_chop_stretch`: trades=52, avg_pnl=-631.73 USD, net_pnl=-32849.80 USD
- `X0_E5EXIT` `low_non_chop`: trades=52, avg_pnl=2725.42 USD, net_pnl=141721.82 USD
- `X0_E5EXIT` `medium_chop`: trades=80, avg_pnl=2082.73 USD, net_pnl=166618.55 USD
- `X0_E5EXIT` `high_chop_stretch`: trades=56, avg_pnl=-188.39 USD, net_pnl=-10549.89 USD

## Interpretation

- Warning-only runtime integration is feasible without changing fills or PnL.
- The simplest carrier is `entry_reason` tagging; no engine change is required for a research deployment.
- If production needs richer structured metadata later, that should be a separate engine/interface change.

## Recommendation

- Safe next step: optional risk-tag logging on `X0_E5EXIT` entry signals.
- Do not convert this into a hard gate by default.

