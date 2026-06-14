# Michigan RP Welcome Bot

A professional Discord welcome bot built with **discord.py 2.x** for the Michigan RP community. Automatically greets new members with richly styled embeds in a server channel and via Direct Message — all fully configurable through `config.json`.

---

## Features

- 🎉 **Auto-welcome** — triggers on every new member join
- 📨 **Channel embed + DM embed** — two independent, fully styled embeds
- ⚙️ **Zero-code configuration** — edit `config.json` to change everything
- 🔄 **Live reload** — `/reload` applies config changes without restarting
- 🛡️ **Graceful DM failure** — if a user has DMs disabled, the bot continues silently
- 🔌 **Slash commands** — `/testwelcome`, `/testdm`, `/reload`
- 🧩 **Placeholder system** — dynamic text with `{user}`, `{username}`, `{mention}`, `{member_count}`, `{server}`

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| discord.py | 2.3.2 or higher |

---

## Installation

### 1 — Clone or download the project

```bash
git clone https://github.com/your-org/michigan-rp-bot.git
cd michigan-rp-bot
```

### 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### Bot token — environment variable

**Never put your token in `config.json`.** Set it as an environment variable instead:

```bash
# macOS / Linux
export DISCORD_TOKEN="your-bot-token-here"

# Windows Command Prompt
set DISCORD_TOKEN=your-bot-token-here

# Windows PowerShell
$env:DISCORD_TOKEN = "your-bot-token-here"
```

For a permanent setup, create a `.env` file and use a library like [`python-dotenv`](https://pypi.org/project/python-dotenv/), or configure your hosting platform's secrets manager.

### config.json

Open `config.json` and fill in your values:

| Key | Description |
|---|---|
| `welcome_channel_id` | The **numeric ID** of the channel where welcome embeds are posted |
| `status_message` | The bot's "Watching …" status text |
| `welcome_embed` | Embed sent to the server channel (see fields below) |
| `dm_embed` | Embed sent to the new member's DMs (same fields) |

#### Embed fields

| Field | Description |
|---|---|
| `title` | Bold embed title — supports placeholders |
| `description` | Main body text — supports placeholders and Markdown |
| `color` | Hex color string, e.g. `"#E8A400"` |
| `thumbnail_url` | Small image in the top-right corner (e.g. server icon URL) |
| `image_url` | Large banner image at the bottom of the embed |
| `author_name` | Text above the title — supports placeholders |
| `author_icon_url` | Small icon next to the author name |
| `author_url` | Makes the author name a hyperlink (optional) |
| `footer_text` | Small text at the very bottom — supports placeholders |
| `footer_icon_url` | Tiny icon next to the footer text |

#### Available placeholders

| Placeholder | Resolves to |
|---|---|
| `{user}` | Full username, e.g. `CoolUser#1234` |
| `{username}` | Display / global name, e.g. `CoolUser` |
| `{mention}` | Clickable @mention, e.g. `@CoolUser` |
| `{member_count}` | Current total member count of the server |
| `{server}` | Server name |

---

## Running the Bot

```bash
python bot.py
```

You should see output like:

```
2024-06-14 12:00:00 [INFO] MichiganRPBot: Config loaded.
2024-06-14 12:00:01 [INFO] MichiganRPBot: Slash commands synced.
2024-06-14 12:00:01 [INFO] MichiganRPBot: Logged in as MichiganRPBot#1234 (ID: 123456789)
```

---

## Slash Commands

| Command | Permission | Description |
|---|---|---|
| `/testwelcome` | Manage Server | Posts a test welcome embed in the configured channel |
| `/testdm` | Everyone | Sends the DM embed to yourself |
| `/reload` | Manage Server | Hot-reloads `config.json` without restarting the bot |

---

## Required Permissions

Grant the bot these permissions when creating its invite link:

| Permission | Why |
|---|---|
| **Read Messages / View Channels** | See the welcome channel |
| **Send Messages** | Post welcome embeds |
| **Embed Links** | Render rich embeds |
| **Mention Everyone** | Not strictly required; the member @mention works without it |

### Required Privileged Gateway Intents

In the [Discord Developer Portal](https://discord.com/developers/applications) → your application → **Bot** page, enable:

- ✅ **Server Members Intent** — required for `on_member_join` and accurate `member_count`

---

## Project Structure

```
michigan-rp-bot/
├── bot.py          # Main bot — events, commands, embed builder
├── config.json     # All configurable settings (no token here!)
├── requirements.txt
└── README.md
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `DISCORD_TOKEN environment variable is not set` | Set the `DISCORD_TOKEN` env var before running |
| Welcome embed not sending | Check `welcome_channel_id` is correct and the bot has **Send Messages** + **Embed Links** permissions |
| Slash commands not appearing | Commands sync on startup; wait up to 1 hour for Discord's cache, or kick and re-invite the bot |
| `Privileged intent` error | Enable **Server Members Intent** in the Developer Portal |
| DMs not delivering | Expected — user has DMs disabled. The bot logs this and continues |

---

## License

MIT — free to use and modify for your community.
