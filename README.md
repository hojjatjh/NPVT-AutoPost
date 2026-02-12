# NPVT-AutoPost

Production-oriented Telegram `.npvt` relay automation with runtime controls, deduplication, and admin panel management.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Telethon](https://img.shields.io/badge/Telethon-1.36%2B-2CA5E0)
![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20MariaDB-005C84)

## Overview
`NPVT-AutoPost` listens to mapped Telegram source chats and automatically relays incoming `.npvt` files to mapped destination chats.

It combines:
- A Telegram self account session for reading/uploading media
- A helper bot for inline admin UX
- A MySQL/MariaDB backend for mappings, runtime settings, and transfer logs

## Why This Project
- Eliminates manual reposting of `.npvt` files
- Adds operational controls without process restarts
- Prevents duplicate reposts using two independent checks
- Keeps relay behavior observable through stats and logs

## Feature Breakdown

### Relay Engine
- `.npvt`-only detection (by filename/extension)
- Asynchronous queue-based processing
- Configurable send interval (rate limiting)
- Automatic FloodWait recovery with delayed requeue
- Auto-renaming output files: `<prefix> (<index>).npvt`

### Deduplication
- Duplicate check by Telegram `file_id`
- Duplicate check by SHA-256 file hash
- Configurable dedup toggle from admin panel

### Runtime Configuration (No Restart Required)
- Toggle relay on/off
- Toggle dedup on/off
- Set relay caption
- Set send interval (seconds)
- Set output filename prefix
- Set source map refresh interval

### Caption Support
- Fully customizable caption text for relayed files
- Supports multilingual content (including Persian/English)
- Supports multi-line captions
- Runtime update from panel
- Telegram-safe length handling (up to 1024 chars)

### Channel Mapping Management
- Add source -> destination mapping
- Delete mapping by source
- Preview mappings in panel
- Export full mapping list to text file

### Admin Observability and Maintenance
- Total transfers
- Unique source chats
- Unique destination chats
- Unique file IDs
- Unique file hashes (dedup cache footprint)
- Latest transfer timestamp
- One-action reset of transfer history (with confirmation flow)

### Bootstrap and Compatibility
- Auto-creates required tables on startup
- Attempts UTF-8 normalization to `utf8mb4`
- Backward-compatible insert fallback if legacy schema lacks `file_hash`

## Tech Stack
- Python 3.10+
- Telethon
- PyMySQL
- python-dotenv
- MySQL / MariaDB

## Project Structure
```text
.
├── main.py
├── requirements.txt
├── .env.example
└── src/
    ├── bot_helper.py
    ├── npvt_relay.py
    ├── handlers.py
    ├── controllers.py
    ├── models.py
    ├── orm.py
    ├── config.py
    ├── buttons.py
    └── utilities.py
```

## Prerequisites
- Python `3.10+`
- Running MySQL/MariaDB instance
- Telegram `API_ID` and `API_HASH` from `my.telegram.org`
- Telegram bot token from `@BotFather`
- Inline mode enabled for helper bot (`/setinline`)

## Quick Start
1. Clone the repository.
```bash
git clone https://github.com/hojjatjh/NPVT-AutoPost.git
cd NPVT-AutoPost
```

2. Create and activate a virtual environment.
```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate
```

3. Install dependencies.
```bash
pip install -r requirements.txt
```

4. Create `.env`.
```bash
cp .env.example .env
```
Windows CMD:
```bat
copy .env.example .env
```

5. Create database (tables are auto-created by the app).
```sql
CREATE DATABASE npvt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. Fill `.env` values and run.
```bash
python main.py
```

7. In your self chat, send:
```text
.panel
```

## Configuration Reference
| Variable | Required | Description |
|---|---|---|
| `DB_HOST` | Yes | Database host |
| `DB_PORT` | Yes | Database port |
| `DB_USER` | Yes | Database username |
| `DB_PASSWORD` | Yes | Database password |
| `DB_NAME` | Yes | Database name |
| `TELEGRAM_API_ID` | Yes | Telegram API ID |
| `TELEGRAM_API_HASH` | Yes | Telegram API hash |
| `TELEGRAM_BOT_TOKEN` | Yes | Helper bot token |
| `TELEGRAM_PHONE_NUMBER` | Yes | Self account phone number |
| `TELEGRAM_OWNER_IDS` | Yes | Comma-separated owner/admin IDs |
| `TELEGRAM_SELF_ID` | Yes | Self owner ID used for inline access |
| `SCRIPT_VERSION` | No | Informational version string |

## Admin Panel Capabilities
- Trigger: `.panel` (owner-only)
- Menu sections:
  - Channel Management
  - Relay Settings
  - Stats and Maintenance
  - Script Information
  - Account Information

### Relay Settings Actions
- Set caption
- Set rate limit
- Set filename prefix
- Set source refresh interval
- Toggle relay status
- Toggle duplicate filter

### Maintenance Actions
- Refresh stats
- Reset transfer log and dedup cache via explicit confirmation phrase

## Runtime Defaults
- Default caption: `#npvt best`
- Default send interval: `6.0` seconds
- Default source cache refresh: `20` seconds
- Default filename prefix: `npvt`
- Default relay status: enabled
- Default dedup status: enabled

## Operational Notes
- Only messages with `.npvt` files are relayed.
- Source and destination entries are handled as Telegram `-100...` IDs.
- First run requires Telegram login verification for session creation.
- Session files are stored under `sessions/`.

## Security and Compliance
- Never commit `.env` or `sessions/` files.
- Keep `TELEGRAM_OWNER_IDS` restricted to trusted IDs.
- Use least-privilege DB credentials when possible.
- Confirm your use complies with Telegram Terms and local laws.

## License
MIT License. See `LICENSE`.

## Disclaimer
This project is not affiliated with, endorsed by, or sponsored by Telegram. You are responsible for compliant and safe use.
