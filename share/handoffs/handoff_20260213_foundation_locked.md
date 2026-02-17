type: handoff
status: LOCKED
version: 1.0
date: 2026-02-13
from: Claude/Gemini collaboration
to: Future AI sessions (Claude, Kimi, Manus, etc.)
---

# 🔒 Handoff: RAG System Foundation LOCKED

## TL;DR
RAG context system foundation **locked and agreed**. Key decisions:
- **Structure:** `system/core/` + `system/lenses/` + `system/router/`
- **Vault split:** Personal (`/vault/`) vs AI (`/system/vault/`)
- **Agent project:** Parallel track in `projects/personal-agent/` (private, gitignored)
- **Method:** Intent classification → lens loading → context assembly
- **Constraint:** Termux-native, no Docker, privacy-first

## Locked Decisions

### 1. Directory Structure (FINAL)
```
system/
├── core/           # identity, constraints, env (always load)
├── lenses/         # code, design, meta (intent-triggered)
├── router/         # classifier.yaml (scoring rules)
├── vault/          # AI-accessible notes (English)
├── skills/         # Existing 8 skills
├── roles/          # Existing 3 roles
└── templates/      # Existing

projects/
├── plugin.program.fluid/
├── plugin.program.fluidsnoop/
└── personal-agent/     # PRIVATE, gitignored, NOT part of RAG

vault/              # Personal Obsidian (Dutch, never exposed)
```

### 2. Vault Strategy (FINAL)
- **Personal:** `vault/` - Dutch, Obsidian, absolute privacy
- **AI:** `system/vault/` - English, technical, AI-accessible
- **Sync:** Manual only - you adapt content when relevant
- **RAG:** Only indexes `system/vault/`, never personal vault directly

### 3. Agent Project Rules (FINAL)
- **Location:** `projects/personal-agent/` (not in `/system/`)
- **Status:** Private, experimental, learning project
- **Boundary:** Completely separate from RAG infrastructure
- **Documentation:** `system/vault/projects/personal-agent.md`
- **Git:** Added to `.gitignore`, never synced

### 4. Intent Classification (FINAL v1)
- **Method:** Keyword scoring (+2 strong, +1 weak)
- **Lenses:** code, design, meta (combinable)
- **Default:** code if no signals
- **Entry:** `qs.sh` generates context, `intent_classifier.sh` detects

### 5. Prohibited (FOR ALL FUTURE SESSIONS)
1. Never suggest agent in `/system/`
2. Never suggest auto vault sync
3. Never expose private paths publicly
4. Never modify core/constraints without explicit ask
5. Never assume mode - detect or ask
6. Never add Docker/heavy deps

## Context for Next Session

### If User Says...
- **"Implement"** → Create files from blueprint (13 files defined)
- **"Refine"** → Suggest improvements to locked structure
- **"Agent"** → Refer to `projects/personal-agent/` (separate project)
- **"Vault"** → Clarify personal vs AI vault split
- **"Dify"** → Cloud playground only, not for this RAG system

### Key Files to Reference
- `system/core/identity.yaml` - User preferences, paths
- `system/core/constraints.yaml` - Hard rules, privacy
- `system/router/classifier.yaml` - Intent scoring
- This handoff - Authority for all decisions

## Next Steps (User Decides)
1. **Implement:** Create all 13 files from blueprint
2. **Test:** Run `qs.sh` with real queries, refine triggers
3. **Build:** Start agent project in `projects/personal-agent/`
4. **Enhance:** Add vault bridge or semantic search (future)

## Authority
**This handoff + blueprint = locked agreement.**  
Override: Only user can modify locked decisions.  
Question: If unclear, ask user - don't assume.

---
**End Handoff - Foundation Locked**