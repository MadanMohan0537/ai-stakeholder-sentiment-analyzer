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
