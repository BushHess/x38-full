# Full-period continuous diagnostic (4 combos)

This is a **continuous full-period diagnostic** for compounding comparison. It **does not replace** the official stitched WFO OOS validation.

Two windows are reported to avoid ambiguity:

- **All available data**: first eligible H4 close **2018-08-17 07:59:59.999000+00:00** through last available H4 close **2026-03-11 07:59:59.999000+00:00**.

- **Cutoff-aligned**: same start, but truncated at the official project cutoff **2026-02-28 23:59:59.999000+00:00**.

Warmup remains frozen at 365 days, so the diagnostic period starts on the first eligible H4 close **2018-08-17 07:59:59.999000+00:00** even though raw data begins in 2017.

## All available data (primary read)

| combo                                         |   sharpe |     cagr |       mdd |   end_equity_multiple |   final_equity_cash |   trades |   closed_trades |   exposure |   bar_count |
|:----------------------------------------------|---------:|---------:|----------:|----------------------:|--------------------:|---------:|----------------:|-----------:|------------:|
| Entry freeze weakvdo(0.0065) + Exit winner    |  1.34205 | 0.469645 | -0.376299 |               18.3845 |              183845 |      220 |             219 |   0.329693 |       16573 |
| Entry freeze weakvdo(0.0065) + Exit runner-up |  1.37031 | 0.479217 | -0.307416 |               19.3095 |              193095 |      228 |             227 |   0.353406 |       16573 |
| Entry freeze weakvdo(0.0065) + Base exit      |  1.48903 | 0.590662 | -0.366178 |               33.4442 |              334442 |      176 |             175 |   0.396488 |       16573 |
| Entry original VDO>0 + Base exit              |  1.4611  | 0.605266 | -0.388616 |               35.8372 |              358372 |      195 |             194 |   0.432571 |       16573 |


### Read

- By **Sharpe** on the full continuous sample, ranking is: combo3 first (1.489028), then combo4 (1.461103), combo2 (1.370307), combo1 (1.342051).

- By **CAGR**, the top combo is **combo4** at **60.526571%**.

- By **MDD** (less negative is better), the best combo is **combo2** at **-30.741602%**.

- The full-period ranking is materially different from the post-2021 stitched OOS ranking. That is consistent with the already-known structural caveat: the promoted improvements are **post-2021 favorable**, while the original/base-exit variants were stronger in the pre-2021 portion of the data.


## Cutoff-aligned continuous run (for consistency with official validation cutoff)

| combo                                         |   sharpe |     cagr |       mdd |   end_equity_multiple |   final_equity_cash |   trades |   closed_trades |   exposure |   bar_count |
|:----------------------------------------------|---------:|---------:|----------:|----------------------:|--------------------:|---------:|----------------:|-----------:|------------:|
| Entry freeze weakvdo(0.0065) + Exit winner    |  1.37504 | 0.486054 | -0.376299 |               19.7719 |              197719 |      218 |             218 |   0.330083 |       16511 |
| Entry freeze weakvdo(0.0065) + Exit runner-up |  1.40126 | 0.494633 | -0.307416 |               20.6483 |              206483 |      226 |             226 |   0.354006 |       16511 |
| Entry freeze weakvdo(0.0065) + Base exit      |  1.51782 | 0.607679 | -0.366178 |               35.763  |              357630 |      174 |             174 |   0.39725  |       16511 |
| Entry original VDO>0 + Base exit              |  1.48856 | 0.622494 | -0.388616 |               38.3219 |              383219 |      193 |             193 |   0.433469 |       16511 |


The cutoff-aligned continuous window is included only to line up with the official acceptance cutoff. The primary diagnostic requested here is the **all-available continuous run**.
