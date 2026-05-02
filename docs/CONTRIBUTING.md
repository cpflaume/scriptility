# Contributing

Skript-/Task-Vertrag und Workflow stehen in [`AGENTS.md`](../AGENTS.md). Diese
Datei ergänzt nur den menschlichen PR-Prozess.

## PR-Checkliste

- [ ] CI grün (`task dev:lint && task dev:test`)
- [ ] Mindestens ein Test pro neuem Skript
- [ ] `desc:` (und ggf. `summary:`) im Task aussagekräftig
- [ ] Neue ENVs in `.env.example` + `docs/REQUIREMENTS.md`
- [ ] Keine Secrets committed (gitleaks läuft als pre-commit)
- [ ] Mutierende Aktionen abgesichert (`--apply`-Flag oder `prompt:`)
- [ ] CODEOWNER hat reviewed (siehe `CODEOWNERS`)

## Reviews

CODEOWNERS-Review pro Namespace ist Pflicht. Reviews ausserhalb des eigenen
Namespaces sind willkommen, aber nicht erforderlich.
