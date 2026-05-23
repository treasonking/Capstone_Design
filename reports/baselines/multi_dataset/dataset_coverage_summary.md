# Multi-Dataset External Baseline Coverage

This coverage summary supports comparison baseline selection and execution pipeline preparation. It is not a final PIGuard / Prompt Guard 2 / ProtectAI detector performance result.

| Dataset | Method | Evaluation scope | Input rows | Result rows | Error count |
|---|---|---|---:|---:|---:|
| deepset | Shared dataset | Common-format input | 100 | 100 | 0 |
| deepset | Capstone Hybrid Proxy | Local full evaluation | 100 | 100 | 0 |
| deepset | Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | 75 | 75 | 0 |
| deepset | Attention Tracker | Related-work local attempt, excluded from main comparison | 100 | 75 | 25 |
| deepset | PIGuard | Pending / Not measured | 100 | 0 | 100 |
| deepset | Meta Prompt Guard 2 | Pending / Not measured | 100 | 0 | 100 |
| deepset | ProtectAI detector | Pending / Not measured | 100 | 0 | 100 |
| ProtectAI | Shared dataset | Common-format input | 100 | 100 | 0 |
| ProtectAI | Capstone Hybrid Proxy | Local full evaluation | 100 | 100 | 0 |
| ProtectAI | Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | 0 | 0 | 0 |
| ProtectAI | Attention Tracker | Related-work local attempt, excluded from main comparison | 100 | 0 | 100 |
| ProtectAI | PIGuard | Pending / Not measured | 100 | 0 | 100 |
| ProtectAI | Meta Prompt Guard 2 | Pending / Not measured | 100 | 0 | 100 |
| ProtectAI | ProtectAI detector | Pending / Not measured | 100 | 0 | 100 |
| Lakera | Shared dataset | Common-format input | 100 | 100 | 0 |
| Lakera | Capstone Hybrid Proxy | Local full evaluation | 100 | 100 | 0 |
| Lakera | Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | 0 | 0 | 0 |
| Lakera | Attention Tracker | Related-work local attempt, excluded from main comparison | 100 | 0 | 100 |
| Lakera | PIGuard | Pending / Not measured | 100 | 0 | 100 |
| Lakera | Meta Prompt Guard 2 | Pending / Not measured | 100 | 0 | 100 |
| Lakera | ProtectAI detector | Pending / Not measured | 100 | 0 | 100 |
