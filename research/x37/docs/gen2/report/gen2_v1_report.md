Mode Confirmation
Session mode is seed_discovery. Constitution file research_constitution_v2.0.yaml is readable, version 2.0, status active.
Snapshot is snapshot_20260318. Declared timeframes are 15m, 1h, 4h, 1d; declared historical coverage is 2017-08-17 through 2026-03-18 UTC.
state_pack_input is null; appended delta window is unset. This is a blind seed-discovery start, not a forward-evaluation continuation.
Admissible Input Audit
Files used: research_constitution_v2.0.yaml, FILE_AND_SCHEMA_CONVENTIONS_EN.md, session_manifest.json, input_hash_manifest.txt, and the four historical snapshot files: spot_btcusdt_15m.csv, spot_btcusdt_1h.csv, spot_btcusdt_4h.csv, spot_btcusdt_1d.csv.
Input manifest states this is the first seed-discovery session and that all four files were canonicalized to the 13-column schema defined by the schema conventions document.
Files present but inadmissible for blind discovery: none detected in the provided workspace.
Forbidden carry-over artifacts were not supplied as active inputs; the manifest explicitly confirms absence of prior reports, prior winners, prior shortlist tables, prior system specs, prior benchmark definitions, and prior state packs from another lineage.
Contamination Status
The historical snapshot is candidate-mining-only in seed_discovery; it is contaminated for same-snapshot out-of-sample claims.
No clean external OOS claim may be made from this snapshot. Clean forward evidence requires genuinely appended post-freeze data.
Execution Boundaries
Allowed archetypes: A_slow_trend_state, B_pullback_continuation, C_compression_breakout. Domain is locked to Binance Spot BTCUSDT, UTC, using spot OHLCV plus taker-flow data on 15m/1h/4h/1d.
Hard caps: max 3 post-seed candidates, max 2 challengers, max 3 logical layers, max 1 slow-context layer, max 1 fast-state layer, max 1 optional entry layer, max 4 tunable quantities per candidate, max 20 discovery configs per archetype, max 60 total seed configs.
Hard constraints: CAGR_50bps > 0, max_drawdown_50bps <= 0.45, entries/year in [6,80], exposure in [0.15,0.90], bootstrap LB5 of mean daily return > 0. Execution is spot long-only/long-flat with binary 0%/100% sizing; no leverage, pyramiding, regime-specific parameter sets, or discretionary overrides.
Required outputs: one champion seed, up to two challenger seeds, frozen system specs, candidate registry, meta-knowledge registry, portfolio state, historical_seed_audit.csv, empty forward_evaluation_ledger.csv, contamination map, and state_pack_v1. This chat must remain in seed_discovery mode only.
Go / No-Go

GO FOR D1

Basis: admissible inputs are present and sufficient; constitution is readable; manifest is internally aligned with blind seed discovery; schema conventions are present; hash manifest is present; no state-pack carry-over is attached.

=========

Đã hoàn tất D1a và lưu báo cáo tại đây: d1a_quality_report.md

Đối chiếu được thực hiện theo schema input chuẩn 13 cột, quy tắc “no synthetic bar repair”, và các split warmup / discovery / holdout / reserve_internal trong constitution. Snapshot này vẫn chỉ là candidate-mining-only, không thể dùng để tuyên bố clean external OOS.

1. Schema Validation
file	status	notes
spot_btcusdt_15m.csv	PASS	Đúng thứ tự 13 cột; không có cột thừa cuối; không cần inject symbol/interval; open_time/close_time là integer ms UTC; symbol=BTCUSDT; interval=15m; bar duration khớp
spot_btcusdt_1h.csv	PASS	Như trên; interval=1h
spot_btcusdt_4h.csv	PASS	Như trên; interval=4h
spot_btcusdt_1d.csv	PASS	Như trên; interval=1d
2. Anomaly Log

Không có anomaly kiểu blocking. Không phát hiện:

duplicate open_time
null / NaN
giá <= 0
high < low
open hoặc close nằm ngoài [low, high]
taker_buy_base_vol > volume

Anomaly thực tế ghi nhận:

timeframe	gap events	missing bars	zero-volume bars	ghi chú
15m	32	561	61	Gaps chỉ nằm trong warmup + discovery
1h	28	126	5	Gaps chỉ nằm trong warmup + discovery
4h	8	16	1	Gaps chỉ nằm trong warmup + discovery
1d	0	0	0	None

Các gap cuối cùng:

15m: gap cuối ở 2023-03-24 12:30:00 UTC -> 2023-03-24 14:00:00 UTC, thiếu 5 bars
1h: gap cuối ở 2023-03-24 12:00:00 UTC -> 2023-03-24 14:00:00 UTC, thiếu 1 bar
4h: gap cuối ở 2020-02-19 08:00:00 UTC -> 2020-02-19 16:00:00 UTC, thiếu 1 bar
1d: không có gap

Điểm đáng chú ý nhất: không có gap nào trong holdout hoặc reserve_internal.

3. Summary Statistics
timeframe	total bars	date range	expected vs actual	price range (min low → max high)	median daily volume	median daily num_trades	zero-volume %
15m	300,479	2017-08-17 04:00:00 UTC → 2026-03-18 23:59:59 UTC	301,040 vs 300,479 (-561)	2817.00 → 126199.63	38909.22142	1,162,109	0.0203%
1h	75,134	2017-08-17 04:00:00 UTC → 2026-03-18 23:59:59 UTC	75,260 vs 75,134 (-126)	2817.00 → 126199.63	38909.22142	1,162,109	0.0067%
4h	18,799	2017-08-17 04:00:00 UTC → 2026-03-18 23:59:59 UTC	18,815 vs 18,799 (-16)	2817.00 → 126199.63	38909.22142	1,162,109	0.0053%
1d	3,136	2017-08-17 00:00:00 UTC → 2026-03-18 23:59:59 UTC	3,136 vs 3,136 (0)	2817.00 → 126199.63	38909.22142	1,162,109	0.0000%
4. Split Coverage

Split boundaries được kiểm theo constitution: warmup từ first available bar đến 2019-12-31, discovery 2020-01-01 đến 2023-06-30, holdout 2023-07-01 đến 2024-09-30, reserve_internal từ 2024-10-01 đến snapshot end.

timeframe	warmup	discovery	holdout	reserve_internal
15m	82,807	122,440	43,968	51,264
1h	20,709	30,617	10,992	12,816
4h	5,186	7,661	2,748	3,204
1d	867	1,277	458	534
5. Data Quality Verdict

PASS (data usable)

Kết luận ngắn gọn:

Schema chuẩn, timestamps chuẩn, không có corruption kiểu blocking.
Có gaps lịch sử ở 15m / 1h / 4h, nhưng chúng đã được log đầy đủ và không được repair.
Holdout và reserve_internal sạch gap.
Snapshot vẫn chỉ được dùng cho candidate mining, không được diễn giải như clean external OOS.

=========

Đã hoàn tất D1b và lưu đầy đủ tại đây: d1b_measurements.md

Không dùng holdout hay reserve_internal. Không có backtest, không có thiết kế chiến lược, không có candidate. Snapshot này vẫn chỉ là candidate-mining-only.

1. D1 Timeframe Summary

D1 có structure rõ, không phải noise.

Thời gian discovery nằm trên EMA50 là 54.03%, trên EMA200 là 58.26%; bullish EMA stack (EMA21 > EMA50 > EMA200) chiếm 45.42%.
EMA spread sign persistence rất cao: 96.6%–99.6% tùy cặp 10/21 đến 100/200.
ROC cũng có persistence cao, nhưng phần này bị “overlap mechanics” khuếch đại; tín hiệu đáng tin hơn là forward-return conditioning.

Tín hiệu D1 theo forward returns:

close > EMA50 nâng 10D forward return thêm khoảng +1.87pp, 20D thêm +3.21pp so với off-state.
ROC50 > 0 nâng 10D khoảng +1.50pp.
EMA stack bull nâng 20D khoảng +3.16pp.
close_pos100_upper nâng 20D khoảng +3.53pp.

Kết luận: primitive kiểu D1 permission / trend filter là có tín hiệu đo được.

2. H4 Timeframe Summary

H4 có hai thứ rất rõ: volatility clustering và pullback structure.

ATR14/close trung bình khoảng 2.09%, p90 khoảng 3.27%.
ATR persistence rất mạnh: ac1 = 0.994, ac24 = 0.738.
Full compression combo (ATR thấp + range thấp + body thấp theo warmup p20) chiếm 11.17% số bar H4, median duration 3.5 bars, max 125 bars.
Raw same-direction bar runs ngắn: median chỉ 1 bar, p90 khoảng 3 bars. Nghĩa là persistence thô theo từng bar không mạnh, nhưng regime state thì mạnh.

Pullback / drawdown:

Với rolling-high 42-bar reference, completed drawdown episode có median recovery khoảng 12 bars.
Recovery time tăng rất mạnh theo độ sâu:
drawdown 2–5%: median khoảng 12.5 bars
5–10%: median khoảng 42.5 bars
>10%: median khoảng 105 bars

Kết luận: primitive kiểu H4 drawdown / pullback depth / volatility regime là có structure thật.

3. 1h Timeframe Summary

1h có signal, nhưng signal sạch nhất không nằm ở breakout trần trụi; nó nằm ở breakout có xác nhận.

Upside breakout trên local 24h range xuất hiện ở 2.93% số bar 1h, tổng 898 events.
Standalone 24h-range breakout có 24h forward return trung bình khoảng +0.34%, hit-rate 49.9%. Tức là có chút drift dương, nhưng standalone thì yếu.
8h short-consolidation breakout có 24h forward return trung bình khoảng +0.21%, hit-rate 49.1%. Cũng không mạnh nếu đứng một mình.
Generic 1h reclaim trên EMA20 cho follow-through yếu/flat; đây không phải primitive đẹp nếu xét độc lập.

Participation quanh H4 events:

Sau H4 breakout, 6h tiếp theo có volume ratio cao hơn baseline khoảng +15.8%, trades ratio cao hơn khoảng +14.3%.
Sau H4 reclaim, lift participation nhỏ hơn nhiều; taker-buy ratio nhích lên nhưng không mạnh.

Kết luận: 1h participation confirmation hữu ích hơn hẳn 1h anchor reclaim.

4. Cross-Timeframe Relationships

Đây là phần đáng giá nhất.

D1 trend -> H4 alignment:

Khi D1 close > EMA50, xác suất H4 close > EMA21 tăng từ 40.2% lên 64.5%. Lift khoảng +24.3pp.
Với D1 ROC50 > 0, lift khoảng +15.1pp.
Với bullish EMA stack, lift khoảng +7.5pp.

D1 permission -> H4 entry quality:

H4 breakout20 dưới D1 close > EMA50 có 48h mean forward return khoảng +0.42%, còn off-state khoảng -0.04%. Lift khoảng +0.45pp.
H4 reclaim dưới D1 close > EMA50 có 48h mean forward return khoảng +1.18%, còn off-state khoảng +0.28%. Lift khoảng +0.90pp, hit-rate lift khoảng +8.0pp.

H4 compression -> 1h breakout follow-through:

1h 24h-range breakout bình thường: 24h mean khoảng +0.34%.
Nếu trước đó có H4 compression combo: tăng lên khoảng +0.91%.
Nếu vừa có H4 compression vừa có high 1h participation: tăng lên khoảng +0.97%.

Kết luận: multi-timeframe conditioning là có thật. D1 filter và H4 regime không phải trang trí; chúng thay đổi chất lượng event downstream.

5. Taker Flow Analysis

Taker flow không vô dụng, nhưng đứng một mình thì yếu hơn nhiều người tưởng.

Phân phối:

Mean taker_buy_ratio ở discovery rất ổn định quanh 0.491–0.492 trên mọi timeframe.
Std giảm dần khi timeframe lớn hơn: 15m cao nhất, 1d thấp nhất.

Predictive quality:

15m, 1h: correlation với forward returns gần như bằng 0. Standalone hầu như là noise.
4h: có tín hiệu dương nhẹ ở horizon dài hơn, nhưng vẫn nhỏ.
1d: có bias dương nhẹ ở 3–5 ngày, nhưng đảo chiều ở 10 ngày; nhìn giống crowding/exhaustion hơn là continuation sạch.

Kết luận:

Volume + num_trades participation tốt hơn taker imbalance.
Taker flow hợp làm biến phụ trợ/context hơn là primitive dẫn đường chính.
6. Primitives Signal Assessment

Đánh giá gọn:

Archetype A
D1 momentum: YES
D1 EMA slope/spread: YES
D1 close vs rolling anchor: YES
H4 trend/state persistence: YES
H4 volatility quiet/expansion as context: YES (context)
Exit by permission-off/state deterioration: YES
ATR-style trailing as standalone directional primitive: WEAK
Archetype B
H4 drawdown from rolling high: YES
H4 distance from MA/anchor reclaim: YES
H4 range position: WEAK
1h reclaim above local anchor: WEAK/NO
1h short-consolidation break: YES
1h participation confirmation: YES
Archetype C
D1 non-bearish / neutral-positive permission: YES
H4 low-ATR compression: YES
H4 range compression: YES
H4 body compression: YES
1h breakout above local range standalone: WEAK
1h volume/trades participation rise: YES
1h taker-flow rise standalone: WEAK

Nói thẳng: phần sạch nhất của snapshot này không nằm ở “taker flow thần thánh”, mà nằm ở D1 permission + H4 regime/compression + 1h participation-conditioned breakout. Generic reclaim kiểu mềm ở 1h thì yếu.

=========

Đã hoàn tất D1c và lưu 2 file tại đây:

d1c_candidate_designs.md
d1c_config_matrix.csv

Không có backtest, không có scoring/ranking, không có chọn champion/challenger. Thiết kế chỉ dùng primitives đã có tín hiệu đo được trong D1b.

1. Archetype A Candidates
candidate_id	thiết kế	layers	tunables	configs
A_D1EMA_H4STATE_DD	D1 permission bằng close > EMA; H4 state bằng close > EMA + drawdown cap từ rolling high; không dùng 1h entry layer	2	4	16

Logic gọn:

Entry tại H4 close khi D1 permission ON và H4 state ON, fill ở next H4 open
Exit khi D1 permission OFF, hoặc H4 close rơi dưới state EMA, hoặc H4 drawdown vượt ngưỡng

Lý do giữ lại:

D1 close > EMA50 là permission signal sạch nhất trong D1b
D1 permissive state làm H4 alignment tốt hơn rõ rệt
H4 drawdown depth có structure thật, nên hợp làm deterioration control
2. Archetype B Candidates
candidate_id	thiết kế	layers	tunables	configs
B_D1RNG_H4PB_1HBRK	D1 upper-range permission (close_pos100); H4 pullback depth zone; 1h breakout khỏi short consolidation kèm participation confirmation	3	4	16

Logic gọn:

Entry tại 1h close khi:
D1 close_pos100 >= threshold
H4 drawdown nằm trong pullback zone
1h close break lên trên breakout level và volume/trades participation vượt ngưỡng warmup
Fill ở next 1h open
Exit khi D1 permission OFF, hoặc H4 pullback hỏng sâu hơn ngưỡng fail-depth, hoặc 1h close rơi lại dưới breakout level đã lưu tại entry

Lý do giữ lại:

D1 upper-range state có forward lift tốt
H4 pullback depth cho recovery profile rõ
1h short-consolidation breakout tốt hơn hẳn 1h reclaim generic
Participation hữu ích; taker-flow standalone thì không đủ sạch
3. Archetype C Candidates
candidate_id	thiết kế	layers	tunables	configs
C_D1ROC_H4CMP_1HBRK	D1 positive ROC filter; H4 compression combo; 1h 24-bar breakout với participation confirmation	3	3	8

Logic gọn:

Entry tại 1h close khi:
D1 ROC dương
parent H4 bar đang ở compression combo
1h close break lên trên 24h local range và participation vượt quantile warmup
Fill ở next 1h open
Exit khi D1 ROC filter OFF, hoặc 1h close rơi lại dưới breakout level, hoặc H4 close thủng compression floor đã lưu ở entry

Lý do giữ lại:

D1 ROC dương có measurable lift
H4 compression -> 1h breakout là interaction mạnh nhất đo được trong D1b
Kết hợp compression + participation tốt hơn breakout trần trụi
4. Config Matrix Summary
archetype	candidate_id	configs
A	A_D1EMA_H4STATE_DD	16
B	B_D1RNG_H4PB_1HBRK	16
C	C_D1ROC_H4CMP_1HBRK	8

Tổng cộng: 40 configs

5. Hard Cap Compliance Check
cap	observed	status
max candidates after seed <= 3	3 designed	PASS
max challengers after seed <= 2	chưa chọn ở D1c; design universe capped at 3	PASS
max logical layers per candidate <= 3	A=2, B=3, C=3	PASS
max tunables per candidate <= 4	A=4, B=4, C=3	PASS
max discovery configs per archetype <= 20	A=16, B=16, C=8	PASS
max total seed configs <= 60	40	PASS
chỉ dùng primitives được constitution cho phép	all pass	PASS
execution = signal at close, fill at next open	all pass	PASS
UTC alignment, no lookahead	all pass	PASS

Điểm quan trọng: tôi cố tình không nhét đủ 60 cấu hình. 40 là đủ phủ những primitive có tín hiệu đo được mà không bắt đầu pha loãng sang các biến thể mang tính suy đoán.

=========

D1d hoàn tất. Không dùng holdout hay reserve_internal. Không freeze, không chọn champion/challenger.

Implementation Notes
Tôi triển khai đúng logic D1c cho cả 40 configs, với fill tại next bar open theo timeframe thực thi của từng candidate (H4 cho A, 1h cho B/C).
Vì các configs ở D1c là fixed-rule, không có per-fold refit, tôi chạy mỗi config như một path liên tục từ historical start đến 2023-06-30, chặn mọi trade trước 2020-01-01, rồi cắt metrics theo 14 quarterly test folds. Cách này giữ đúng information set theo thời gian mà không cần ép flat giả ở cuối mỗi quý.
Higher-timeframe alignment luôn dùng last completed bar. D1 closepos100 được tính trên rolling D1 high/low 100 ngày. ATR14 dùng Wilder smoothing. Các quantile gate cho participation/compression đều cố định từ warmup pre-2020.
Cost model: 20bps RT và 50bps RT, áp tại entry/exit execution open. Equity được mark-to-market ở bar close; Sharpe dùng UTC daily returns từ daily close equity; MDD dùng bar-close equity path. Cuối discovery được chốt tại 2023-06-30 close, nên không cần chạm sang bar open của holdout.
Execution Progress
D1d COMPLETE
Hoàn thành 40 / 40 configs
Hoàn thành 560 / 560 config×fold windows
Hoàn thành 1,120 / 1,120 config×fold×cost evaluations
File outputs:
d1d_wfo_results.csv: 1120 rows
d1d_wfo_aggregate.csv: 80 rows
WFO Results Summary

Top 10 configs theo aggregate Calmar_50bps = agg_cagr / max(abs(agg_mdd), 0.15) ở mức phí 50bps RT:

config_id	candidate_id	agg_cagr	agg_sharpe	agg_mdd	total_entries	avg_exposure	calmar_50bps
C002	C_D1ROC_H4CMP_1HBRK	0.6648	1.5679	0.2877	7	0.2765	2.3109
C001	C_D1ROC_H4CMP_1HBRK	0.6610	1.5617	0.2877	8	0.2765	2.2978
C004	C_D1ROC_H4CMP_1HBRK	0.6206	1.4905	0.2877	12	0.2823	2.1573
C003	C_D1ROC_H4CMP_1HBRK	0.6193	1.4882	0.2877	14	0.2824	2.1527
C006	C_D1ROC_H4CMP_1HBRK	0.4771	1.2093	0.4994	17	0.2931	0.9554
C005	C_D1ROC_H4CMP_1HBRK	0.4643	1.1847	0.5082	19	0.2949	0.9136
A013	A_D1EMA_H4STATE_DD	0.3035	0.8503	0.3436	190	0.3510	0.8832
C008	C_D1ROC_H4CMP_1HBRK	0.4490	1.1579	0.5192	23	0.2955	0.8647
C007	C_D1ROC_H4CMP_1HBRK	0.4388	1.1380	0.5213	25	0.2968	0.8417
A015	A_D1EMA_H4STATE_DD	0.2860	0.8453	0.3678	165	0.3118	0.7775

Ghi chú ngắn:

Top 10 ở 50bps nghiêng mạnh về Archetype C; Archetype B đã được chạy đầy đủ nhưng không nằm trong top 10 Calmar_50bps.
Đây chỉ là mô tả kết quả WFO, chưa phải bước lọc/chọn seed. Việc đó thuộc D1e.
Files Saved
d1d_wfo_results.csv
d1d_wfo_aggregate.csv

=========

Hard Constraint Filter

Discovery WFO aggregate ở 50 bps RT:

40 configs vào filter
19 configs sống sót
21 configs bị loại

Breakdown theo candidate:

A_D1EMA_H4STATE_DD: 9/16 sống sót
B_D1RNG_H4PB_1HBRK: 10/16 sống sót
C_D1ROC_H4CMP_1HBRK: 0/8 sống sót

Lý do loại trùng lặp giữa các config:

mdd > 0.45: 14
entries/year ngoài [6, 80]: 6
exposure ngoài [0.15, 0.90]: 3
cagr <= 0: 1

Representative config sau Step 2:

A → A013 (Calmar_50bps = 0.8832)
B → B009 (Calmar_50bps = 0.5269)

Archetype C bị chặn ngay ở discovery, chủ yếu vì entries/year quá thấp, và một số config còn dính MDD > 0.45.

Holdout Results

Holdout: 2023-07-01 → 2024-09-30

candidate_id	config_id	cost_rt	CAGR	Sharpe	MDD	entries	exposure	mean_daily_return	holdout hard pass @50bps
A_D1EMA_H4STATE_DD	A013	20	0.2358	0.8145	0.2108	85	0.4458	0.000721	—
A_D1EMA_H4STATE_DD	A013	50	0.0080	0.1869	0.2766	85	0.4458	0.000168	PASS
B_D1RNG_H4PB_1HBRK	B009	20	0.0480	0.3175	0.2276	20	0.1835	0.000203	—
B_D1RNG_H4PB_1HBRK	B009	50	-0.0011	0.1137	0.2627	20	0.1835	0.000073	FAIL (cagr<=0)
Reserve Results

Reserve internal: 2024-10-01 → 2026-03-18
Đây chỉ là internal evidence, không phải clean forward evidence.

candidate_id	config_id	cost_rt	CAGR	Sharpe	MDD	entries	exposure	mean_daily_return
A_D1EMA_H4STATE_DD	A013	20	0.1600	0.6857	0.2676	86	0.3508	0.000504
A_D1EMA_H4STATE_DD	A013	50	-0.0279	0.0335	0.3847	86	0.3508	0.000025
B_D1RNG_H4PB_1HBRK	B009	20	-0.2215	-2.1361	0.3516	31	0.0764	-0.000667
B_D1RNG_H4PB_1HBRK	B009	50	-0.2696	-2.5437	0.4066	31	0.0764	-0.000840
Bootstrap Check

Bootstrap trên full discovery daily returns của representative configs:

block sizes: 5, 10, 20 ngày
3000 resamples mỗi block size
seed: 20260319
dùng common paired indices giữa candidates

Hard rule: LB5 block-10 > 0

candidate_id	config_id	p5 block-5	LB5 block-10	p5 block-20	pass
A_D1EMA_H4STATE_DD	A013	-0.000037	-0.000042	-0.000078	FAIL
B_D1RNG_H4PB_1HBRK	B009	-0.000153	-0.000180	-0.000199	FAIL

Kết luận thẳng:

Cả A013 lẫn B009 đều rớt bootstrap hard constraint
Sau Step 6, không còn candidate nào sống sót
Final Ranking

Không có candidate nào đủ điều kiện để xếp hạng cuối cùng.

Pre-bootstrap adjusted preference chỉ để tham chiếu nội bộ:

A013: 0.8832 - (2×0.02) - (4×0.03) = 0.7232
B009: 0.5269 - (3×0.02) - (4×0.03) = 0.3469

Nhưng phần này không còn hiệu lực vì cả hai đều fail bootstrap.
Do đó d1e_final_ranking.csv được lưu ở trạng thái empty.

Files Saved
d1e_hard_constraint_filter.csv
d1e_holdout_results.csv
d1e_reserve_results.csv
d1e_final_ranking.csv
