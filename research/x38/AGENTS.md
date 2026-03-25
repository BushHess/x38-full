# Project Instructions

X38 là nghiên cứu **thiết kế kiến trúc** — sản phẩm là đặc tả (blueprint),
KHÔNG phải code. Không cần Python environment.

## ⚠️ Đọc trước tiên

**[docs/online_vs_offline.md](./docs/online_vs_offline.md)** — Phân biệt Online
(gen1/gen2/gen3/gen4 = AI chat) vs Offline (Alpha-Lab = deterministic code pipeline).
Gen1/gen2/gen3/gen4 là evidence về VẤN ĐỀ, KHÔNG phải template cho giải pháp offline.
Nhầm lẫn này là lỗi nghiêm trọng nhất agent có thể mắc trong debate x38.

## Bắt đầu từ đây

1. Đọc [docs/online_vs_offline.md](./docs/online_vs_offline.md) — **BẮT BUỘC** — phân biệt online/offline
2. Đọc [x38_RULES.md](./x38_RULES.md) — quy tắc và phạm vi
3. Đọc [PLAN.md](./PLAN.md) — master plan + bối cảnh đầy đủ
4. Đọc [docs/design_brief.md](./docs/design_brief.md) — input chính thức cho debate (authoritative nếu mâu thuẫn với PLAN.md)
5. Đọc [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) — trạng thái hiện tại + phase đang chạy
6. Đọc [debate/rules.md](./debate/rules.md) — quy tắc tranh luận

## Environment Boundaries

X38 lives inside the btc-spot-dev repository.

- Primary working directory for x38 tasks:
  `/var/www/trading-bots/btc-spot-dev/research/x38/`

- Git repository root:
  `/var/www/trading-bots/btc-spot-dev/`
  (`.git` lives here)

- Shared Python/project root:
  `/var/www/trading-bots/`

Operational rules:
- For file reads/writes in x38, prefer working inside:
  `/var/www/trading-bots/btc-spot-dev/research/x38/`
- For git commands, run them against the btc-spot-dev repo root, for example:
  `git -C /var/www/trading-bots/btc-spot-dev status`
- Do NOT assume `/var/www/trading-bots/` is the git root.
  The git root is `/var/www/trading-bots/btc-spot-dev/`.
- If a Python command needs the shared environment or top-level imports,
  launch it from `/var/www/trading-bots/` or set paths explicitly.
- When citing paths in artifacts, use absolute paths if environment ambiguity is possible.
