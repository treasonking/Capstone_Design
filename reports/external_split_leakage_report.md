# External Split Leakage Report

- Generated at: `2026-05-18T22:03:31`
- Random seed: `42`
- Train/eval id overlap: `0`
- Train/eval normalized text-hash overlap: `42`

## Leakage Summary

| Dataset | Exact Text Overlap | Near Duplicate Count >= 0.95 | Note |
|---|---:|---:|---|
| `Lakera/gandalf_ignore_instructions` | 1 | N/A | exact normalized text-hash check only |
| `deepset/prompt-injections` | 0 | 4 | deepset train/eval injection and safe pairs checked with SequenceMatcher |
| `protectai/prompt-injection-validation` | 41 | N/A | exact normalized text-hash check only |

## Near Duplicate Examples

| Label | Similarity | Train ID | Eval ID |
|---|---:|---|---|
| injection | 0.9661 | `deepset/prompt-injections:deepset-test-00008` | `deepset/prompt-injections:deepset-test-00107` |
| injection | 0.9725 | `deepset/prompt-injections:deepset-train-00338` | `deepset/prompt-injections:deepset-train-00493` |
| injection | 0.9588 | `deepset/prompt-injections:deepset-train-00530` | `deepset/prompt-injections:deepset-train-00490` |
| injection | 0.9797 | `deepset/prompt-injections:deepset-train-00533` | `deepset/prompt-injections:deepset-train-00493` |

## Interpretation

- Exact text overlap uses SHA-256 over normalized lowercase whitespace-collapsed text.
- Near duplicate check is intentionally limited to `deepset/prompt-injections` and same-label train/eval pairs.
- If exact overlap or many near duplicates appear, custom split metrics may overestimate true generalization and official split results should be preferred.
