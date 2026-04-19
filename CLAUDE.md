# CLAUDE.md — Codex Operating Instructions

Read this at the start of every session. This is the operating constitution for the Cyan Black Codex.

---

## What This Repository Is

CB-V1 is the Cyan Black production Codex — a centralized system for generating, reviewing, and iterating on MidJourney still images for the Cyan Black episodic project.

Owner: James
Purpose: Controlled image generation with canon fidelity, not random prompt experimentation.

---

## Session Start Protocol

Run this at the beginning of every session:

```bash
python codex.py load --timeline a
```

Confirm:
1. World rules loaded (no warnings)
2. Both characters loaded with state cards
3. Prompt blocks and locations available
4. Failure library accessible

If warnings exist, resolve them before generating any prompts.

---

## Core Commands

```bash
# Load and validate canon
python codex.py load [--timeline a|b]

# Generate a character prompt
python codex.py character james [--pose standing|body-shot] [--timeline a|b] [--mood MOOD] [--format portrait|landscape|square|widescreen]
python codex.py character shiba [--pose standing|body-shot] [--timeline a|b]

# Build a scene prompt
python codex.py scene ep01_sc001 [--timeline a|b] [--format landscape]

# Review an output
python codex.py review [PROMPT_ID]

# View history
python codex.py log [--last 20] [--success] [--fail] [--type character|scene]

# View patterns
python codex.py patterns successful
python codex.py patterns failed
```

---

## Workflow Rules

### Generating Prompts
1. Always specify which timeline before generating.
2. Load the relevant character's state card mentally before adjusting.
3. Do not override locked dossier elements without explicit instruction from James.
4. Log every prompt — never present a prompt that isn't in the log.

### Reviewing Outputs
- Score every output James wants to evaluate.
- Minimum score 7.0 for approval.
- Failed fragments (score < 5.0) must be added to `style/failure_library.yaml`.
- Approved patterns worth preserving go in `style/prompt_blocks.yaml`.

### Canon Discipline
- Canon files in `canon/` are LOCKED — never suggest changes unless James asks.
- Character dossiers define immutable identity — visual drift is always wrong.
- State cards define what changes per timeline — they can be updated as story develops.
- Scene cards can be added freely as new scenes are needed.

---

## File Map

```
codex/              Python engine (prompt generation, review, logging)
canon/              Hard locked world rules and episode canon
style/              Visual DNA, prompt blocks, failure library
characters/         Character dossiers and state cards
  james/            James's identity, states, prompt templates
  shiba/            SHIBA's identity, states, prompt templates
scenes/             Locations, lighting, and scene cards
  cards/            Individual scene card files
templates/          Blank templates for new documents
outputs/            Generated prompts, review queue, approved/rejected
  prompt_log.json   Full prompt history with review scores
```

---

## What Claude Must Never Do

1. Invent canon not present in the source files.
2. Change locked character dossier elements without explicit instruction.
3. Generate prompts without logging them.
4. Approve outputs based on "vibe" — always score against the rubric.
5. Present a prompt assembly without tracing it to source layers.
6. Skip the failure library check before generating new prompts.
7. Add to `style/prompt_blocks.yaml` without a review-backed approval.

---

## Adding New Content

### New character
1. Copy `templates/dossier_template.md` → `characters/[name]/dossier.md`
2. Copy `templates/state_card_template.md` → `characters/[name]/state_cards/timeline_a.md`
3. Create `timeline_b.md` with the same template
4. Create `prompts/` directory with `standing_pose.txt` and `body_shot.txt`
5. Fill in all sections — do not generate prompts from incomplete dossiers

### New scene
1. Copy `templates/scene_card_template.md` → `scenes/cards/[ep##_sc###].md`
2. Fill in all sections
3. If location doesn't exist in `scenes/locations.yaml`, add it first
4. Run `python codex.py scene [scene_id]` to test

### New location
1. Open `scenes/locations.yaml`
2. Add a new entry following the existing format
3. Test with a scene that uses the location

---

## The Four Traceability Questions

Every output must be able to answer:
1. **What canon does it obey?** → Traceable to `canon/`
2. **What state does it represent?** → Traceable to a state card (timeline + character)
3. **What scene/shot purpose does it serve?** → Traceable to `scenes/cards/`
4. **What prompt assembly produced it?** → Logged in `outputs/prompt_log.json`
