# CB-V1 — Cyan Black Codex

**Version:** 1.0  
**Owner:** James  
**Purpose:** Controlled still generation system for the Cyan Black episodic project

---

## Quick Start

```bash
# 1. Validate your canon state
python codex.py load

# 2. Generate a character prompt
python codex.py character james --pose standing --timeline a

# 3. Take that prompt to MidJourney, run it, come back

# 4. Review the output
python codex.py review [PROMPT_ID from step 2]

# 5. View what's working
python codex.py patterns successful
```

---

## What This System Does

The Codex is a production control system, not a folder of prompts. It:

- **Locks canon** so character identity and world rules don't drift between sessions
- **Assembles prompts** from reusable, tested building blocks
- **Logs everything** so every output is traceable back to its source
- **Scores outputs** against a defined rubric so approval isn't just vibes
- **Learns over time** by accumulating approved patterns and flagging failure patterns

---

## System Map

| Directory | What it contains |
|-----------|-----------------|
| `canon/` | Hard world rules, episode canon, timeline map |
| `style/` | Visual DNA, prompt blocks, failure library |
| `characters/` | Identity dossiers, state cards, prompt templates |
| `scenes/` | Location library, lighting library, scene cards |
| `templates/` | Blank templates for adding new content |
| `outputs/` | Prompt log, approved stills, rejected stills |
| `codex/` | Python engine (don't edit unless extending) |

---

## Setup (First Session)

Fill these files in order before running any prompt generation:

1. `canon/world_rules.md` — your world rules
2. `canon/episode_01_canon.md` — Episode 1 facts
3. `canon/timeline_map.md` — your two timelines
4. `characters/james/dossier.md` — James's locked identity
5. `characters/shiba/dossier.md` — SHIBA's locked identity
6. State cards for both characters in both timelines
7. `style/visual_dna.md` — your visual identity
8. `style/prompt_blocks.yaml` — your starting style language
9. Run `python codex.py load` — resolve any warnings before generating

---

## The Review Rubric

Every output is scored across five dimensions:

| Dimension | Weight | Question |
|-----------|--------|----------|
| Canon Fidelity | 25% | Does it obey locked world rules and character definitions? |
| Character Accuracy | 25% | Are appearances, clothing, and silhouettes correct? |
| Visual Clarity | 20% | Is it readable at intended print/screen size? |
| Print Impact | 15% | Does it hold up at print resolution with strong composition? |
| Mood Alignment | 15% | Does the mood match the scene intent? |

- Score ≥ 7.0: **Approved** — patterns logged
- Score 5.0–6.9: **Conditional** — flag for revision
- Score < 5.0: **Rejected** — failure fragments logged

---

## Command Reference

```bash
python codex.py load                         # Validate canon state
python codex.py load --timeline b            # Load Timeline B

python codex.py character james              # Standing pose, Timeline A, portrait
python codex.py character james --pose body-shot --timeline b --format landscape
python codex.py character shiba --mood grief

python codex.py scene ep01_sc001             # Build scene prompt
python codex.py scene ep01_sc001 --format widescreen

python codex.py review 20240101-120000-a1b2  # Score an output interactively

python codex.py log                          # Last 10 entries
python codex.py log --last 25 --success      # Last 25 approved only
python codex.py log --fail --type character  # Failed character prompts

python codex.py patterns successful          # What's working
python codex.py patterns failed              # What to avoid
```

---

## Adding to the System

**New character:** See `templates/dossier_template.md`  
**New scene:** See `templates/scene_card_template.md`  
**New location:** Add to `scenes/locations.yaml`  
**New prompt block:** Only after a reviewed, approved output confirms it works

---

## Requirements

```bash
pip install pyyaml
```

Python 3.8+ required. No other dependencies.
