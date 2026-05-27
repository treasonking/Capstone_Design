# Multi-Dataset Source Notes

No HuggingFace download was required for this run; all selected rows came from repository-local files.

| Dataset | Source | Split | Original columns | Label mapping | Selected sample count | Note |
|---|---|---|---|---|---:|---|
| deepset | data/external/attention_tracker/shared_prompt_injection_eval.csv | capstone-selected subset | id,text,label,instruction | injection/attack/jailbreak/unsafe=1; safe/benign/normal=0 | 100 | preserves existing deepset selected subset for cross-baseline comparability |
| protectai | datasets/external_splits/eval_external_prompt_injection.jsonl; datasets/external_splits/train_external_prompt_injection.jsonl | repo-local external_splits | id,dataset,text,label | injection/attack/jailbreak/unsafe=1; safe/benign/normal=0 | 100 | balanced attack=50, benign=50 |
| lakera | datasets/external_splits/eval_external_prompt_injection.jsonl; datasets/external_splits/train_external_prompt_injection.jsonl | repo-local external_splits | id,dataset,text,label | injection/attack/jailbreak/unsafe=1; safe/benign/normal=0 | 100 | single-class source; balanced 50/50 subset unavailable |
