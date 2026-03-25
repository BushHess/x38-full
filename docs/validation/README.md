# Validation Docs

Bộ tài liệu chuẩn để theo dõi và audit validation pipeline.

## Mục lục

- [Decision Policy](decision_policy.md)
- [Output Contract](output_contract.md)
- [Validation Changelog](validation_changelog.md)
- [Threshold Governance](THRESHOLD_GOVERNANCE_POLICY.md)
- [Pair Review Workflow](pair_review_workflow.md)
- [Golden Template](golden_template.yaml)

## Cách dùng

1. Dùng [Validation CLI](validation_cli.md) để chạy lệnh.
2. Đối chiếu verdict bằng `reports/decision.json` theo [Decision Policy](decision_policy.md).
3. Kiểm tra đủ artifacts bằng [Output Contract](output_contract.md).
4. Khi thay đổi logic/suite/contract, ghi vào [Validation Changelog](validation_changelog.md).

