# Fieldnote: AI voice mock interviewer

Fieldnote helps you practice technical interviews based on your resume and target role. You can speak or type your answers, work through reasoning exercises, and review a report linked to your interview records. This README explains the project structure and how to run it locally.

## What you can do

An interview combines conversation and practice tasks:

- Upload a text PDF or paste resume text, then edit the claims you want to discuss
- Choose Backend, Frontend, or Full-stack Engineer at junior or intermediate level
- Answer adaptive follow-up questions using voice or text
- Pause, repeat a question, interrupt speech, or correct a transcript
- Investigate authored scenarios through evidence cards and reasoning exercises
- Write Python or C++ solutions in the editor, with execution on a separate isolated runner
- Review factual reports, challenge findings, and practice with coaching

Groq is the default AI provider. You can select OpenRouter or Codex (Luna) in **Settings**. Speech recognition and synthesis run locally; the selected AI provider processes the text needed for the interview.

Automatic technical ratings and adverse labels remain disabled because independent human calibration is unavailable. Reports still include statements, task records, references, and transcript corrections.

## How the project works

The browser connects to a Python API, which stores interviews in a local SQLite database and calls your selected AI provider. Optional local speech services handle microphone input and spoken responses. A separate Ubuntu computer executes submitted code under gVisor isolation.

| Component | Technology | Purpose |
| --- | --- | --- |
| Web app | React, TypeScript, Vite | Interview setup, voice sphere, editor, and reports |
| API server | Python, FastAPI, SQLite | Interview state, providers, and account-scoped storage |
| Account service | Node.js, Better Auth, SQLite | Email/password accounts, profiles, and signed API tokens |
| Local voice | faster-whisper, Kokoro, Pipecat | Speech recognition, speech synthesis, and browser audio transport |
| Code editor | Monaco | Python and C++ editing |
| Dedicated runner | Docker and gVisor | Isolated compilation and code execution |

## Project structure

Application code, authored exercises, and verification tools live in separate folders:

```text
apps/
  api/
    interviewer/       API routes, session logic, storage, and local voice
    tests/             API regression tests
    run-local-speech.sh Ubuntu/WSL API startup with voice dependencies
  web/
    src/               React interface, styles, editor, and voice controls
  runner/              Dedicated Ubuntu runner, installer, and acceptance checks
content/               Roles, scenarios, coding problems, and rubric references
prompts/               Versioned interviewer and coaching prompts
evals/                 Browser journeys and integration checks
docs/                  Acceptance results, audits, and screenshots
data/                  Local runtime files; excluded from version control
.env.example           Non-secret environment template
start.bat              Windows launcher for WSL API and web development server
```

## Choose your local setup

You can run the API without Windows Subsystem for Linux (WSL). Choose the setup that matches the features you need:

| Setup | Requirements | Features |
| --- | --- | --- |
| Windows API and web app | Node.js, Python, uv, provider key | Typed interviews and the practice workflow |
| Windows with Ubuntu WSL2 | Above, plus NVIDIA CUDA support and speech models | Typed interviews and local voice |
| Dedicated Ubuntu runner | Separate Ubuntu computer, Docker, gVisor | Python and C++ execution |

The current voice configuration uses English Whisper large-v3-turbo on an NVIDIA GPU and Kokoro on the CPU. Native Windows voice operation is not verified. Coding execution stays unavailable until you configure the dedicated runner; it never falls back to the API computer.

## Run the API and web app on Windows

### Automatic Windows installer

Download and extract the whole repository, then double-click **install.bat**.
It installs missing Node.js LTS and uv through Windows Package Manager, downloads
Python and locked project dependencies, creates `.env` only when absent, and
builds the web app. The default setup also installs Ubuntu if missing, then
installs the WSL speech dependencies and downloads Whisper and Kokoro models
using the existing provisioning script. Allow several GB of downloads.

Windows needs App Installer (winget). Voice requires an NVIDIA Windows driver
with WSL CUDA support. Ubuntu installation may need administrator permission and
a Windows restart; open Ubuntu once to create your Linux user, then rerun the
installer. The script stops with a clear message when a prerequisite is missing.
Existing `.env`, accounts, and interviews are preserved. Stop running Fieldnote
servers before reinstalling dependencies.

For typed-only setup, run `install.bat -SkipVoice` from a terminal and follow the
manual Windows startup steps below. After full voice setup, configure a provider
in `.env` and run **start.bat**. Optional OpenAI CLI sign-in and the separate
code-execution runner are configured separately; the installer does not sign in
to accounts or install the runner on the application computer.

Use this setup for typed interviews. Run commands in PowerShell from the repository root unless a step says otherwise.

### 1. Install prerequisites

Install these tools and make sure their commands work in your terminal:

- [Node.js](https://nodejs.org/) 22.12 or newer in the 22.x series, including npm
- Python 3.12, or Python 3.11 if you also need the voice runtime
- [uv](https://docs.astral.sh/uv/getting-started/installation/), the Python dependency manager
- A [Groq API key](https://console.groq.com/keys), or an OpenRouter key for that provider

Open the cloned or downloaded project folder before continuing. The commands below assume it contains `apps`, `content`, and `README.md`.

### 2. Install project dependencies

Create the API environment from its lockfile:

```powershell
uv sync --project apps/api --locked --group dev --python 3.12
```

Install the frontend dependencies from their lockfile:

```powershell
cd apps/web
npm ci
cd ../..
```

### 3. Configure your environment

Copy the template only if you don't already have a local configuration:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` in your editor and set the provider key you plan to use. Keep the development origin below:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=
FIELDNOTE_ORIGIN=http://localhost:5173
```

You can leave the inactive provider key empty. Leave the runner variables empty until you configure the dedicated computer. Never commit `.env` or put provider keys in frontend variables.

### 4. Start the account service

Open a terminal at the repository root and run:

```powershell
cd apps/web
npm run auth
```

Keep this terminal open. Better Auth stores account data in `data/auth.sqlite3` and creates a private signing secret in `data/auth.secret` on first start.

### 5. Start the API

Open a terminal at the repository root and run one API worker:

```powershell
cd apps/api
.venv/Scripts/python.exe -m uvicorn interviewer.main:app `
  --host 127.0.0.1 --port 8000 --workers 1
```

Keep this terminal open. One worker avoids duplicate speech models and conflicting ownership of background jobs.

### 6. Start the web app

Open a third terminal at the repository root:

```powershell
cd apps/web
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open [Fieldnote on localhost](http://localhost:5173). Keep all three terminals open while using the app. Press `Ctrl+C` in each terminal to stop it.

### 7. Create an account and test your provider

Create an account with your name, username, email, and password. The first account to use the API receives the existing interviews and resumes from the previous single-owner setup. Keep `data/auth.secret` and `data/auth.sqlite3` private; they hold your account signing key and account records.

Interview and resume records belong to each account. Provider credentials and model settings remain shared by this local installation.

Complete these steps before starting an interview:

1. Open **Settings** and select Groq, OpenRouter, or Codex.
2. Choose available live and assessment models.
3. For OpenRouter, select the downstream provider routes you approve.
4. Review potential costs, save the settings, and run the connection test.
5. Return to setup, review your resume claims, and accept the cloud-processing disclosure.

Connection tests send synthetic text to the selected provider. Model availability, prices, and quotas can change. Configure spending limits with your provider. Existing interviews keep their original provider and model settings.

### Use your Codex subscription

Install the official [Codex CLI](https://developers.openai.com/codex/cli/) on the computer running the API and run `codex login` there. Sign in with ChatGPT using a plan that includes Codex and Luna access. Fieldnote reuses that local login; it does not need an OpenAI API key or copy your login tokens.

In **Settings**, select **Codex**, save, then run the connection test. Both interview dialogue and practice reviews use `gpt-6-luna` with medium reasoning. Resume context, interview answers, and submitted code used for review go to OpenAI through the CLI. Subscription usage limits apply. Requests can take longer than streamed API responses; there is no automatic fallback to another provider.

If the CLI is missing from the API process's PATH, set `CODEX_CLI_PATH` in `.env` to its executable path and restart the API. A Windows installation can also be invoked from WSL through its `.exe` path. In that case, keep `FIELDNOTE_DATA` on a Windows-mounted drive such as `/mnt/c/...`, so both processes can read temporary schema files. A native Linux CLI uses its own Linux login.

New Codex interviews use a fixed local greeting and invite an introduction. Luna then explores up to two confirmed resume experiences, asks role-specific fundamentals, then opens the coding stage. Each topic allows an opening answer and a follow-up; clarification and uncertainty keep the topic open, while an explicit question skip moves on. You can still advance or end through the interview controls.

After an interview ends, **View report** automatically generates answer-linked technical feedback and a provisional score using the selected review model. You can request an updated review after editing answers or adding coding results. Only assessable recorded answers count toward the percentage; personal achievements and missing work are not verified or scored as incorrect. This AI feedback is for self-practice, not a calibrated hiring assessment. Code execution still requires the separate Ubuntu runner; Codex does not execute candidate code.

## Add local voice with Ubuntu WSL2

Use Ubuntu WSL2 for the project's configured speech runtime. The API runs inside WSL instead of the Windows API process; don't run both on port 8000.

Install Ubuntu WSL2, an NVIDIA driver with WSL CUDA support, and `uv` inside Ubuntu. Confirm that `nvidia-smi` works in Ubuntu. The recorded speech checks used an RTX 4050 with 6 GB GPU memory; other hardware needs verification.

From the repository root in an Ubuntu terminal, install the model download tool and provision speech assets:

```bash
uv tool install huggingface-hub
bash apps/api/interviewer/voice/provision_models.sh data/models
```

Ensure `hf` is on your Ubuntu `PATH` before provisioning. The script downloads model files, so review their upstream licenses before use or redistribution. Downloads require internet access; the API doesn't download models during interviews.

Start the API with the existing voice startup script:

```bash
bash apps/api/run-local-speech.sh
```

This script installs locked application dependencies into `data/wsl-api-env` and configures CUDA library paths. Start the web app in Windows using step 5 above, then open the same localhost URL. Voice and TTS start automatically when an interview starts or resumes. Grant microphone permission to answer aloud, or type while listening to interviewer audio. If the browser blocks autoplay, select **Play audio**. The completed report automatically reads the saved rating, summary and next practice focus through Pipecat and Kokoro with the microphone off; **Stop audio** and **Read feedback aloud** control playback.

After provisioning, you can double-click `start.bat` instead of starting all three services manually. The launcher requires the WSL distribution named `Ubuntu`, uses ports 8000, 8001, and 5173, and starts the API, account service, and web app in separate windows. It does not install or start the dedicated runner.

See the [local speech documentation](apps/api/interviewer/voice/README.md) for model paths, offline checks, and voice recovery details. For new WSL installations, a private persistent Linux data directory can reduce storage overhead. Changing `FIELDNOTE_DATA` does not migrate existing interviews, accounts, or signing secrets.

## Enable Python and C++ execution

Run the code execution service only on a separate, dedicated Ubuntu computer. The runner requires Python 3.11 or 3.12 and an x86_64 or aarch64 processor.

From the Windows repository root, create a bundle containing only the runner source and coding content:

```powershell
apps/api/.venv/Scripts/python.exe apps/runner/package_source.py `
  data/fieldnote-runner-source.tar.gz
```

The packager refuses to overwrite an existing archive. Transfer the bundle to your trusted runner administrator. It includes private coding tests, so don't publish it to candidates or copy your `.env` and interview data with it.

On the dedicated Ubuntu computer, extract the bundle and run the installer:

```bash
mkdir fieldnote-runner-source
tar -xzf fieldnote-runner-source.tar.gz -C fieldnote-runner-source
cd fieldnote-runner-source
sudo bash apps/runner/install-dedicated-ubuntu.sh
```

The installer sets up Docker, gVisor, runtime images, and an authenticated service bound to localhost. Follow the [runner setup and acceptance guide](apps/runner/README.md) to connect it through an SSH tunnel, configure backend credentials, and verify isolation. Don't expose its plain HTTP port to the network.

Actual dedicated-host installation and sandbox enforcement remain unverified in the recorded acceptance results. Without a ready runner, the app reports execution as unavailable and preserves your submission.

## Build the frontend for API hosting

You can serve the built web app from the API instead of running Vite. Build the frontend from `apps/web`:

```powershell
npm run build
```

Set `FIELDNOTE_ORIGIN=http://localhost:8000` in `.env`, stop the development servers, and restart the API. Open [the API-hosted app](http://localhost:8000). The API serves files from `apps/web/dist`.

Keep the supplied deployment on localhost. Network access requires HTTPS, authenticated access, and matching origin settings; network microphone operation has not been verified.

## Privacy and local storage

You control which resume claims enter an interview and whether to retain microphone recordings. Review the selected text before starting, because automatic contact-detail removal is incomplete.

The application handles data as follows:

- Resume extraction and speech processing happen on the local API computer
- Selected resume text, transcripts, and submitted code may reach your chosen AI provider
- Raw microphone audio stays local; recording is off by default
- Interviews expire after 30 days by default, or you can choose deletion on completion
- Local deletion doesn't delete provider-held data or promise forensic erasure
- Local machine administrators can access stored files

Keep `.env`, `data/auth.secret`, `data/auth.sqlite3`, interview databases, recordings, and downloaded model assets out of GitHub. The repository's ignore rules exclude runtime data and local secrets.

## Verify your changes

Run API, voice-helper, and runner-source checks from the Windows repository root:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests apps/api/interviewer/voice/test_manager.py apps/runner/tests -q
```

These checks do not execute candidate code or establish real sandbox enforcement. Build the frontend separately with `npm run build` from `apps/web`.

The recorded suite passed 277 tests. Real provider checks and a physical microphone check also passed within their documented scope. Voice latency targets remain unmet, and OpenRouter availability has been intermittent. Calibrated technical ratings remain disabled; the selected review model provides separately labeled, provisional practice ratings and feedback.

See the [acceptance matrix](docs/acceptance-matrix.md) for coverage and remaining gaps, and [acceptance results](docs/acceptance.md) for commands and measurements.

## Troubleshoot startup

Use the symptom below to choose the next check:

| Symptom | What to check |
| --- | --- |
| Port 8000 or 5173 is busy | Stop the existing API or web server before restarting |
| Sign-in or requests fail after changing URLs | Match `FIELDNOTE_ORIGIN` to the browser URL, then restart the API |
| Voice is unavailable | Check Ubuntu CUDA support, downloaded models, and speech warmup |
| Provider test fails | Check the server-side key, model access, route, quota, and spending balance |
| Coding execution is unavailable | Check the dedicated runner, tunnel, token, and isolation preflight |
| History appears empty after changing storage | Restore the previous `FIELDNOTE_DATA`; changing it selects a different database |
