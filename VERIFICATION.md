# Verification scope

- Domain tests cover calculations, validation, and relevant failure cases.
- Provider-contract tests validate request construction and structured responses using mocked HTTP calls.
- Paid API use is blocked by default and local mode rejects remote URLs.
- UI smoke tests construct the Gradio interface and execute each app's primary sample workflow through its Python callbacks, including local persistence and export creation.
- No live DeepSeek requests were made. No inference costs were incurred.
- Live Ollama inference and optional audio transcription require separately installed model weights and have not been quality-benchmarked in this environment.

Run `python -m pytest -q` to repeat the automated checks. Results from an offline template or heuristic must not be presented as model-generated results.

Delivered check results (Python 3.12): 13 automated tests passed. All five apps were also started as local HTTP servers and exercised through the Gradio client, including a primary queued action, session state, and export download. No live model or audio quality claims are implied.
