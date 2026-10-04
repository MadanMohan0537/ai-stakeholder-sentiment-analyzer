# Signal — AI stakeholder sentiment analyzer

Signal organizes expressed stakeholder feedback by project topic, sentiment, and urgency. Review exact evidence quotes, correct classifications, and export a concern report without treating text labels as measurements of a person’s emotions or performance.

Built with Python, Gradio, SQLite, and optional schema-validated AI generation. Each repository is self-contained and includes sample inputs, editable results, exports, a setup launcher, and automated tests.

**No API key is required to start.** Offline demo mode uses deterministic rules or templates; it is explicitly not an AI model. Genuine AI generation uses your local Ollama model, DeepSeek, or another explicitly configured OpenAI-compatible API.

## Review a concern before acting on it

Start with an [included example](examples/), inspect each supporting quote, correct any topic or urgency labels, then export the concern report. Labels describe the supplied text, not a stakeholder's personality, internal emotions or job performance.

Choose offline demo mode for a reproducible rules-based walkthrough. Choose a configured model only when you intend to send the supplied text to that endpoint. A local Ollama setup and a hosted provider have different data boundaries.

For setup, begin with [the launcher](run.py). Use [verification guidance](VERIFICATION.md), [example verification](verify_example.py) and [tests](tests/) to inspect behavior beyond the interface.

## What you can do

- Analyze stakeholder feedback from a CSV upload or pasted CSV.
- Classify expressed sentiment as positive, negative, mixed, neutral, or unclear.
- Tag timeline, budget, scope, quality, communication, and general topics.
- Show urgency and suggested follow-up actions for review.
- Preserve exact source quotes and require one finding per source row.
- Chart message counts over time and topic mentions.
- Correct classifications before saving and exporting JSON, CSV, and Markdown.

## Quick start

Requires Python 3.11 or 3.12 and an existing computer. Python 3.12 on Linux was used for verification.

```bash
git clone https://github.com/MadanMohan0537/ai-stakeholder-sentiment-analyzer.git
cd ai-stakeholder-sentiment-analyzer
python run.py
```

Use `python3 run.py` on macOS/Linux if your command is named `python3`. On Windows, you can use `py -3.12 run.py`; PowerShell activation is not required.

The launcher creates a project-specific `.venv`, installs the pinned dependencies when missing, creates `.env` from the free defaults only if it does not already exist, and starts the app. Existing settings and data are preserved. Initial dependency downloads need internet access. Later offline demo runs do not need an inference service or API key. The launcher does not download AI models, enable paid APIs, or deploy a cloud service.

Open **http://127.0.0.1:7864**. Stop the app with Ctrl+C. Each project has its own environment, data folder, and port.

Private repositories require authenticated GitHub access to clone. Alternatively, use GitHub's **Code → Download ZIP**, extract the project, and run `python run.py` inside its folder.

Useful setup commands:

```bash
python run.py --setup-only   # Install dependencies without starting the app
python run.py --check        # Check local Ollama and the configured model
python run.py --smoke-test   # Test one tiny synthetic response with local AI
python run.py --verify-example  # Run this project's sample with real local AI
```

The checks return exit code `0` on success and `1` when setup or inference needs attention. `--check` only reads model metadata. `--smoke-test` uses your local model and compute; it never selects DeepSeek. None of these checks downloads models automatically. `--verify-example` runs this project's synthetic example and checks relevant output constraints without saving application records. A failed check may indicate a model limitation; it does not fall back to a paid API. A missing Ollama service does not prevent offline demo mode from running.

Manual setup is also supported: create a virtual environment with `python -m venv .venv`, install `requirements.txt` with that environment's Python, then run `app.py`. On macOS/Linux use `.venv/bin/python`; on Windows use `.venv\Scripts\python.exe`.

## Try the included workflow

1. Click **Load sample feedback** and then **Analyze stakeholder feedback**.
2. The first message has mixed sentiment about quality and timeline. The blocked security review is marked high urgency.
3. Read the exact evidence beside each classification. The ambiguous final message is marked unclear.
4. Expand **Review and correct classifications** to adjust the JSON.
5. Save the reviewed version, download the exports, and reload it from **Saved reports**.

## Run real AI locally for free

1. Install [Ollama](https://ollama.com/) on your computer.
2. Download a local model:

   ```bash
   ollama pull qwen3:4b
   ```

3. Make sure the Ollama application/service is running. If needed, start `ollama serve` in a separate terminal.
4. Run `python run.py`. The launcher creates `.env` if needed.
5. Expand **Set up free local AI**, click **Check local AI**, then **Test local AI with a sample**. A successful sample confirms a valid structured response, not the accuracy of every future result.
6. Select **Ollama (local)** in the app and run the included project workflow.

The default model is configurable through `OLLAMA_MODEL`. Local mode permits only a loopback Ollama server and rejects cloud model tags. Model size and context length affect RAM use and speed; no GPU purchase is required by the app, but performance depends on your hardware. A model download alone is not a validation of its output quality.

`OLLAMA_CONTEXT` defaults to 16384 tokens. The app reserves output and template space and uses a conservative UTF-8 byte budget to reject oversized input rather than silently discard source text. Shorten inputs first; increase the context only when your hardware supports it. Model outputs must pass a JSON schema before they are used.

## AI providers and API configuration

Choose the setup that fits your hardware, budget, and preferred model. The application is **not restricted to DeepSeek**.

| Analysis mode | What it uses | API key needed? |
| --- | --- | --- |
| **Offline demo** | Deterministic rules or templates; no language model | No |
| **Ollama (local)** | A downloaded model on your computer | No |
| **DeepSeek (opt-in)** | DeepSeek chat API with DeepSeek-specific settings | Yes |
| **Custom API (OpenAI-compatible)** | Your endpoint and model using the chat-completions protocol | Usually; optional for a loopback server |

### Configure an API in the app

1. Start the app and expand **API settings · DeepSeek and custom providers** beneath **Analysis mode**.
2. Set **API base URL** and **Model ID** for your chosen provider.
3. Enter your **API key** in the password-masked field.
4. Enable **I allow API requests that may charge my account** when you intend to generate results. You can leave it disabled to apply settings and check model metadata only.
5. Click **Apply settings**. This does not contact the provider and clears the visible key field.
6. Optionally click **Check API connection** to request the provider's model list.
7. Select **DeepSeek (opt-in)** for the DeepSeek endpoint, or **Custom API (OpenAI-compatible)** for another compatible endpoint, then run the project's workflow.

Use the API base URL, **not** the full `/chat/completions` URL. For example:

| Service | API base URL | Model ID |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com` | A model currently available to your account; the app defaults to `deepseek-flash` |
| OpenAI | `https://api.openai.com/v1` | Your enabled chat-completions model |
| OpenRouter | `https://openrouter.ai/api/v1` | The provider/model ID from its catalog |
| Groq | `https://api.groq.com/openai/v1` | A model from its current catalog |
| Together AI | `https://api.together.xyz/v1` | A supported chat model from its catalog |
| LM Studio or a compatible local server | `http://127.0.0.1:1234/v1` | The loaded model's ID; adjust the port to match your server |

These are configuration examples, not a claim that every model on those services has been tested. Providers control available models, pricing, context limits, and access permissions. Use their current documentation when choosing a model.

### Compatibility and structured output

Custom mode sends `POST {base_url}/chat/completions` with `model`, `messages`, and `stream: false`. When a key is present, it uses `Authorization: Bearer …`. The response must contain `choices[0].message.content` with JSON matching this project's schema.

**Request JSON mode** adds `response_format: {"type": "json_object"}`. Turn it off if your provider or model rejects that option, then apply settings again. The schema remains in the prompt, and the app still validates the returned JSON. Turning off JSON mode does not allow arbitrary prose or malformed results.

Custom mode omits DeepSeek-specific thinking settings and optional sampling/token parameters so models can use their own defaults. A model that only supports a different protocol, special headers, an incompatible response shape, or a separate Responses API needs an adapter or a compatible gateway. Native Anthropic Messages and provider-specific Azure deployments are not directly supported by this adapter.

The connection check uses `GET {base_url}/models` without requesting generation. Some otherwise compatible services do not implement that endpoint; a 404/405 is reported without claiming generation cannot work. A successful metadata check does not establish sufficient balance, generation quality, or schema accuracy.

### Keys, sessions, and costs

- Applied keys stay in server memory for the browser session, for up to one hour after applying settings. Reloading, expiry, or restarting requires applying settings again.
- Keys are excluded from SQLite records, report history, exports, and source files. Entering a key in the app never writes `.env`.
- To change the model or JSON/usage options, leave the key field blank and apply again. If you change the endpoint, re-enter its key; the app will not silently forward an existing key to a new endpoint.
- **Clear session key** removes the applied credential and disables API generation. It does not cancel requests already in progress.
- Remote endpoints require HTTPS. HTTP is accepted only for loopback servers, where an API key is optional. API requests still require explicit opt-in, including for a free local compatible server.
- Remote generation sends project input to the selected provider and may incur charges. Offline demo and Ollama remain the paths without hosted API usage. There is no automatic paid-provider fallback.

### Optional environment configuration

The UI can use an existing local key: select **Use the key configured in my local .env instead** and click **Apply settings**. A DeepSeek endpoint uses `DEEPSEEK_API_KEY`; other endpoints use `AI_API_KEY`. Set the endpoint and model in the UI as well. Each browser session requires its own usage opt-in, regardless of environment flags.

For direct Python/script use, DeepSeek settings are:

```dotenv
ALLOW_PAID_API=true
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-flash
```

For direct Python/script use with `Custom API (OpenAI-compatible)`:

```dotenv
ALLOW_PAID_API=true
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=your_key_here
AI_MODEL=your_model_id
AI_JSON_MODE=true
```

Never commit a real key. `.env` is ignored; `.env.example` contains placeholders and free defaults. Review your provider's prices and data policies before using it.

## Input format

Dates must be real calendar dates in exactly `YYYY-MM-DD` format. Compact dates such as `20261005` and week dates such as `2026-W41-1` are rejected.

CSV imports require unique, nonempty column headers and valid quoting; duplicate columns are never silently overwritten. The CSV size limit counts UTF-8 bytes.

CSV columns: `id,date,stakeholder,message`. IDs must be unique, dates use `YYYY-MM-DD`, and messages must be nonempty. Quote CSV fields containing commas. Analyze up to 100 messages per batch, with up to 3,000 characters per message. All supplied messages are included in the AI request, subject to the provider context budget.

Offline concern previews are limited to 1,200 characters and end with an ellipsis when shortened. The original message and evidence quote remain complete in the review table and JSON/CSV exports.

## Data and architecture

| File or folder | Purpose |
| --- | --- |
| `run.py` | One-command environment setup and app launcher |
| `local_ai_check.py` | Local model readiness and optional synthetic inference test |
| `verify_example.py` | Repeatable live local AI check using this project's synthetic example |
| `app.py` | Gradio screens, event wiring, and review/export workflow |
| `domain.py` | Project-specific models, validation, and calculations |
| `api_settings.py` | Session credentials, endpoint validation, and metadata connection checks |
| `ai.py` | Ollama, DeepSeek, and custom chat-completions adapters with schema validation |
| `common.py` | SQLite persistence, input validation, and safe CSV exports |
| `ui.py` | Shared-in-this-repository visual helpers and local launch settings |
| `examples/` | Synthetic sample inputs |
| `tests/` | Domain, provider-contract, and UI workflow tests |
| `data/` | Runtime database and exports; created locally and ignored by Git |

This repository is self-contained; no sibling repository or hosted database is required. `APP_DATA_DIR` can override the data folder. Back up the data directory while the app is stopped. Reports and exports are retained until you remove them. Each export receives a unique filename. CSV exports escape cells that could be interpreted as spreadsheet formulas.

The server binds to `127.0.0.1`, Gradio sharing is off, and analytics are disabled. This is an unauthenticated single-user local app. Do not expose it to the public internet without adding authentication, access controls, deployment hardening, and a persistence plan. No cloud deployment, paid service, or automatic GitHub Actions runner is configured.

## Tests

Run `python run.py --setup-only` first if the project environment does not exist.

```bash
# macOS / Linux
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

```powershell
# Windows
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary data directories and mocked provider responses. They exercise validation, failure handling, persistence, and the sample UI callbacks without purchasing API usage. Live Ollama/DeepSeek model quality is not verified by those tests. See [VERIFICATION.md](VERIFICATION.md) for the delivered verification scope.

## Limitations

Offline mode uses a small English keyword lexicon and limited negation rules. It is not a trained sentiment model and can misread context, sarcasm, dialect, or mixed clauses. AI mode still requires review. Labels describe expressed text, not a person's feelings, intent, trustworthiness, or performance. Charts show message counts, not calibrated psychological scores; topics can overlap. Suggested follow-ups are never sent. Use only feedback you are authorized to process.

## Troubleshooting

- **Port already in use:** set `PORT` to an unused number in `.env` and restart.
- **Cannot reach Ollama:** run `python run.py --check`, start the Ollama service, and check `OLLAMA_MODEL`.
- **Model missing:** run the `ollama pull` command shown by the readiness check.
- **Installed model cannot generate:** use `python run.py --smoke-test`; a smaller model or shorter input may fit your hardware better.
- **Environment incomplete or Python unsupported:** install Python 3.11 or 3.12, rename the project `.venv`, and rerun the launcher. Keep `.env` and `data/` to preserve settings and records.
- **Invalid structured output:** retry with a shorter input or a more capable local model. Invalid results are not silently accepted.
- **Local context budget exceeded:** split the document or reduce the batch size.
- **API generation blocked:** apply session settings with usage opt-in enabled; script usage requires `ALLOW_PAID_API=true`.
- **Provider rejects JSON mode:** uncheck **Request JSON mode** and apply settings again. Output must still be valid schema-matching JSON.
- **Wrong endpoint or model:** use a base URL without `/chat/completions` and a model ID offered by that endpoint.
- **Endpoint changed:** re-enter its API key before applying settings.
- **Changed `.env` values not taking effect:** restart the application.

## Development and contributions

Use the tests above before proposing a change. Keep project calculations and validation in `domain.py`, provider request logic in `ai.py`, credential handling in `api_settings.py`, and interface wiring in `app.py`/`ui.py`. Provider tests mock HTTP calls so contributing does not require API spending.

To add a native API adapter, add an explicit provider choice, translate the existing messages and schema into that provider's request, and pass its output through the same schema validation. Include tests for its authentication, error responses, incomplete output, and session isolation. Never put credentials into report context or introduce automatic paid fallbacks.

## License

MIT. Dependencies and model weights retain their own licenses. See [LICENSE](LICENSE).
