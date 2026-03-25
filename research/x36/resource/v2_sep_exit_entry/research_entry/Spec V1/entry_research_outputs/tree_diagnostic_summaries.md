## Fold 1 (train n=75, oos n=31)

```text
|--- ema28_net_quote_norm_28 <= -0.04
|   |--- class: 1
|--- ema28_net_quote_norm_28 >  -0.04
|   |--- ema12_vol_surprise_quote_28 <= 0.90
|   |   |--- class: 0
|   |--- ema12_vol_surprise_quote_28 >  0.90
|   |   |--- class: 0

```

## Fold 2 (train n=106, oos n=47)

```text
|--- ema28_net_quote_norm_28 <= -0.04
|   |--- class: 1
|--- ema28_net_quote_norm_28 >  -0.04
|   |--- ema12_vol_surprise_quote_28 <= 0.90
|   |   |--- class: 0
|   |--- ema12_vol_surprise_quote_28 >  0.90
|   |   |--- class: 0

```

## Fold 3 (train n=153, oos n=28)

```text
|--- ema12_vol_surprise_quote_28 <= 0.89
|   |--- ema28_net_quote_norm_28 <= -0.00
|   |   |--- class: 0
|   |--- ema28_net_quote_norm_28 >  -0.00
|   |   |--- class: 0
|--- ema12_vol_surprise_quote_28 >  0.89
|   |--- ema28_imbalance_ratio_base <= -0.03
|   |   |--- class: 1
|   |--- ema28_imbalance_ratio_base >  -0.03
|   |   |--- class: 0

```

## Fold 4 (train n=181, oos n=12)

```text
|--- ema12_vol_surprise_quote_28 <= 0.89
|   |--- ema12_net_quote_norm_28 <= -0.00
|   |   |--- class: 0
|   |--- ema12_net_quote_norm_28 >  -0.00
|   |   |--- class: 0
|--- ema12_vol_surprise_quote_28 >  0.89
|   |--- ema28_imbalance_ratio_base <= -0.03
|   |   |--- class: 1
|   |--- ema28_imbalance_ratio_base >  -0.03
|   |   |--- class: 0

```
