# 🔒 Blueprint: Tha G👑 Thang - RAG Context System v1.0

**Status:** Foundation Locked  
**Date:** 2026-02-13  
**Scope:** `/system/` RAG infrastructure + Project Coexistence Rules  
**Privacy:** LOCAL ONLY - Never commit to GitHub

---

## 1. Philosophy & Constraints (Locked)

### Core Principles
1. **Fluid over Rigid:** Intent detection > hardcoded modes
2. **Progressive Disclosure:** Minimal context default, expand on demand
3. **Privacy-First:** Personal vault stays separate; AI vault is derived/filtered
4. **Coexistence:** Agent project is parallel track, not part of RAG system
5. **Termux-Native:** All tools must work on Android without root/Docker

### Hard Constraints
- `delta_only: true` for all coding output
- `no_emoticons`, `no_citations` in technical contexts
- Never expose `/system/`, `/vault/`, `/logs/`, `/zips/` paths publicly
- Never assume mode - detect intent or ask

---

## 2. Directory Structure (Locked)

```
repo-root/
├── system/                    # LOCAL ONLY - RAG infrastructure
│   ├── core/                # Always-loaded essentials
│   │   ├── identity.yaml    # Who you are, project basics, vault paths
│   │   ├── constraints.yaml # Hard rules (delta-only, privacy)
│   │   └── env.yaml         # Termux, Android, tool paths
│   │
│   ├── lenses/              # Context modules (cross-cutting)
│   │   ├── code.yaml        # Technical: Python, Kodi, debugging
│   │   ├── design.yaml      # Creative: brainstorming, architecture
│   │   └── meta.yaml        # System: handoffs, workflows
│   │
│   ├── router/              # Intent detection & routing
│   │   └── classifier.yaml  # Scoring rules for lens selection
│   │
│   ├── vault/               # AI-accessible notes (English, technical)
│   │   ├── README.md        # Vault relationship explanation
│   │   └── projects/        # Project context (FLUID, Snoop, personal-agent)
│   │
│   ├── skills/              # Existing (8 skills with SKILL.md)
│   ├── roles/               # Existing (3 roles: archivist, debugger, optimizer)
│   └── templates/           # Output templates (existing)
│
├── projects/                # GitHub-synced (public)
│   ├── plugin.program.fluid/     # Kodi addon
│   ├── plugin.program.fluidsnoop/ # Dev tool
│   └── personal-agent/      # PRIVATE - Your agent project (gitignored)
│
├── vault/                   # LOCAL ONLY - Personal Obsidian (Dutch, private)
│   ├── Creative/
│   ├── Dagboek & Reflectie/
│   ├── Financiën/
│   └── Planning & To-Do/
│
├── scripts/                 # Build/dev tools
│   ├── qs.sh                # Main entry: generate AI context
│   ├── lib/
│   │   ├── intent_classifier.sh  # Detect intent from query
│   │   └── project_selector.sh   # Existing project picker
│   └── (existing scripts: bridge.sh, bundle.sh, lint.sh, etc.)
│
├── share/                   # AI collaboration artifacts
│   ├── handoffs/            # Session continuity
│   └── generated/           # qs.sh outputs (context files)
│
├── docs/                    # Architecture blueprints
├── logs/                    # LOCAL ONLY - Script outputs
└── zips/                    # LOCAL ONLY - Build artifacts
```

---

## 3. Key Design Decisions (Locked)

### Vault Strategy
| Aspect | Personal Vault (`/vault/`) | AI Vault (`/system/vault/`) |
|--------|---------------------------|----------------------------|
| **Location** | `vault/` | `system/vault/` |
| **Language** | Dutch (your preference) | English (AI-optimized) |
| **Content** | Personal notes, finances, diary | Technical notes, ADRs, project context |
| **Privacy** | Absolute - never exposed | AI-accessible, still local-only |
| **Sync** | You edit in Obsidian | Manual copy/adapt from personal vault |
| **RAG Access** | None (future: selective bridge) | Yes - indexed and retrieved |

### Agent Project Rules
- **Location:** `projects/personal-agent/` (not in `/system/`)
- **Privacy:** Private, gitignored, never synced to GitHub
- **Relationship:** Parallel track - learns from RAG, doesn't interfere
- **Documentation:** Context in `/system/vault/projects/personal-agent.md`
- **Tech Stack:** TBD by you (Python recommended, local LLM optional)

### Intent Classification
- **Method:** Keyword scoring (+2 for strong signals, +1 for weak)
- **Lenses:** code, design, meta (can combine if multiple score >1)
- **Default:** code lens if no strong signals detected
- **Future:** May enhance with sqlite-vec for semantic search

---

## 4. File Specifications (Locked)

### Core Files (`system/core/`)
| File | Format | Purpose | Update Frequency |
|------|--------|---------|------------------|
| `identity.yaml` | YAML+MD | Who you are, preferences, paths | Rarely |
| `constraints.yaml` | YAML+MD | Hard rules, privacy boundaries | Rarely |
| `env.yaml` | YAML+MD | Termux specifics, tool paths | When tools change |

### Lens Files (`system/lenses/`)
| File | Triggers | Content |
|------|----------|---------|
| `code.yaml` | fix, bug, def, class, import, error, python, kodi | Technical patterns, debugging |
| `design.yaml` | idea, concept, design, brainstorm, architecture | Creative frameworks, ADRs |
| `meta.yaml` | continue, handoff, status, workflow, setup | System continuity, scripts |

### Router (`system/router/`)
| File | Purpose |
|------|---------|
| `classifier.yaml` | Scoring rules, trigger definitions, examples |

### Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `qs.sh` | Generate AI context | `qs.sh "query" [--compact\|--deep]` |
| `intent_classifier.sh` | Detect intent (sourced) | `classify_intent "query"` |

---

## 5. Workflow (Locked)

### Daily Usage
1. **Start session:** Run `qs.sh "your task description"`
2. **Review context:** Check `/share/generated/context_[timestamp].md`
3. **Work:** Use context with AI assistant
4. **Handoff:** If needed, create `/share/handoffs/handoff_[date]_[topic].md`

### Context Assembly Process
1. Load `system/core/` (identity, constraints, env) - **always**
2. Classify intent from query
3. Load active lenses (1-3 depending on intent)
4. Retrieve recent handoffs (0 for compact, 1 for standard, 3 for deep)
5. Assemble to `/share/generated/context_[timestamp].md`

### Adding New Knowledge
- **Technical patterns:** Add to `system/lenses/code.yaml` or `system/vault/patterns/`
- **Project context:** Add to `system/vault/projects/[name].md`
- **ADRs:** Add to `system/vault/adrs/[decision].md`
- **Personal notes:** Add to `/vault/` (Obsidian), manually adapt to `/system/vault/` if AI-relevant

---

## 6. Integration Points (Future)

### Vault Bridge (When Ready)
- **Purpose:** Selectively pull from personal vault when explicitly requested
- **Method:** `vault_bridge.sh` with keyword search
- **Privacy:** Only searches `vault/_system/` or explicitly tagged notes
- **Trigger:** User asks "check my vault for..." or similar

### Semantic Search (When Ready)
- **Tool:** sqlite-vec (lightweight, Termux-compatible)
- **Scope:** Index `system/vault/` and `system/lenses/`
- **Fallback:** Keep keyword classifier for speed

### Agent Integration (When Ready)
- **Method:** Agent project reads from RAG system as reference
- **Contribution:** Agent learnings feed back to `system/vault/`
- **Boundary:** Agent never modifies `/system/` directly

---

## 7. Prohibited Actions (Locked)

For all AI sessions working with this system:
1. **Never** suggest moving agent project into `/system/`
2. **Never** suggest auto-syncing personal vault to AI vault
3. **Never** expose internal paths in public files
4. **Never** modify `core/` or `constraints/` without explicit user request
5. **Never** assume mode - always detect or ask
6. **Never** add Docker/heavy dependencies (Termux constraint)

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-13 | Foundation locked - core, lenses, router, coexistence rules |

---

**Lock Status:** 🔒 FOUNDATION LOCKED  
**Next Phase:** Implementation (file creation) or refinement based on usage  
**Authority:** This blueprint overrides all previous discussions and handoffs
