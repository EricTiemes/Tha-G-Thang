🎯 Ways to reuse this script — now and after small adjustments

Your script is now a template engine for turning any folder of .md prompts into a unified YAML specialist. Here's how to reuse it:

---

✅ 1. AS-IS — New prompt collections

```bash
# You downloaded new prompt packs from the internet
./create_specialists.sh ~/Downloads/new_prompts /ai/lib
```

Result: Instant YAML specialists for any new theme.

---

✅ 2. AS-IS — Different source folders

```bash
# Generate from a specific subfolder only
./create_specialists.sh /ai/prompts/Entertain /ai/lib/entertain_only
```

Result: Specialist for just one category.

---

✅ 3. MINOR ADJUST — Change output format (JSON)

Change one line in the script:

```bash
OUTPUT_NAME="specialist.yaml"  →  OUTPUT_NAME="specialist.json"
```

Then modify the cat > "$outfile" << EOF block to output JSON instead of YAML.

Use case: Feeding specialists into web apps or APIs.

---

✅ 4. MINOR ADJUST — Add frontmatter for Obsidian

Modify the output to include Obsidian-compatible frontmatter:

```yaml
---
name: "Entertain Specialist"
modes: [expand, sequence]
roles: [companion, maker]
---
You are an entertainment specialist...
```

Use case: Directly usable in Obsidian notes.

---

✅ 5. MINOR ADJUST — Generate system prompts only (no YAML)

Remove the YAML wrapper, output just the raw system prompt:

```bash
echo "$system_prompt" > "$dir/$folder"_system.txt
```

Use case: Quick copy-paste into ChatGPT, Claude, etc.

---

✅ 6. MAJOR ADJUST — Batch update all specialists

When you improve your meta-prompt, regenerate everything:

```bash
# Delete old lib
rm -rf /ai/lib/*
# Regenerate all with new prompt
./create_specialists.sh /ai/prompts /ai/lib
```

---

✅ 7. MAJOR ADJUST — Add embedding generation

Insert a step after YAML creation:

```bash
# Generate embedding of the system prompt
ollama embeddings -m nomic-embed-text -p "$system_prompt" > "$dir/embedding.json"
```

Use case: Semantic search across your specialist library.

---

✅ 8. MAJOR ADJUST — Auto-tag modes/roles via keywords

Replace the hardcoded folder mappings with AI detection:

```bash
# Ask Ollama to suggest modes/roles based on content
suggestion=$(ollama run "$MODEL" "Suggest 2 modes and 2 roles from this list: $all_modes_text\n\nPrompt:\n$combined")
```

Use case: No manual mapping needed — script learns.

---

✅ 9. MAJOR ADJUST — Watch mode for auto-updates

Wrap the script in a loop with inotifywait:

```bash
while inotifywait -r -e modify,create,delete /ai/prompts; do
    ./create_specialists.sh
done
```

Use case: Whenever you edit/add a prompt, specialist auto-updates.

---

✅ 10. COMPLETELY DIFFERENT — Use it for non-prompt text

Feed it meeting notes, documentation, or articles instead of prompts:

```bash
# Each .md file = one document on a topic
./create_specialists.sh ~/documents/project-x /ai/lib/project-specialists
```

Result: A "specialist" that knows everything about that topic.

---

🧠 The core pattern your script solves:

Input: Folder of .md files, each describing ONE capability
Output: ONE YAML file that combines ALL capabilities into a unified system prompt

This pattern is endlessly reusable for:

· Team onboarding — turn employee expertise docs into a "team specialist"
· Course materials — turn lesson plans into a "tutor specialist"
· Product docs — turn feature docs into a "support specialist"
· Research papers — turn abstracts into a "domain specialist"

---

Your script is now a permanent tool in your AI toolkit.
One small change, infinite applications.