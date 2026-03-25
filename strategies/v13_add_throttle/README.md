# v13_add_throttle

Intent:
- Preserve V10/V8 Apex entry alpha and exits.
- Add an adds-only throttle driven by rolling portfolio drawdown depth.

Invariants:
- First entry while flat is never throttled.
- Throttle applies only to the add-cap path (`max_add_per_bar` equivalent).
- No new indicators or entry signals are introduced.

Throttle:
- `dd_depth = 1 - nav / peak_nav`
- if flat: use `max_add_per_bar`
- if `dd_depth >= add_throttle_dd2`: allow add = `0`
- elif `dd_depth >= add_throttle_dd1`: allow add = `max_add_per_bar * add_throttle_mult`
- else: allow add = `max_add_per_bar`
