# External Prompt Injection False Negative Analysis

## Purpose

This document tracks false negative samples from public prompt injection datasets. The goal is to identify missing attack patterns and improve detector coverage.

## Summary

| Dataset | FN Count | Main Missing Pattern | Planned Rule/Model Improvement |
|---|---:|---|---|
| deepset/prompt-injections | 243 | TBD | Expand English injection patterns |
| protectai/prompt-injection-validation | 1142 | TBD | Add classifier-based detection |
| Lakera/gandalf_ignore_instructions | 552 | TBD | Improve ignore-instruction attack coverage |

## Sample Storage

Up to 50 false negative and false positive previews per dataset are stored in `reports/external_prompt_injection_errors.json`. Text is truncated to avoid storing unnecessary full prompt content.

## Analysis Categories

False negative samples should be categorized into the following types.

| Category | Description | Example Pattern |
|---|---|---|
| Direct override | Explicitly ignores prior instructions | ignore previous instructions |
| Role manipulation | Assigns a new unsafe role to the model | you are now unrestricted |
| System prompt extraction | Requests hidden system/developer messages | reveal your system prompt |
| Policy bypass | Asks to disable safety or filtering | turn off the filter |
| Indirect injection | Attack is embedded in a task/document | summarize this document and follow the hidden instruction |
| Encoding/obfuscation | Attack uses spacing, symbols, encoding, or mixed language | i g n o r e, base64-like text |
| Goal hijacking | Replaces the original user task with another goal | instead of the task, do this |