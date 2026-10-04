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

Requires Python 3.11 or 3.12 and an existing computer. The project was verified with Python 3.12. Initial dependency and model downloads require internet access. Once installed, offline workflows do not require an inference service.

```bash
git clone https://github.com/MadanMohan0537/ai-stakeholder-sentiment-analyzer.git
cd ai-stakeholder-sentiment-analyzer
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Then install and run:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:7864**. Stop the app with Ctrl+C. The five projects use separate default ports and can run independently. You can also use `.venv\Scripts\python.exe app.py` on Windows without activating the environment.

Private repositories require your own authenticated GitHub access to clone. Alternatively, use GitHub's **Code → Download ZIP**, extract the project, and run the same setup commands inside its folder.

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
4. Copy `.env.example` to `.env` (`cp .env.example .env` on macOS/Linux; `Copy-Item .env.example .env` in PowerShell).
5. Select **Ollama (local)** in the app.

The default model is configurable through `OLLAMA_MODEL`. Local mode permits only a loopback Ollama server and rejects cloud model tags. Model size and context length affect RAM use and speed; no GPU purchase is required by the app, but performance depends on your hardware. A model download alone is not a validation of its output quality.

`OLLAMA_CONTEXT` defaults to 16384 tokens. The app reserves output and template space and uses a conservative UTF-8 byte budget to reject oversized input rather than silently discard source text. Shorten inputs first; increase the context only when your hardware supports it. Model outputs must pass a JSON schema before they are used.

## Optional DeepSeek API

DeepSeek's hosted API may charge per token. This is not part of the strict $0 path. It is disabled even if a key is present until you explicitly opt in.

In your local `.env`:

```dotenv
ALLOW_PAID_API=true
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-flash
```

Select **DeepSeek (opt-in)** only if you intend to use that account's allowance or balance. Source content is sent to DeepSeek when you select this mode and run generation. Check the [current pricing](https://api-docs.deepseek.com/quick_start/pricing/) and model availability. There is no automatic fallback to a paid provider. Never put a real key in source files or GitHub; `.env` is ignored.

## Input format

CSV columns: `id,date,stakeholder,message`. IDs must be unique, dates use `YYYY-MM-DD`, and messages must be nonempty. Quote CSV fields containing commas. Analyze up to 100 messages per batch, with up to 3,000 characters per message. All supplied messages are included in the AI request, subject to the provider context budget.

## Data and architecture

| File or folder | Purpose |
| --- | --- |
| `app.py` | Gradio screens, event wiring, and review/export workflow |
| `domain.py` | Project-specific models, validation, and calculations |
| `ai.py` | Explicit Ollama/DeepSeek adapters and JSON schema validation |
| `common.py` | SQLite persistence, input validation, and safe CSV exports |
| `ui.py` | Shared-in-this-repository visual helpers and local launch settings |
| `examples/` | Synthetic sample inputs |
| `tests/` | Domain, provider-contract, and UI workflow tests |
| `data/` | Runtime database and exports; created locally and ignored by Git |

This repository is self-contained; no sibling repository or hosted database is required. `APP_DATA_DIR` can override the data folder. Back up the data directory while the app is stopped. Reports and exports are retained until you remove them. Each export receives a unique filename. CSV exports escape cells that could be interpreted as spreadsheet formulas.

The server binds to `127.0.0.1`, Gradio sharing is off, and analytics are disabled. This is an unauthenticated single-user local app. Do not expose it to the public internet without adding authentication, access controls, deployment hardening, and a persistence plan. No cloud deployment, paid service, or automatic GitHub Actions runner is configured.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use temporary data directories and mocked provider responses. They exercise validation, failure handling, persistence, and the sample UI callbacks without purchasing API usage. Live Ollama/DeepSeek model quality is not verified by those tests. See [VERIFICATION.md](VERIFICATION.md) for the delivered verification scope.

## Limitations

Offline mode uses a small English keyword lexicon and limited negation rules. It is not a trained sentiment model and can misread context, sarcasm, dialect, or mixed clauses. AI mode still requires review. Labels describe expressed text, not a person's feelings, intent, trustworthiness, or performance. Charts show message counts, not calibrated psychological scores; topics can overlap. Suggested follow-ups are never sent. Use only feedback you are authorized to process.

## Troubleshooting

- **Port already in use:** set `PORT` to an unused number in `.env` and restart.
- **Cannot reach Ollama:** start the Ollama service, run `ollama list`, and check `OLLAMA_MODEL`.
- **Invalid structured output:** retry with a shorter input or a more capable local model. Invalid results are not silently accepted.
- **Local context budget exceeded:** split the document or reduce the batch size.
- **DeepSeek blocked:** `ALLOW_PAID_API=false` is the intended free default.
- **Changed `.env` values not taking effect:** restart the application.

## License

MIT. Dependencies and model weights retain their own licenses. See [LICENSE](LICENSE).
