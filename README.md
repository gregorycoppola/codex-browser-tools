# Codex browser tools

Control visible Chromium windows from Codex in a terminal, without the ChatGPT
app. This repo supplies pinned MCP packages, a machine-specific configuration
generator, and browser checks.

Tested on Omarchy / Arch Linux ARM with Hyprland, Chromium 152, Node 26, and
Python 3.14. Other Linux desktops can use the interaction checks, but automatic
window verification is Hyprland-specific. macOS and Windows setup is not tested.

## Choose a browser connection

| MCP server | What it controls | Logins |
| --- | --- | --- |
| `playwright` | A visible Chromium with a dedicated persistent profile | Sign in once in that window |
| `chrome-devtools` | Another dedicated Chromium, with debugging tools | Its own separate profile |
| `playwright-personal` (optional) | Regular Chromium through Microsoft's extension | Existing browser logins |

Dedicated profiles are useful for development and testing. The extension is for
working with your existing browsing session. A successful tool response does not
by itself prove a browser window is visible; our desktop check verifies that too.

## Prerequisites

- Linux graphical desktop and an installed Chromium/Chrome browser.
- Codex CLI installed and signed in; `codex` available in your terminal.
- Node.js and npm. The pinned packages accept Node 20.19+, 22.12+, or 23+ in
  their respective major-version ranges; Node 26 is what we tested.
- Python 3.11+ (uses the standard library only).
- Git, plus access to this repository if it is private.
- For automatic window verification: Hyprland and `hyprctl`.

This setup does not require disabling Codex's sandbox or using a special shell
alias. Browser servers must be able to start subprocesses and reach the desktop.
Your Codex permission settings remain a separate choice.

## Install from a checkout

Run in a terminal **inside your graphical desktop session**:

Replace `username` in the clone URL with the GitHub account that owns your copy
of this repository.

```bash
git clone https://github.com/username/codex-browser-tools.git
cd codex-browser-tools
env PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 PUPPETEER_SKIP_DOWNLOAD=true npm ci --no-audit --no-fund
python3 scripts/generate-config.py
```

The lockfile pins Playwright MCP **0.0.80** and Chrome DevTools MCP **1.9.0**.
The download flags use the system browser instead of downloading another browser.
Dependencies install into this checkout's ignored `node_modules/` directory.

The generator writes `config/local.toml`, detects executable paths and desktop
variables, and uses persistent profiles outside the repository. It does **not**
change your Codex settings, install a browser, or read an authentication token.

Merge the generated `[mcp_servers.*]` sections into `~/.codex/config.toml` (or
`$CODEX_HOME/config.toml` if you use a custom Codex directory). Back up that file
first. Replace matching server sections instead of appending duplicate TOML
sections, and preserve unrelated settings and any existing personal token.
`config/codex-mcp.toml` is a placeholder example, not a ready-to-run configuration.
See [Codex MCP configuration](https://developers.openai.com/codex/mcp/).

Restart Codex after merging. From this checkout, run `codex`. Ask it to use the
`playwright` server to open a page. Keep the checkout at this location: generated
paths are absolute. If you move it, regenerate and merge the browser entries.

### Override paths

```bash
python3 scripts/generate-config.py \
  --node /absolute/path/to/node \
  --browser /absolute/path/to/chromium \
  --profile-root "$HOME/.local/share/codex-browser-tools/profiles"
```

The generator preserves executable wrappers and symlinks, including Omarchy's
Chromium wrapper. Use `--help` for all options.

## Use your regular browser and existing logins

1. In **regular Chromium**, install Microsoft's
   [Playwright Extension](https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm).
   Its extension ID is `mmlmfjhmonkocbjadbfplnigmagldckm`.
2. Open `chrome://version` and find **Profile Path**. Pass its parent directory
   (the directory containing `Default` or `Profile 1`), not the profile subfolder.
3. Generate the additional connection, then merge the generated sections as above:

```bash
python3 scripts/generate-config.py --personal-profile "$HOME/.config/chromium"
```

For Google Chrome the user-data root is often `~/.config/google-chrome`; use the
actual path from your browser. The supplied example is for Chromium.

4. Restart Codex, and ask it to use **`playwright-personal`**. The first connection
   opens an extension page. Click **Allow & select** beside a tab to start there.
   Drag additional tabs into the Playwright group to make them available.

The extension's consent screen grants broad access to the browser, including
signed-in sessions; choosing a starting tab is not a security boundary. This
connection does not copy cookies and does not launch a second standalone browser
against your regular profile. Different clients can have different tab groups.

### Connect automatically without repeated clicks

Open the extension's status page and copy its `PLAYWRIGHT_MCP_EXTENSION_TOKEN`.
In your **local Codex configuration only**, add it under the existing section:

```toml
[mcp_servers.playwright-personal.env]
# Keep the generated desktop variables here too.
PLAYWRIGHT_MCP_EXTENSION_TOKEN = "PASTE_YOUR_OWN_TOKEN_HERE"
```

Do not create a second copy of that section. Set local file permissions:

```bash
chmod 600 "${CODEX_HOME:-$HOME/.codex}/config.toml"
```

Restart Codex. The token is profile-specific and lets subsequent connections
skip the approval dialog. To revoke automatic access, regenerate the token in
the extension, restart the browser as instructed there, and remove/update the
old token in Codex's configuration. Removing the extension disables this route.
Do not put real tokens in Git, shell commands, screenshots, or issue reports.
No `.env` file is loaded automatically by these scripts.

[Microsoft's extension documentation](https://github.com/microsoft/playwright/tree/main/packages/extension#readme)
explains installation, tab groups, and authentication.

## Environment variables

| Variable | Where used | Value / purpose |
| --- | --- | --- |
| `DISPLAY` | Each MCP server's `env` | Copied from the desktop terminal, e.g. `:0`; X11/XWayland display |
| `WAYLAND_DISPLAY` | Each MCP server's `env` | Copied when set, e.g. `wayland-1`; Wayland socket name |
| `XDG_RUNTIME_DIR` | Each MCP server's `env` | Copied when set, e.g. `/run/user/1000`; never assume another user's UID |
| `XAUTHORITY` | Each MCP server's `env` | Copied when set; X11 authorization file |
| `PLAYWRIGHT_MCP_EXTENSION_TOKEN` | Local `playwright-personal.env` only | Optional personal token for automatic connection |
| `CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS` | `chrome-devtools.env` | Generator sets `1` |
| `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` | `npm ci` command | Set `1` to use installed Chromium |
| `PUPPETEER_SKIP_DOWNLOAD` | `npm ci` command | Set `true` to use installed Chromium |
| `CODEX_HOME` | Check scripts | Optional alternative Codex config directory; defaults to `~/.codex` |
| `XDG_DATA_HOME` | Generator | Optional base for dedicated profiles; defaults to `~/.local/share` |
| `HYPRLAND_INSTANCE_SIGNATURE` | Desktop check process | Inherited from Hyprland; needed by `hyprctl` |

Do not blindly copy another machine's display values. Regenerate from the desktop
terminal if the session's display/socket changes. Generated variables are a
snapshot of that session, not automatic display discovery at each Codex launch.

## Verify the setup

Dedicated browser checks use temporary isolated profiles and a local loopback
HTTP page. They click a button, verify a unique title, and check Hyprland for a
mapped window. They do not use your saved logins.

```bash
python3 scripts/browser-smoke.py
# Test the configured desktop variables without inheriting these from the shell:
env -u DISPLAY -u WAYLAND_DISPLAY -u XDG_RUNTIME_DIR python3 scripts/browser-smoke.py
# Test generated settings before merging them into Codex:
python3 scripts/browser-smoke.py --config config/local.toml
```

On other Linux desktops, use `--skip-window-check` and confirm the windows appear
yourself. The output explicitly says visibility was not checked in that mode.

To test the extension (browser and extension must be open/installed):

```bash
python3 scripts/personal-browser-check.py
python3 scripts/personal-browser-check.py --github-login
```

The first lists tabs shared with that client. The optional GitHub check opens a
new tab, reads GitHub's signed-in username metadata, then closes only that test
tab. A `null` login means the page did not expose a signed-in username. Connection
`PASS` alone does not assert a GitHub login. The check disconnects afterward;
Codex establishes its own connection when you next use its tools. A connection
welcome tab may remain. Both checks accept `--config PATH`.

Logs and browser artifacts go into private, per-run
`/tmp/codex-browser-check-*` directories; paths are printed in the output. These
may contain personal URLs or tokens in server-generated artifacts. Do not share
raw artifacts. Printed results and MCP errors redact the configured token.
Delete a run's directory when it is no longer needed.

Run configuration tests without opening browsers:

```bash
python3 -m unittest discover -s tests
```

## Troubleshooting

- **Tools work but there is no window:** check the generated desktop `env` values
  and restart Codex. Missing display variables caused a headless Playwright
  browser in our initial setup. A page title alone is not evidence of visibility.
- **Chrome DevTools says “Target closed”:** verify the desktop variables and run
  the isolated check. Fixing the missing variables resolved this on our machine.
- **Connection prompt expires:** run the personal check again and use the newly
  opened prompt. The check waits up to 120 seconds for each MCP request.
- **Extension is installed but cannot connect:** verify the browser executable
  and user-data root match the profile where you installed it. Check whether the
  extension is enabled in `chrome://extensions`.
- **Web Store offers “Download Chrome”:** verify you opened the exact extension
  link in Chromium itself, not a non-Chromium browser or an unrelated download
  page. Alternate/manual installation has not been tested here.
- **Wrong or missing login:** confirm whether the tool is `playwright-personal`
  or a dedicated-profile tool. Personal windows, dedicated profiles, and
  temporary test profiles do not share cookies with one another.
- **Profile is already in use:** avoid multiple standalone browsers using the
  same user-data root. Use the extension for a running regular browser; the
  smoke checks already use isolated profiles.
- **New tools do not appear:** restart Codex after updating configuration.
- **Paths stop working after moving the repo or updating Node:** regenerate the
  snippet and merge it again, preserving your local token.

## Repository layout and local state

- `package.json`, `package-lock.json`: pinned server dependencies.
- `scripts/generate-config.py`: portable Linux configuration generator.
- `scripts/browser-smoke.py`: dedicated browser and visibility checks.
- `scripts/personal-browser-check.py`: extension and optional GitHub login check.
- `scripts/mcp_client.py`: shared stdio MCP client.
- `config/codex-mcp.toml`: token-free placeholder example.
- `config/local.toml`: generated local configuration, ignored by Git.
- `docs/local-setup.md`: tested setup and migration notes for this machine.

Browser profiles, tokens, installed packages, and generated artifacts stay out
of Git. Repository access and browser authentication are independent; cloning
this project never supplies anyone else's login. This repo does not change its
GitHub visibility during setup.
