# D1b2 Report — Measurements: Volatility & Regime

## Volatility Channels

- Volatility clustering is real in all four timeframes. Absolute 1-bar return autocorrelation at lag 1 is 0.374 / 0.281 / 0.216 / 0.130 for 15m / 1h / 4h / 1d. The cleaner non-overlap-style persistence check, rv_42 at lag 42, is 0.661 / 0.576 / 0.557 / 0.085.
- Volatility is much stronger as a **future-magnitude channel** than as a universal directional channel.

**Strongest realized-volatility magnitude splits:**

- **15m:** W=84 → H=12, spread +139.65 bp, t=74.02
- **1h:** W=24 → H=6, spread +162.34 bp, t=33.41
- **4h:** W=6 → H=6, spread +218.55 bp, t=16.73
- **1d:** long-horizon sign flips; W=42 → H=168, spread -11142.51 bp, t=-12.52, so low-vol daily states outperform high-vol states over long forward windows

**Range-based volatility** is at least as informative as realized volatility in 15m/1h/4h, and stronger on 1d. Strongest directional splits:

- **15m:** range_W24 → fwd_84, t=6.58
- **1h:** range_W6 → fwd_168, t=5.20
- **4h:** range_W84 → fwd_168, t=7.58
- **1d:** range_W84 → fwd_168, t=-18.06

**Vol-normalization** helps in several places, but not uniformly:

- 15m W=84: raw t=0.71 → normalized t=7.26
- 1h W=168: raw reversal t=-4.43 → normalized t=-0.56, so the raw edge is heavily vol-state-driven
- 4h W=168: raw t=19.51 → normalized t=22.43
- 1d W=168: raw t=0.90 → normalized t=5.87, but block sign consistency worsens

**Compression** does not support a generic intraday breakout-release claim here.

- 15m comp_W12: in-compression future-magnitude spread -48.82 bp, t=-98.39
- 1h comp_W6: -56.64 bp, t=-38.48
- 4h comp_W6: -102.00 bp, t=-16.24
- release bars stay weak/negative rather than turning into a clean expansion effect
- only 1d W=168 shows the opposite: compression aligns with higher future magnitude, t=9.00

## Regime Structure

Using a raw W=42 regime lens, **4h and 1d** have the clearest directional regime separation.

- **4h** trend vs chop: forward-42 return spread +227.57 bp, t=6.08
- **4h** crisis vs chop: +832.90 bp, t=6.14
- **1d** trend vs chop: +1723.60 bp, t=5.29
- **1d** crisis vs chop: +3607.53 bp, t=14.97

**15m** regimes matter mainly for magnitude, not direction.

- 15m crisis vs chop on |fwd_42|: +279.83 bp, t=29.55
- 15m trend vs chop on signed fwd_42: t=-1.57

**1h** trend vs chop is mostly noise.

- signed t=-0.37
- magnitude t=-1.21
- only crisis states matter there, mainly by increasing magnitude

**Tail behavior:**

- **15m** extreme 1% one-bar tails reverse over H=24: signed edge -72.13 bp, t=-5.15; they also raise H=12 future magnitude, t=17.43
- **1h** extreme tails mildly reverse over H=6: t=-2.08; future magnitude at H=1 rises, t=9.23
- **4h** tail direction is near noise; magnitude is positive
- **1d** extreme tails are underpowered: only 12 events in the 1%/99% scan, so directional inference is weak

## Volatility/Regime Channel Summary

**Strongest directional signals by absolute t-stat:**

| Channel | Timeframe | Measure | t |
|---|---|---|---|
| range vol | 1d | range_W84 high/low → fwd_168 | -18.06 |
| regime | 1d | crisis vs chop → fwd_42 | 14.97 |
| realized vol | 1d | vol_W84 high/low → fwd_168 | -11.51 |
| realized vol | 15m | vol_W84 high/low → fwd_168 | 10.16 |
| realized vol | 4h | vol_W84 high/low → fwd_168 | 10.07 |

**Strongest magnitude/regime signals by absolute t-stat:**

| Channel | Timeframe | Measure | t |
|---|---|---|---|
| compression | 15m | comp_W12 in-state → \|fwd_12\| | -98.39 |
| range vol | 15m | range_W6 high/low → \|fwd_12\| | 74.02 |
| realized vol | 15m | vol_W84 high/low → \|fwd_12\| | 74.02 |
| compression | 1h | comp_W6 in-state → \|fwd_6\| | -38.48 |
| range vol | 1h | range_W24 high/low → \|fwd_6\| | 33.41 |
| realized vol | 1h | vol_W24 high/low → \|fwd_6\| | 33.41 |

**Noise / weak areas:**

- 1h trend-vs-chop directional split
- daily extreme-tail direction due very small event count
- any broad claim that "compression exit = immediate volatility expansion"

---

D1b2 complete. No strategies, no backtests, no candidate proposals, and no clean external OOS claim.
