# Local development

- This checkout is the local Codex marketplace source for `dsvideo-plugin`.
- Edit the repository files, not anything under the Codex plugin cache.
- After changing plugin or skill files, run `./scripts/dev-reinstall.ps1` from PowerShell.
- Test the refreshed plugin in a new Codex task; an existing task keeps its previously loaded plugin context.
- The reinstall script adds a local cachebuster to `.codex-plugin/plugin.json`. Replace it with the intended release version before publishing.
