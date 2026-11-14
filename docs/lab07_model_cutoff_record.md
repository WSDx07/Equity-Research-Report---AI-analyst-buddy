# Lab 07 Model Cutoff Record

Checked: 2026-11-13

## Agent team model

- Project: `desk_flow.py`
- Configured model: `gpt-oss:120b`
- Configuration: `PURDUE_MODEL` is unset in the project `.env`. The code defaults to `gpt-oss:120b` in `desk_flow.py` (lines 57 and 138).
- Provider route: `Purdue/gpt-oss:120b`, confirmed by the captured stateless request.

## Model self-report

The model was asked in stateless requests with no browsing or external tools. The first response could not be captured because of Windows console encoding. The self-report below is from the repeated request.

- Self-reported name: `ChatGPT (based on GPT-4 architecture)`
- Self-reported cutoff: `2024-06`
- Reliability note: the self-reported name does not match the configured model ID, `gpt-oss:120b`. Treat the self-report as unverified. It gave the cutoff month, not an exact day.

## Provider documentation

OpenAI's official [gpt-oss-120b model page](https://developers.openai.com/api/docs/models/gpt-oss-120b) lists a knowledge cutoff of **June 1, 2024**.

## Cutoff to record for Lab 07

**June 1, 2024**, based on the official OpenAI model documentation for `gpt-oss-120b`. The captured request went to the Purdue endpoint with the configured `gpt-oss:120b` model ID. The model's self-report agreed on the month, but gave an incorrect model identity and no exact day.
