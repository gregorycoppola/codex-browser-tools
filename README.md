# Codex browser tools

Local setup records and a Chromium interaction test for the Playwright and
Chrome DevTools MCP servers installed on the example machine.

## Files and locations

- `scripts/browser-smoke.py`: our test script, preserved from `/tmp`.
- `package.json` and `package-lock.json`: copies of the installed dependency
  manifests, pinning Playwright MCP 0.0.80 and Chrome DevTools MCP 1.9.0.
- Installed packages: `/home/myuser/.local/share/codex-browser-tools/node_modules/`.
- Active MCP configuration: `/home/myuser/.codex/config.toml`.
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

The script uses the existing Node executable at
`/home/myuser/.local/share/mise/installs/node/latest/bin/node` and Chromium at
`/usr/local/bin/chromium`. These paths are machine-specific.

It serves a local page on an ephemeral loopback port, starts each MCP server
with an isolated browser profile, clicks a button, and checks the changed page
title. Each server should print `PASS`. Logs are written to
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

## Version control

This is a local Git repository. No remote hosting is required. Review changes
with `git diff` and record them with `git add` and `git commit` once a Git author
name and email are configured.
