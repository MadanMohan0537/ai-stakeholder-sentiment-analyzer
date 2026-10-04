# Verification scope

- Domain tests cover calculations, validation, and relevant failure cases.
- Provider-contract tests validate request construction and structured responses using mocked HTTP calls.
- Paid API use is blocked by default and local mode rejects remote URLs.
- UI smoke tests construct the Gradio interface and execute each app's primary sample workflow through its Python callbacks, including local persistence and export creation.
- No live DeepSeek requests were made. No inference costs were incurred.
- Live Ollama inference and optional audio transcription require separately installed model weights and have not been quality-benchmarked in this environment.

Run `python -m pytest -q` to repeat the automated checks. Results from an offline template or heuristic must not be presented as model-generated results.

Delivered check results (Python 3.12 on Linux): **27 automated tests passed** in this repository; **136 tests passed** across the five separate projects.

The follow-up checks cover the one-command launcher, preservation of existing settings, missing dependencies and failed installs, local model availability, absent services, invalid configuration, paid-provider isolation, and incomplete model responses. The app's existing sample workflow and export callbacks still pass.

All five apps were started as local HTTP servers. Their primary queued workflows and both local-AI setup controls were exercised through the Gradio client. The setup controls used a local test server with an empty model list so missing-model handling was checked without downloading weights or incurring inference costs.

The shared launcher was additionally exercised end to end on the meeting app in a fresh temporary folder containing spaces, from a different working directory. It created a real virtual environment, installed dependencies, preserved the generated settings on a second invocation, and launched the actual app. Windows and macOS launch paths are implemented but were not executed on those operating systems.

`python run.py --smoke-test` is available for a real local model check on your computer. Automated provider tests use simulated responses; live Ollama inference, DeepSeek usage, and audio model quality remain unverified here. No paid API requests were made.

## Continuation verification — 2026-10-04

Python 3.12 on Linux: **37 tests passed** in this repository; **174 tests passed** across all five projects. This run includes the existing launcher, provider, persistence, export, and UI callback checks.

New regression checks enforce real calendar dates in exactly `YYYY-MM-DD` format, including rejection of compact and ISO week dates that Python otherwise accepts. This prevents inconsistent date ordering in scheduling and allocation.

Long negative, question, and ambiguous feedback now completes the offline workflow with a shortened concern preview while preserving the full 3,000-character message and evidence. The ambiguous phrase “Fine, I guess” is also covered.

No live model inference or paid API requests were made during this continuation.

## Input and lifecycle regression pass

After merging the newer repository commits: **44 tests passed** here and **214 tests passed** across all five projects, on Python 3.12/Linux.

The additional tests cover strict calendar dates, duplicate/empty CSV headers, malformed quoting, UTF-8 byte limits, long report excerpts, conservative owner/date evidence, long feedback, and safe archive restoration as applicable to each app. All existing domain and callback workflows still pass.

A real local Ollama verification was attempted using Ollama 0.35.1. The runtime started, but downloading the local model was blocked by this environment's network restriction on the storage redirect. **No live model inference completed.** The failure was not worked around with a paid provider.

Use `python run.py --verify-example` on a computer with a downloaded Ollama model to repeat the project's example checks. It uses synthetic data, never selects DeepSeek, and does not save application records. A passing sample is an integration check, not a general accuracy benchmark. The existing `--smoke-test` remains the smaller structured-response check.

The new example command was exercised through the launcher for all five apps against a simulated local HTTP provider. Success returned exit code 0 without creating application records; a semantically incomplete meeting result correctly returned exit code 1. These checks validate the command and error path, not live model accuracy.

## In-app API settings verification — 2026-10-04

Python 3.12 on Linux: **60 automated tests passed** here; **294 passed** across the five repositories.

The API settings tests cover masked key entry, explicit environment-key selection, retained keys when editing settings, clear/replacement behavior, paid-request gating, model overrides, concurrent request isolation, and context cleanup after errors. Model-list checks use mocked success, missing-model, authentication, timeout, and malformed responses without requesting generation.

Gradio's actual event dispatcher is exercised with separate browser session states. An applied test key reaches every project AI action, including meeting questions and planning revisions, while remaining absent from response data and another session. Generated results are saved and exported, and database/export files are checked for key leakage. Existing offline, launcher, persistence, and validation tests also pass.

All DeepSeek responses in these checks are mocked. No real key was supplied and no live paid API requests were made. Actual account authorization, balance, and generation quality are not established by these tests.
