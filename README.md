# Codex browser tools

Local setup records and a Chromium interaction test for the Playwright and
Chrome DevTools MCP servers installed on the example machine.

## Files and locations

- `scripts/browser-smoke.py`: our test script, preserved from `/tmp`.
- `package.json` and `package-lock.json`: copies of the installed dependency
  manifests, pinning Playwright MCP 0.0.80 and Chrome DevTools MCP 1.9.0.
- Installed packages: `/home/myuser/.local/share/codex-browser-tools/node_modules/`.
- Active MCP configuration: `/home/myuser/.codex/config.toml`.
- Browser-only configuration to restore: `config/codex-mcp.toml`.
- Dedicated profiles: `/home/myuser/.local/share/codex-browser-tools/profiles/`.

This repository stores source and setup notes. Codex currently launches packages
from the installed location above. Changing this repository does not automatically
change that installation. Browser profiles, installed packages, and logs are
excluded from Git. The full personal Codex configuration is not copied here.

## Run the browser check

From this repository, in the graphical desktop session:

```bash
python scripts/browser-smoke.py
```

The script reads the active browser entries in `~/.codex/config.toml`, including
their display environment, and replaces persistent profiles with isolated ones.
The configuration uses the existing Node executable at
`/home/myuser/.local/share/mise/installs/node/latest/bin/node` and Chromium at
`/usr/local/bin/chromium`. These paths are machine-specific.

It serves a local page on an ephemeral loopback port, starts each MCP server
with an isolated browser profile, clicks a button, and checks the changed page
title. It also checks Hyprland for a mapped window with that title, so a headless
browser cannot pass. Each server should print `PASS`. Logs are written to
`/tmp/codex-playwright-smoke.log` and `/tmp/codex-chrome-devtools-smoke.log`.

## Restore the installed dependencies

With Node/npm available, run from this repository:

```bash
mkdir -p /home/myuser/.local/share/codex-browser-tools
cp package.json package-lock.json /home/myuser/.local/share/codex-browser-tools/
env PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 PUPPETEER_SKIP_DOWNLOAD=true npm ci --prefix /home/myuser/.local/share/codex-browser-tools --no-audit --no-fund
```

This reinstalls the locked packages in the existing runtime directory. Chromium
must already be installed. The existing Codex MCP entries are configured to use
that directory and dedicated persistent profiles; the test uses isolated profiles.

## Visible browser setup

Merge the browser sections from `config/codex-mcp.toml` into
`~/.codex/config.toml`, preserving unrelated settings. Restart Codex after
changing these entries so the MCP servers receive the new environment.

Both servers need the graphical session variables. On this machine these are
`DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-1`, and `XDG_RUNTIME_DIR=/run/user/1001`.
Check these against the current desktop session when restoring on another
machine or after changing the display setup.

Without the display variables, Playwright launched headless and Chrome DevTools
failed to connect. Successful page clicks alone did not establish visibility.
The updated test verifies actual desktop windows. To reproduce Codex's missing
inherited display variables while testing the configured values:

```bash
env -u DISPLAY -u WAYLAND_DISPLAY -u XDG_RUNTIME_DIR python scripts/browser-smoke.py
```

Browser tools open separate Chromium profiles, not the regular browsing profile.
Sign into sites in the tool's visible window when needed; cookies remain in the
dedicated profile. Playwright and Chrome DevTools each use their own window and
profile. The temporary visible manual window opened during troubleshooting is
separate from these persistent profiles.

## Version control

Remote: https://github.com/gregorycoppola/codex-browser-tools

Only setup files and tests belong in Git. Browser profiles and session data stay
local.
