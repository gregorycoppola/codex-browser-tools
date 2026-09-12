# Tested local setup — September 12, 2026

This records the machine where the setup was developed. Other users should use
the generator and their own paths, displays, and extension token.
Home-directory examples use `myuser` as a placeholder for your Linux username.

| Item | Local value |
| --- | --- |
| Checkout | `/home/myuser/Projects/codex-browser-tools` |
| OS / desktop | Omarchy, Arch Linux ARM, Hyprland |
| Browser wrapper | `/usr/local/bin/chromium` |
| Node | `/home/myuser/.local/share/mise/installs/node/latest/bin/node` |
| Codex config | `/home/myuser/.codex/config.toml` |
| Desktop env | `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-1`, `XDG_RUNTIME_DIR=/run/user/1001` |
| Regular Chromium data root | `/home/myuser/.config/chromium` |
| Dedicated profiles | `/home/myuser/.local/share/codex-browser-tools/profiles/` |

## Runtime migration

Initially the packages ran from
`/home/myuser/.local/share/codex-browser-tools/node_modules/`, and this repo only
stored copies of the manifests. The setup now installs packages with `npm ci`
in the checkout and points the three local Codex entries at that checkout's
`node_modules/`. Existing dedicated profiles remain at their original locations,
so saved logins are preserved. The old package installation has not been deleted.

The local Codex configuration has a backup from before the migration. The
extension token remains only in that local configuration, mode 0600; it is not
in the generated example. Restart Codex to load the updated commands and the
new `playwright-personal` server.

## What was verified

- Playwright and Chrome DevTools both opened mapped desktop windows and clicked
  a local test button with configured display variables.
- The extension connected to regular Chromium after installation and approval.
- Adding a local extension token allowed reconnection without another click.
- GitHub username metadata confirmed the existing signed-in session.

A visible browser launched manually during troubleshooting used a temporary
Playwright profile. That window is separate from both regular Chromium and the
persistent dedicated profiles; it should not be used as the long-term login
store. The main early mistake was treating a successful headless click test as
proof that a desktop window existed; the current check verifies a window too.
