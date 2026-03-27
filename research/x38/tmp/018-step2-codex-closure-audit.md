# Step 2 — Codex Closure Audit + Judgment-Call Documentation

Paste this prompt into a **Codex session** (e.g., ChatGPT with Codex instructions).
This is read-only — it produces an advisory document, does not modify any files.

---

```
Role: Codex (advisor for closure)
Task: Closure audit and judgment-call documentation for
      debate/018-search-space-expansion/, after Round 6 (max rounds reached)
Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07,
       SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/codex/judgment-call-memo.md
Read-only — do not modify any existing files.

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root.

CONTEXT — THIS MEMO ALSO SERVES AS CLOSURE AUDIT:
The existing `closure-audit.md` (2026-03-26) covers the prior 4-agent
extra-canonical debate and is STALE. This memo replaces it as the authoritative
audit record for the standard 2-agent debate (6 rounds, claude_code + codex).

CONTEXT — HUMAN RESEARCHER JUDGMENT ON SSE-D-05:
The human researcher has decided SSE-D-05 as follows. This is final and not
subject to review. Document it accurately.

    Type: Judgment call (Round 6)
    Decision: Hybrid — Reviewer correct on status (Judgment call, not
    Converged); Author correct on handoff value (named working minimum
    inventory needed for downstream consumption).

    Content:
    - Topic 018 locks pre-freeze recognition topology:
      surprise_queue → equivalence_audit → proof_bundle → freeze
    - Topic 018 adopts a working minimum inventory for handoff:
      * 5 anomaly axes: decorrelation_outlier, plateau_width_champion,
        cost_stability, cross_resolution_consistency, contradiction_resurrection
      * 5 proof components: nearest_rival_audit, plateau_stability_extract,
        cost_sensitivity_test, dependency_stressor, contradiction_profile
      * Proof item 4: family-level name = dependency_stressor;
        ablation_or_perturbation_test is a valid alias/concrete form
    - NOT described as immutable historically-converged exact label set
    - Topology stops at freeze — does NOT extend to freeze_comparison_set →
      candidate_phenotype → contradiction_registry (overreach per live row)
    - Thresholds and proof-consumption rules: owned by 017/013
    - Expansion beyond this minimum: requires explicit downstream finding

    Rationale: Authoritative evidence locks pre-freeze topology and minimum
    5+5 floor, but archive shows material label drift (4-dimension → 5-axis,
    "dependency stressor" vs "ablation_or_perturbation_test", ChatGPT Pro
    deferred exact taxonomy downstream). Pure Converged overstates evidence
    convergence. Pure "unnamed 5+5 family" is operationally too weak for
    017/013 handoff (they already reference named axes/components). Hybrid
    adopts named working inventory at Judgment call authority level.

Read all files in this order:
  1. AGENTS.md, docs/online_vs_offline.md, x38_RULES.md, debate/rules.md
  2. debate/018-search-space-expansion/README.md
  3. debate/018-search-space-expansion/findings-under-review.md
  4. debate/018-search-space-expansion/final-resolution.md (NON-AUTHORITATIVE)
  5. debate/018-search-space-expansion/closure-audit.md (STALE)
  6. ALL round files in debate/018-search-space-expansion/claude_code/ (rounds 1-6)
  7. ALL round files in debate/018-search-space-expansion/codex/ (rounds 1-6)
  8. debate/017-epistemic-search-policy/findings-under-review.md (downstream ref)
  9. docs/search-space-expansion/debate/ archive (non-authoritative evidence):
     - claude/claude_debate_lan_3.md, claude_debate_lan_4.md, claude_debate_lan_6.md
     - chatgptpro/chatgptpro_debate_lan_4.md, chatgptpro_debate_lan_5.md
     - codex/codex_debate_lan_4.md, codex_debate_lan_6.md

Produce the following sections:

1. PER-ISSUE SUMMARY
   | Issue ID | Finding | Final positions | Agreement level | Resolution |
   Assess each issue separately (SSE-D-01 through SSE-D-11).
   Agreement levels: Converged (§7 complete), Near-converged, Disputed.
   For SSE-D-05: record the human researcher's judgment as stated above.

2. STEEL-MAN AUDIT
   - Which issues completed §7(a)(b)(c)?
   - Which have incomplete steel-man? (cite specific round)

3. CROSS-TOPIC IMPACT CHECK
   For each downstream topic receiving routing from 018:
   - Topic 006: generation_mode (SSE-D-03)
   - Topic 015: lineage (SSE-D-07) + contradiction registry (SSE-D-08)
   - Topic 017: surprise topology (SSE-D-05) + contradiction consumption (SSE-D-08-CON)
   - Topic 013: multiplicity control (SSE-D-09)
   - Topic 008: identity_vocabulary (SSE-D-04 field 3)
   - Topic 003: breadth-activation blocker (SSE-D-04)

4. STATUS DRIFT CHECK
   Compare findings-under-review.md against actual round outcomes.
   Flag discrepancies.

5. CLOSURE AUDIT (replaces stale closure-audit.md)
   Verify:
   a. Termination: max_rounds_per_topic = 6 reached (debate/rules.md §13)
   b. Round symmetry: both agents have 6 rounds (§14b satisfied)
   c. All issues: Converged or Judgment call (§14 prerequisite met)
   d. Human researcher has decided SSE-D-05 (§15 prerequisite met)
   e. Steel-man protocol compliance per issue (§7)
   f. Cross-topic tensions documented (§22)
   g. Downstream routing complete with issue IDs

   Final audit verdict: PASS / FAIL / CONDITIONAL

Do not:
  - Make final decisions (the human researcher has already decided)
  - Propose consensus or compromise positions
  - Write to any file other than the output path above
  - Override or second-guess the human researcher's SSE-D-05 judgment
```
