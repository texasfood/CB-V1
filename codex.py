#!/usr/bin/env python3
"""Cyan Black Codex — Production System CLI"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from codex.loader import CanonLoader
from codex.prompt_generator import PromptGenerator
from codex.scene_builder import SceneBuilder
from codex.review_engine import ReviewEngine
from codex.prompt_log import PromptLog


def cmd_load(args):
    loader = CanonLoader()
    state = loader.load_all(timeline=args.timeline)

    print("\n╔══════════════════════════════════════╗")
    print("║     CYAN BLACK CODEX — CANON LOAD    ║")
    print("╚══════════════════════════════════════╝\n")

    print(f"Timeline:              {args.timeline.upper()}")
    print(f"World rules:           {'✓ loaded' if state.world_rules_loaded else '✗ MISSING or unfilled'}")
    print(f"Episode canon files:   {len(state.episode_canon)}")
    print(f"Characters:            {', '.join(state.characters.keys()) or 'none found'}")
    print(f"Locations:             {len(state.locations)}")
    print(f"Lighting presets:      {len(state.lighting_library.get('presets', {}))}")
    print(f"Failure patterns:      {len(state.failure_library)}")

    if state.warnings:
        print(f"\n⚠  Warnings ({len(state.warnings)}):")
        for w in state.warnings:
            print(f"   - {w}")
        print()
        return 1
    else:
        print("\n✓  Canon state clean — ready to generate.\n")
        return 0


def cmd_character(args):
    loader = CanonLoader()
    state = loader.load_all(timeline=args.timeline)

    if args.name not in state.characters:
        available = ', '.join(state.characters.keys()) or 'none'
        print(f"✗ Character '{args.name}' not found. Available: {available}")
        return 1

    generator = PromptGenerator(state)
    log = PromptLog()

    result = generator.character_prompt(
        name=args.name,
        pose=args.pose,
        timeline=args.timeline,
        mood=args.mood,
        aspect=args.format,
    )

    entry_id = log.record(
        prompt_type='character',
        prompt=result['prompt'],
        source_layers=result['sources'],
        character=args.name,
        timeline=args.timeline,
        pose=args.pose,
    )

    width = 42
    header = f"CHARACTER — {args.name.upper()}"
    print(f"\n╔{'═' * width}╗")
    print(f"║ {header:<{width-1}}║")
    print(f"╚{'═' * width}╝\n")
    print(f"Timeline: {args.timeline.upper()} | Pose: {args.pose} | Format: {args.format}")
    if args.mood:
        print(f"Mood override: {args.mood}")
    print(f"\n── PROMPT (ID: {entry_id}) {'─' * max(0, 38 - len(entry_id))}")
    print()
    print(result['prompt'])
    print(f"\n── SOURCE LAYERS {'─' * 26}")
    for layer, value in result['sources'].items():
        print(f"  {layer:<22} {value}")
    print()

    return 0


def cmd_scene(args):
    loader = CanonLoader()
    state = loader.load_all(timeline=args.timeline)

    builder = SceneBuilder(state)
    log = PromptLog()

    result = builder.build(scene_id=args.scene_id, aspect=args.format)

    if result.get('error'):
        print(f"✗ {result['error']}")
        return 1

    entry_id = log.record(
        prompt_type='scene',
        prompt=result['prompt'],
        source_layers=result['sources'],
        scene_id=args.scene_id,
        timeline=args.timeline,
    )

    width = 42
    header = f"SCENE — {args.scene_id}"
    print(f"\n╔{'═' * width}╗")
    print(f"║ {header:<{width-1}}║")
    print(f"╚{'═' * width}╝\n")
    print(f"Timeline: {args.timeline.upper()} | Format: {args.format}")
    print(f"\n── PROMPT (ID: {entry_id}) {'─' * max(0, 38 - len(entry_id))}")
    print()
    print(result['prompt'])
    print(f"\n── SOURCE LAYERS {'─' * 26}")
    for layer, value in result['sources'].items():
        if value:
            print(f"  {layer:<22} {value}")
    print()

    return 0


def cmd_review(args):
    log = PromptLog()
    entry = log.get(args.prompt_id)

    if not entry:
        print(f"✗ Prompt ID '{args.prompt_id}' not found in log.")
        print("  Run `python codex.py log` to see available IDs.")
        return 1

    engine = ReviewEngine()
    scores = engine.interactive_review(entry)

    log.update_review(args.prompt_id, scores)

    overall = scores['overall']
    if overall >= 7.0:
        print(f"\n✓ APPROVED (score: {overall:.1f}/10) — logged to approved patterns.\n")
    elif overall >= 5.0:
        print(f"\n⚠ CONDITIONAL (score: {overall:.1f}/10) — flagged for revision.\n")
    else:
        print(f"\n✗ REJECTED (score: {overall:.1f}/10) — add failed fragments to style/failure_library.yaml\n")

    return 0


def cmd_log(args):
    log = PromptLog()
    entries = log.list_entries(
        last=args.last,
        approved_only=args.success,
        failed_only=args.fail,
        prompt_type=args.type,
    )

    if not entries:
        print("No entries found.")
        return 0

    print(f"\n╔══════════════════════════════════════╗")
    print(f"║         CODEX PROMPT LOG              ║")
    print(f"╚══════════════════════════════════════╝\n")

    for e in entries:
        if e.get('approved'):
            status = '✓'
        elif e.get('rejected'):
            status = '✗'
        else:
            status = '·'

        review = e.get('review') or {}
        score_str = f"  [{review['overall']:.1f}]" if review.get('overall') is not None else ''
        subject = e.get('character') or e.get('scene_id') or ''
        print(f"{status} {e['id']}  {e.get('type', ''):<10}  {subject:<14}{score_str}")

        if args.verbose:
            print(f"   {e.get('prompt', '')[:90]}...")
            print()

    print()
    return 0


def cmd_patterns(args):
    if args.action == 'successful':
        log = PromptLog()
        patterns = log.get_successful_fragments()
        print(f"\n── SUCCESSFUL PATTERNS {'─' * 20}\n")
        if not patterns:
            print("  No approved patterns yet. Review some outputs first.")
        for p in patterns:
            print(f"  Category: {p['category']}")
            print(f"  Fragment: {p['fragment']}")
            print(f"  Used in:  {p['prompt_id']}")
            print()

    elif args.action == 'failed':
        loader = CanonLoader()
        state = loader.load_all()
        print(f"\n── FAILURE LIBRARY {'─' * 24}\n")
        active = [f for f in state.failure_library if not f.get('archived')]
        if not active:
            print("  No active failure patterns. Run `python codex.py review` after bad outputs.")
        for f in active:
            print(f"  Pattern:  {f.get('pattern', 'N/A')}")
            print(f"  Reason:   {f.get('reason', 'N/A')}")
            print(f"  Category: {f.get('category', 'general')}")
            print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='codex',
        description='Cyan Black Codex — Production System CLI',
    )
    parser.add_argument('--version', action='version', version='CB-V1 Codex 1.0')

    sub = parser.add_subparsers(dest='command', required=True)

    # load
    p_load = sub.add_parser('load', help='Validate and load the current canon state')
    p_load.add_argument('--timeline', choices=['a', 'b'], default='a')
    p_load.set_defaults(func=cmd_load)

    # character
    p_char = sub.add_parser('character', help='Generate a character prompt set')
    p_char.add_argument('name', help='Character name (e.g. james, shiba)')
    p_char.add_argument('--pose', choices=['standing', 'body-shot', 'custom'], default='standing')
    p_char.add_argument('--timeline', choices=['a', 'b'], default='a')
    p_char.add_argument('--mood', default=None, help='Override the default mood')
    p_char.add_argument(
        '--format',
        choices=['portrait', 'landscape', 'square', 'widescreen'],
        default='portrait',
    )
    p_char.set_defaults(func=cmd_character)

    # scene
    p_scene = sub.add_parser('scene', help='Build a scene prompt from a scene card')
    p_scene.add_argument('scene_id', help='Scene card ID (e.g. ep01_sc001)')
    p_scene.add_argument('--timeline', choices=['a', 'b'], default='a')
    p_scene.add_argument(
        '--format',
        choices=['portrait', 'landscape', 'square', 'widescreen'],
        default='landscape',
    )
    p_scene.set_defaults(func=cmd_scene)

    # review
    p_review = sub.add_parser('review', help='Score an output against the rubric')
    p_review.add_argument('prompt_id', help='Prompt ID from the log')
    p_review.set_defaults(func=cmd_review)

    # log
    p_log = sub.add_parser('log', help='View prompt history')
    p_log.add_argument('--last', type=int, default=10)
    p_log.add_argument('--success', action='store_true', help='Approved entries only')
    p_log.add_argument('--fail', action='store_true', help='Rejected entries only')
    p_log.add_argument('--type', choices=['character', 'scene'], default=None)
    p_log.add_argument('--verbose', '-v', action='store_true')
    p_log.set_defaults(func=cmd_log)

    # patterns
    p_pat = sub.add_parser('patterns', help='Extract working or failed prompt patterns')
    p_pat.add_argument('action', choices=['successful', 'failed'])
    p_pat.set_defaults(func=cmd_patterns)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()
