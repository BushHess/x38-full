# X34 - Thesis Ve Con Duong Lon Hon

Ngay: 2026-03-13
Pham vi: Tai dung "con duong lon hon" ma X34 mo ra, thay vi chi nhin X34 nhu mot attempt that bai de thay VDO bang Q-VDO-RH Option A.

---

## Thesis Tong Ket

Gia tri lon nhat cua X34 khong nam o cho no tim ra mot replacement tot hon cho VDO.
No khong lam duoc dieu do.

Gia tri sau hon cua X34 nam o cho no lam sac net hon mot thesis cap project:

1. Tren BTC spot trend-following, thong tin volume/microstructure tai thoi diem vao lenh co the da gan nhu bi khai thac het boi cap doi `trend_up` + xac nhan nhi phan `VDO > 0`.
2. Viec lam cho xac nhan do "kho hon" bang mot nguong duong, ke ca khi nguong do adaptive va duoc dat len mot flow signal bieu dien phong phu hon, co xu huong cai thien ve mat dep cua signal-space hon la cai thien alpha co the giao dich duoc.
3. Trong thuc te, kieu gating chat hon nay van hanh chu yeu nhu mot may veto rong. No cat rat nhieu entry, nhung khong cat dung muc o nhung state co gia tri thap de bu lai phan bull/chop upside bi mat.
4. Vi vay, con duong lon hon ma X34 mo ra khong phai la "toi uu Q-VDO-RH manh hon nua". No la:
   - falsify hoac confirm lop y tuong lon hon: hard-thresholded flow filters tai entry;
   - neu con component nao song sot, chuyen vai tro cua no sang `context`, `confidence`, hoac `regime`;
   - chuyen marginal alpha search ra khoi entry filtering, tru khi co bang chung moi vuot qua mot burden of proof cao hon ro ret.

Thesis nay phu hop voi artifact goc cua X34 va dong thoi hoi tu voi prior work trong X25 va X27.

---

## Vi Sao Memo Nay Can Thiet

Co mot cach doc de nhung nong ve X34:

- Q-VDO-RH nhin co ve dep trong diagnostic space.
- Phien ban strategy dau tien fail.
- Vay buoc tiep theo la tune hoac ablate Q-VDO-RH cho toi khi no thang.

Cach doc nay qua hep.

Cach doc manh hon la: X34 la mot bai test moi cho mot cau hoi tong quat hon:

> Mot flow filter chon loc hon, bieu dien giau hon, adaptive hon co cai thien duoc BTC spot entry khi `trend_up` va `VDO > 0` da co san hay khong?

Cau tra loi hien tai cua X34 la: khong, neu dung no nhu mot always-on hard entry gate; va kha nang cao cung khong nen xem bai toan nay la bai toan "tim mot threshold chat hon".

---

## Dung Lai Cau Chuyen Tu Primary Artifacts

### 1. `a_diagnostic` chung minh Q-VDO-RH thuc su khac, khong phai clone

Nhanh diagnostic khong chi la mot clone-check hinh thuc. No cho thay Q-VDO-RH thuc su khac VDO goc:

- Spearman correlation chi `0.886639`, khong gan-identical.
- Trigger count `4477` so voi `9378`, tuc Q-VDO-RH chi fire bang `47.74%` baseline.
- Dynamic range mo rong ro: max `0.2873` so voi `0.1710`.
- Divergence rat bat doi xung: `4962` bars `VDO yes / Q-VDO no` nhung chi co `71` bars `VDO no / Q-VDO yes`.

Nguon: `branches/a_diagnostic/results/diagnostic_results.json`

Chi tiet nay quan trong vi no loai bo mot cach giai thich de dan:

> strategy fail vi signal moi thuc ra gan giong signal cu.

Khong phai.
No thuc su sac hon, chon loc hon, va bieu dien phong phu hon trong indicator space.

Nhung chinh diagnostic nay dong thoi dua ra warning dau tien:

- trigger frequency ratio thap hon nguong flag preregistered 50%;
- bien the moi da dang hanh xu nhu mot signal suppressor manh, chu khong phai mot refinement nhe.

Warning do ve sau tro thanh chi tiet quyet dinh.

### 2. Bat doi xung trong diagnostic da goi y co che that su

Ty le `4962 vs 71` la manh moi dau tien.

Q-VDO-RH khong mo ra mot opportunity surface moi dang ke.
No chu yeu veto nhung co hoi ma baseline VDO van se nhan.

Day la structural shift cốt lõi:

- baseline VDO: chap nhan bat ky positive momentum cua raw bounded flow;
- Q-VDO-RH Option A: chi chap nhan normalized-flow momentum neu no vuot adaptive noise floor.

Noi cach khac, design da bien mot confirmation signal kha permissive thanh mot confirmation signal rat selective voi mot thanh chuan di dong.

Dieu nay chi co ich neu muc selectivity them vao that su tap trung vao low-quality states.
Neu khong, no se tro thanh mot recall-destroying filter co ve ngoai dep.

### 3. `b_e0_entry` cho thay selectivity moi khong convert thanh alpha

Ket qua validation day du rat ro:

- candidate harsh score `97.36` vs baseline `123.32`
- Sharpe `1.151` vs `1.265`
- CAGR `42.8%` vs `52.0%`
- MDD `45.0%` vs `41.6%`
- decision: `REJECT`

Nguon: `branches/b_e0_entry/results/validation/reports/validation_report.md`

Day la manh moi lon thu hai.

That bai o day khong phai chi la:

> candidate hoi kem hon mot chut.

No dong thoi kem tren cac truc thuc dung quan trong nhat:

- return thap hon;
- Sharpe thap hon;
- drawdown xau hon.

Profile nay rat hop voi mot entry filter cat qua nhieu trade co gia tri nhung khong kiem duoc du protection de bu lai.

### 4. Underperformance den tu mat return, khong phai tu phi hay implementation noise

Score decomposition audit rat quan trong vi no dong mot loat escape hatch thuong gap.

Full-period delta chu yeu la:

- `return_term = -23.125`
- `mdd_penalty = -2.034`

O holdout, delta duong cung chu yeu den tu return, khong phai do cost terms.

Nguon: `branches/b_e0_entry/results/validation/reports/audit_score_decomposition.md`

Dieu nay co nghia la van de cot loi khong phai:

- phi qua cao;
- filter co giam churn nhung score formula khong credit dung;
- mot penalty term nao do vo tinh bury loi ich.

Van de cot loi don gian hon:

> strategy kiem duoc it tien hon o nhung noi quan trong nhat.

### 5. Trade-level artifact cho thay day khong phai mot tightening nhe

Trade-level analysis lam co che kho bi doc lech hon:

- matched trades: `68`
- baseline-only trades: `124`
- candidate-only trades: `86`
- match rate khoang `44%`
- ngay ca tren matched trades, mean delta PnL van la `-942.61`
- matched win rate cung giam: `54.41% -> 52.94%`

Nguon:
- `branches/b_e0_entry/results/validation/reports/trade_level_analysis.md`
- `branches/b_e0_entry/results/validation/results/trade_level_summary.json`

Day la mot ket qua rat quan trong.

Neu Q-VDO-RH chi don gian la trim bot nhung baseline trade te nhat, ta ky vong mot trong hai dieu:

1. phan lon surviving trades se giong baseline va perform tot hon; hoac
2. du co xoa nhieu trades, nhung matched trades con lai it nhat cung phai cai thien.

Khong dieu nao xay ra.

Filter nay khong chi cat mot chut noise.
No viet lai trade set va van fail ngay tren subset ma no giu lai.

Day la luc interpretation chuyen tu:

- "chua tune du"

sang:

- "vai tro nay co the la vai tro sai cho signal nay".

### 6. Pattern wins/losses cho thay over-filtering, khong phai improved selection

Duoi harsh cost:

- baseline: `77` wins, `115` losses, win rate `40.10%`, avg win `7460.65`, avg loss `-3095.57`
- candidate: `65` wins, `89` losses, win rate `42.21%`, avg win `5256.94`, avg loss `-2347.28`

Nguon: `branches/b_e0_entry/results/validation/results/full_backtest_detail.json`

Day la mot trong nhung pattern giau thong tin nhat cua toan bo study.

Q-VDO-RH:

- xoa nhieu losses hon wins neu nhin theo so luong;
- tang nhe hit rate;
- giam average loss;
- nhung giam average win manh hon nua.

Tuc la filter cai thien mot so "quality metrics" cuc bo nhung pha huy absolute payoff.

Day chinh la kieu pattern lam indicator space nhin dep hon, trong khi strategy-level outcome xau di.

Cach doc sach nhat la:

> filter nay chon loc, nhung no khong chon loc theo cach giu lai nhung winners outsized ma he thong dang song dua vao.

X34 khong prove per-trade tail attribution truc tiep, nhung no du manh de bac bo cau chuyen ngan gon kieu:

> precision cao hon chac chan se tot hon.

### 7. Risk path cung phan bac truc giac "it trade hon = an toan hon"

Candidate co it trades hon va exposure thap hon:

- trades `154` vs `192`
- avg exposure `40.13%` vs `46.82%`
- time in market `40.13%` vs `46.82%`

Nhung drawdown quality van xau di:

- worst DD `45.0%` vs `41.6%`
- mean DD `18.0%` vs `14.3%`
- DD episodes `17` vs `28`
- buy fills per episode `8.94` vs `6.82`

Nguon:
- `branches/b_e0_entry/results/validation/results/full_backtest_detail.json`
- `branches/b_e0_entry/results/validation/results/dd_episodes_summary.json`
- `branches/b_e0_entry/results/validation/results/trade_level_summary.json`

Day la mot ly do nua de khong doc X34 theo kieu "chi can toi uu filter them mot chut".

Filter co giam activity.
Nhung giam activity khong convert thanh equity path muot hon.
Nguoc lai, rui ro bi don vao it campaign hon nhung dam hon.

Day khong phai van de tuning theo nghia he hinh.
Day la mot phat hien ve cach filter tuong tac voi opportunity structure cua he thong.

### 8. Veto la broad-based, khong phai smart removal cua obvious junk

Diagnostic divergence breakdown:

- high-vol vetoed bars: `2512`
- low-vol vetoed bars: `2450`
- trend-up vetoed bars: `2590`
- trend-down vetoed bars: `2372`

Tuc la veto khong tap trung vao mot state nao ro rang la "xau".

Nguon: `branches/a_diagnostic/results/diagnostic_results.json`

Chi tiet nay rat quan trong, vi neu khong co no, ta van co the tu bao chua:

> dung la no cat nhieu, nhung biet dau no chu yeu cat rac.

Evidence cho thay nguoc lai.
No cat kha deu tren nhieu loai state.

Luc nay cau hoi phai doi:

> neu no cat rong nhu vay, tai sao performance van hu xau den the?

Cau tra loi nam o decomposition theo regime.

### 9. Uniform veto + asymmetric opportunity cost moi la failure mode that su

Regime trade summary cho thay:

- BULL PnL: `57.3k` candidate vs `109.7k` baseline
- CHOP PnL: `54.8k` candidate vs `93.1k` baseline
- BEAR PnL: `28.2k` candidate vs `24.6k` baseline

Regime decomposition cung cho thay candidate nhinh hon mot chut o mot so analytical regime nhu CHOP/TOPPING, nhung kem ro o BULL va hoi kem o BEAR.

Nguon:
- `branches/b_e0_entry/results/validation/results/regime_trade_summary.csv`
- `branches/b_e0_entry/results/validation/results/regime_decomposition.csv`

Day la trung tam cua larger-path thesis.

Extra selectivity cua Q-VDO-RH khong tap trung o nhung noi opportunity cost thap.
No la broad.
Nhung nhung trades no cat bo trong bull/chop lai co gia tri lon hon rat nhieu so voi nhung trades ma no giup tranh o noi khac.

Vi vay, abstraction dung khong phai:

- "Q-VDO-RH fail vi selectivity la xau."

Ma la:

- "Broad selectivity ma khong y thuc duoc opportunity cost se pha alpha trong mot fat-tail trend system."

Day la mot statement lon hon rat nhieu so voi rieng Q-VDO-RH.

### 10. Holdout paradox khong cuu duoc Option A, nhung no doi cau hoi nghien cuu

Holdout harsh nghieng ve candidate:

- candidate score `84.54`
- baseline score `65.42`

Nhung full-sample va WFO khong ung ho mot universal improvement:

- WFO win rate `0.375`
- Wilcoxon `p = 0.679688`
- bootstrap CI cat qua zero
- PSR `0.005436`

Nguon:
- `branches/b_e0_entry/results/validation/results/holdout_detail.json`
- `branches/b_e0_entry/results/validation/results/wfo_summary.json`
- `branches/b_e0_entry/results/validation/results/selection_bias.json`

Ket luan dung khong phai la:

> holdout noi no work.

Ket luan dung la:

> candidate co the co conditional usefulness, nhung khong phai nhu mot always-on replacement entry filter.

Chi tiet nay rat quan trong.

Khi framing dung, downstream path cung doi theo:

- khong phai `toi uu Option A cho toi khi no thang`;
- ma la `kiem tra xem component nao, neu co, co gia tri trong mot vai tro khac hay khong`.

---

## Larger Thesis, Noi Thang Ra

### Thesis A: X34 la bang chung chong lai hard-thresholded flow filters nhu default entry gate

Signal family moi dua vao hai structural change cung luc:

1. normalized signed notional flow;
2. adaptive positive threshold.

Bang chung hien tai cho thay: them mot gate chat hon len tren "good enough flow" la nguy hiem trong system nay.

Baseline entry logic hien tai da capture mot fact quan trong:

- flow momentum nam dung phia cua zero.

Dieu Q-VDO-RH Option A doi them la:

- khong chi positive flow momentum,
- ma la positive normalized-flow momentum va con phai clear mot moving noise floor.

Y tuong nay nghe rat principled.
Nhung no co ve rat dat do.

Ham y sau hon la BTC spot trend-following co the la mot domain ma:

- vao som quan trong hon xac nhan sach hon;
- mot so it winners outsized ganh mot phan rat lon tong alpha;
- tightening entry confirmation de cat dung phan distribution dang tra tien cho toan he thong.

Day la larger-path reading truc tiep nhat tu X34.

### Thesis B: signal-space quality la objective yeu cho entry-filter research

X34 tao ra mot textbook failure mode cua indicator research:

- selectivity cao hon;
- dynamic range rong hon;
- correlation voi baseline kha tot;
- normalization tinh vi hon;
- adaptive thresholding;
- nhung performance co the giao dich duoc lai te hon.

Dieu nay co nghia la trong future entry-filter research, can xem cac dau hieu sau la weak evidence:

- histogram dep hon;
- range rong hon;
- denoising co ve hop ly hon;
- trigger it hon va "chat" hon;
- normalization story thanh lich hon.

Nhung thu do khong vo ich.
Nhung chung rat xa muc du de escalate mot entry-filter idea.

X34 vi vay lam manh them mot methodology rule:

> dung escalate mot entry-filter idea chi vi no dep hon trong indicator space.
> Chi escalate neu no song sot nhanh duoc trade-level va OOS validation.

### Thesis C: neu con gi song sot, kha nang cao no chi song sot trong mot vai tro khac

X34 khong test moi component cua Q-VDO-RH trong moi vai tro co the.

Cai da fail cu the la hard gate:

- `trend_up AND momentum > theta`

Dieu do van de mo, ve mat nguyen tac:

- `level` nhu context hoac regime signal;
- `momentum` nhu confidence weighting thay vi veto;
- hysteresis nhu hold logic thay vi entry barrier;
- normalized flow nhu state descriptor voi `theta = 0`, khong phai mot strict filter.

Vi vay, buoc tiep theo tu nhien la ablation, khong phai parameter search.

Cau hoi khong con la:

> qvdo parameter nao la tot nhat?

Ma la:

> component nao, neu co, van con gia tri khi bo vai tro hard-thresholded entry di?

---

## X34 Noi Voi Prior Research Nhu The Nao

### X25 da tung noi headroom cua entry-time volume filtering rat nho

Ket luan cua X25 rat ro:

- volume/taker-buy information tai BTC H4 entry da gan nhu bi khai thac het boi setup hien tai;
- `VDO > 0` kha nang da capture phan lon usable entry-time volume information;
- next marginal alpha khong nam o entry filtering.

Nguon:
- `research/x25/04_go_no_go.md`
- `research/x25/07_final_report.md`

Cau key cua X25 nen duoc xem nhu prior:

> "VDO is not being replaced. The next marginal alpha is not in entry filtering."

X34 khong chi lap lai ket luan do.
No stress-test ket luan do bang mot candidate manh hon:

- quote-notional thay cho base-volume ratio;
- adaptive threshold thay cho fixed zero;
- tach level/state ro rang;
- robust scale.

Va ngay ca nhu vay, candidate van fail neu dung nhu mot always-on entry gate.

Dieu nay lam manh hon dang ke broader thesis.

### X27 tung canh bao: regime conditioning co the "dung ve mat phan phoi" nhung van hai strategy

X27 tim thay D1 regime conditioning co real distributional effect, nhung van hurt average Sharpe tren tap pairs duoc test.

Prior nay quan trong vi X34 co cung mot danger structure:

- conditional behavior nhin ra duoc;
- nhung conditional behavior khong dong nghia voi deployed strategy tot hon.

Vi vay, ngay ca neu X34 ve sau yield ra mot regime-switch branch, branch do cung phai bi nghi ngo manh.

Bai hoc dung la:

> co structure co dieu kien trong du lieu khong dong nghia co mot conditional actuator co loi trong strategy.

---

## Con Duong Nghien Cuu Tiep Theo Nen La Gi

### 1. Dung `c_ablation` nhu mot falsification gate, khong phai optimization program

Cau hoi chua duoc giai dap quan trong nhat la failure den tu:

- normalized input `x_t`;
- adaptive threshold `theta`;
- hay interaction giua chung.

Do la ly do A3 va A5 quan trong.

Nhung muc dich cua A3/A5 khong phai la "cuu Q-VDO-RH bang moi gia".
Muc dich cua chung la quyet dinh statement lon nao dung:

- positive thresholding moi la van de that su;
- normalized flow moi la van de that su;
- hay ca hai deu khong dang mang di tiep.

Day la theory test, khong phai tuning sweep.

### 2. Neu A5 thua E0, hay escalate ket luan, dung escalate search

Neu `VDO + adaptive theta` thua ro plain E0, ham y rat lon:

> threshold ban than no lam hong phan entry information huu dung da co san trong VDO.

Luc do, buoc dung khong phai la tim `k` tot hon.
Buoc dung la nang muc tu tin vao larger thesis rang positive thresholding tai entry la huong sai tren BTC spot.

### 3. Neu co component nao song sot, hay doi vai tro cho no

Neu mot component nao do song sot qua ablation, hay mac dinh no chi "vo toi" trong vai tro yeu hon:

- state descriptor;
- regime/context variable;
- confidence modifier;
- hold-management input.

No khong nen tu dong duoc cap lai quyen tro thanh always-on hard veto, tru khi no vuot qua mot burden of proof manh hon rat nhieu.

### 4. Chuyen marginal effort sang nhung alpha surface lon hon

Neu doc X34 cung voi X25, research implication duoc sap hang kha ro:

1. cost reduction va execution quality;
2. longer-horizon hoac structurally different regime research;
3. different instrument structure;
4. chi sau do moi quay lai xem co component nao cua X34 dang duoc tai su dung co kiem soat.

Day la larger-path answer.
No khong anti-research.
No la cach phan bo lai research budget ve nhung noi co expected payoff cao hon.

---

## Dieu Gi Se Lam Thesis Nay Sai

Memo nay co chu y viet manh, nen no phai tu khai bao failure conditions cua chinh no.

Larger-path thesis can duoc sua neu mot trong cac dieu sau xay ra:

1. `A5` danh bai E0 mot cach ro rang.
   Khi do adaptive thresholding tren mot signal VDO da huu dung se chung minh duoc gia tri that.

2. `A3` hoac mot stripped variant khac theo kip E0 trong khi giu duoc upside tot hon.
   Khi do van de se la Q-VDO-RH construction cu the, khong phai lop thresholded flow filtering rong hon.

3. Mot regime-switch implementation xay tren component con song sot pass WFO va full validation ma khong phai tra gia bang bull alpha destruction.

4. Mot per-trade attribution study trong tuong lai cho thay cac entry bi cat bo boi flow gating thuc ra tap trung vao low-value tail, khong phai vao nhung winners outsized dang co ve bi mat.

Cho toi khi mot trong cac dieu do xay ra, burden of proof da doi chieu.

Default stance nen la:

- dung mac dinh flow confirmation selectivity cao hon se tot hon;
- hay mac dinh no co toi cho toi khi no tu chung minh duoc bang trade-level va OOS evidence.

---

## Ket Luan Cuoi

X34 nen duoc doc nhu mot ket qua nghien cuu ve gioi han cua entry filtering tren BTC spot, khong chi nhu mot attempt that bai de thay VDO.

Dong gop sau nhat cua no la:

> Mot flow signal giau hon va mot threshold "thong minh" hon van co the la doi tuong toi uu sai, neu alpha cua he thong song dua vao viec giu du de permissive de bat nhung trend entry outsized.

Do moi la con duong lon hon.

No co nghia cau hoi nghiem tuc tiep theo khong phai la:

> "Lam the nao de Q-VDO-RH thang?"

Ma la:

> "Lieu chung ta da co du bang chung de nghi rang hard-thresholded entry filters da gan sat tran, va neu flow features con gia tri thi gia tri do phai duoc trich ra duoi dang context, khong phai veto?"

X34 chua dong hoan toan cau hoi do.
Nhung no da day burden of proof di rat xa theo huong do.
