## 📘 1. DAILY WORKFLOW GUIDE – Where to Find Things + Command Examples

### 📂 Key Directories (All Paths Relative to Repo Root)

| What | Where | Purpose |
|------|-------|---------|
| **Test build zips** | `/zips/` | All addon zips (test, pre‑release, stable). Filename includes version + optional build ID. |
| **Release summaries (JSON)** | `/system/state/release/release_summary.json` | Machine‑readable log of every release (addon, version, news, timestamp). |
| **AI handoff state** | `/share/handoffs/current_state.yaml` | Latest repository status – feed this to AI for context. |
| **Changelogs** | `projects/*/CHANGELOG.md` | Human‑readable release notes, updated automatically on stable release. |
| **Logs** | `/logs/` | Script outputs, tree dumps, etc. |
| **System config** | `/system/config/` | AI protocol, modes. |
| **Skills / Roles** | `/system/skills/`, `/system/roles/` | AI capabilities. |
| **Handoff archive** | `/share/handoffs/` | All past session transfers. |

---

### 🧪 Daily Debugging – Quick Test Build

```bash
# Create test zip with dev build ID (no version bump)
scripts/debug_bundle.sh projects/plugin.program.fluid
# → /zips/plugin.program.fluid-1.0.2+dev.20260212_1435.zip
```

**Copy to TVBox** – via USB, ADB, SMB, or `scripts/deploy.sh` (if you create it).

---

### 🚧 Pre‑Release (Shared Testing)

```bash
# 1. Bump version + add suffix
scripts/bump_version.sh projects/plugin.program.fluid patch alpha.1

# 2. Create zip (suffix in filename)
scripts/bundle.sh projects/plugin.program.fluid
# → /zips/plugin.program.fluid-1.0.3-alpha.1.zip
```

---

### 🏁 End‑of‑Day Stable Release

```bash
# 1. Remove suffix / set final version
scripts/bump_version.sh projects/plugin.program.fluid 1.0.3

# 2. Update CHANGELOG.md, generate handoff state
scripts/release_info.sh

# 3. Create final zip
scripts/bundle.sh projects/plugin.program.fluid

# 4. Commit and push (optional)
scripts/git_sync.sh
```

---

### 🌳 Directory Tree – Useful Variations

```bash
# Full repo tree (exclude clutter) – using built-in `tree`
tree -a -I 'projects|sandro|vault|zips|logs|__pycache__|*.pyc|.git|.idea|.vscode'

# System‑only tree (config, modes, internal, etc.)
tree system -I '__pycache__|*.pyc'

# Handoff‑only tree
tree share/handoffs

# Save tree to log with timestamp
scripts/tree.sh   # (custom script) → /logs/tree_YYYYMMDD_HHMMSS.txt
```

---

### 🧠 AI Handoff – Quick Commands

```bash
# Show current repository state for AI
cat share/handoffs/current_state.yaml

# Feed it directly to AI (copy/paste or attach)
```