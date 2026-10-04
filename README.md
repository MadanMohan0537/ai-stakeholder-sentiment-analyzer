# Signal — AI stakeholder sentiment analyzer

A standalone local application built with Python, Gradio, SQLite, and optional structured AI generation. Includes a working offline demonstration, synthetic sample data, editable results, exports, and automated tests.

**No API key is required to start.** Offline demo mode uses deterministic rules or templates; it is explicitly not an AI model. Genuine AI generation uses your local Ollama model, or an explicitly enabled DeepSeek API connection.

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

## Optional DeepSeek API

You can enter your API key directly in the app. No source-code edits or restart are needed.

1. Expand **API settings · DeepSeek** beneath **Analysis mode**.
2. Paste your key into **DeepSeek API key**; the field masks it.
3. Set **DeepSeek model** to a model available to your account.
4. Select **I allow DeepSeek requests that may charge my account** if you want to generate results. Leave it unchecked to configure and check the connection only.
5. Click **Apply settings**. This makes no network request and clears the visible key field.
6. Optionally click **Check API connection**. It reads DeepSeek's model list without requesting generation. It does not verify account balance or model accuracy.
7. Select **DeepSeek (opt-in)** and run the project's AI action. Your project content is sent to DeepSeek for that action.

To change the model or opt-in choice, edit the controls and click **Apply settings** again. Leave the key field blank to retain the applied key, or enter a replacement. Changes take effect when applied. **Clear session key** removes the session credential and disables generation. It does not cancel requests already in progress.

The app retains the applied key only in server memory for that browser session, for up to one hour after applying it. Reloading the page, expiry, or restarting the app requires applying settings again. Keys are not included in report history, SQLite data, exports, source files, or GitHub. Each browser session has separate credentials. This remains a local single-user application, not an authenticated multi-user hosting service.

If you already keep a key in your local `.env`, select **Use the key configured in my local .env instead**, opt in as appropriate, and click **Apply settings**. This uses the configured key without displaying it. Entering a key in the app never writes or changes `.env`. The UI always requires its own opt-in; an environment flag cannot silently enable a new browser session.

For direct Python/script use, the previous environment setup remains available:

```dotenv
ALLOW_PAID_API=true
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-flash
```

DeepSeek's hosted API may charge per token and is outside the strict $0 path. Check [current pricing and model availability](https://api-docs.deepseek.com/quick_start/pricing/). Offline demo and Ollama need no API key, and there is no automatic fallback to a paid provider. Never commit a real key; `.env` is ignored.

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
| `api_settings.py` | Session credential handling and metadata connection checks |
| `ai.py` | Explicit Ollama/DeepSeek adapters and JSON schema validation |
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
- **DeepSeek blocked:** `ALLOW_PAID_API=false` is the intended free default.
- **Changed `.env` values not taking effect:** restart the application.

## License

MIT. Dependencies and model weights retain their own licenses. See [LICENSE](LICENSE).
