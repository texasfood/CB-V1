"""Cyan Black Codex — Flask web application."""

import base64
import os
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

import sys
sys.path.insert(0, str(Path(__file__).parent))

from codex.loader import CanonLoader
from codex.prompt_generator import PromptGenerator
from codex.review_engine import ReviewEngine, RUBRIC
from codex.scene_builder import SceneBuilder
from codex.prompt_log import PromptLog
from codex import studio

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-key')
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15 MB upload ceiling

POSES = ['standing', 'body-shot', 'custom']
TIMELINES = ['a', 'b']
FORMATS = ['portrait', 'landscape', 'square', 'widescreen']


def _load(timeline='a'):
    loader = CanonLoader()
    return loader.load_all(timeline=timeline)


def _scene_ids():
    cards_dir = Path(__file__).parent / 'scenes' / 'cards'
    if not cards_dir.exists():
        return []
    return sorted(f.stem for f in cards_dir.glob('*.md'))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    state = _load()
    log = PromptLog()
    recent = log.list_entries(last=5)
    total = len(log.list_entries(last=9999))
    approved = len(log.list_entries(last=9999, approved_only=True))
    return render_template(
        'index.html',
        warnings=state.warnings,
        characters=sorted(state.characters.keys()),
        location_count=len(state.locations),
        failure_count=len([f for f in state.failure_library if not f.get('archived')]),
        total_prompts=total,
        approved_prompts=approved,
        recent=recent,
    )


@app.route('/studio', methods=['GET', 'POST'])
def studio_view():
    state = _load()
    characters = sorted(state.characters.keys())

    result = None
    error = None
    form_data = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()
        name = form_data.get('name') or None
        timeline = form_data.get('timeline', 'a')
        aspect = form_data.get('format', 'portrait')
        quality = form_data.get('quality', 'standard')
        mood = form_data.get('mood') or None
        intent = (form_data.get('intent') or '').strip()

        if not intent:
            error = 'Tell the Codex what you want in the image — one line is enough.'
        else:
            try:
                ref_bytes = None
                ref_data_url = None
                upload = request.files.get('reference')
                if upload and upload.filename:
                    ref_bytes = studio.prep_image(upload)
                    ref_data_url = 'data:image/png;base64,' + base64.b64encode(ref_bytes).decode()

                client = studio._client()
                context = studio.build_context(name, timeline)
                written = studio.write_prompt(
                    client, context, intent, name, timeline, aspect, mood, ref_data_url,
                )
                b64 = studio.generate_image(
                    client, written['prompt'], aspect, quality, ref_bytes,
                )
                image_data_url = 'data:image/png;base64,' + b64

                log = PromptLog()
                eid = log.record(
                    prompt_type='studio',
                    prompt=written['prompt'],
                    source_layers={
                        'intent': intent,
                        'character': name or 'unspecified',
                        'timeline': timeline,
                        'reference_used': bool(ref_bytes),
                        'engine': studio.IMAGE_MODEL,
                    },
                    character=name,
                    timeline=timeline,
                    intent=intent,
                )
                studio.save_image(b64, eid)

                result = {
                    'id': eid,
                    'image': image_data_url,
                    'prompt': written['prompt'],
                    'midjourney': written.get('midjourney', ''),
                    'notes': written.get('notes', ''),
                    'missing': written.get('missing_canon', []),
                    'reference': ref_data_url,
                }
            except studio.StudioError as e:
                error = str(e)
            except Exception as e:
                error = f'Something went wrong: {e}'

    return render_template(
        'studio.html',
        characters=characters,
        timelines=TIMELINES,
        formats=FORMATS,
        has_key=studio.has_key(),
        result=result,
        error=error,
        form_data=form_data,
    )


@app.route('/character', methods=['GET', 'POST'])
def character():
    timeline = request.form.get('timeline', 'a') if request.method == 'POST' else 'a'
    state = _load(timeline=timeline)
    characters = sorted(state.characters.keys())

    result = None
    error = None
    form_data = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()
        name = form_data.get('name', '')

        if not name:
            error = 'Select a character.'
        elif name not in state.characters:
            error = f"Character '{name}' not found. Check that dossier.md exists."
        else:
            gen = PromptGenerator(state)
            r = gen.character_prompt(
                name=name,
                pose=form_data.get('pose', 'standing'),
                timeline=timeline,
                mood=form_data.get('mood') or None,
                aspect=form_data.get('format', 'portrait'),
            )
            log = PromptLog()
            eid = log.record(
                prompt_type='character',
                prompt=r['prompt'],
                source_layers=r['sources'],
                character=name,
                timeline=timeline,
                pose=form_data.get('pose', 'standing'),
            )
            result = {'id': eid, 'prompt': r['prompt'], 'sources': r['sources']}

    return render_template(
        'character.html',
        characters=characters,
        poses=POSES,
        timelines=TIMELINES,
        formats=FORMATS,
        result=result,
        error=error,
        form_data=form_data,
    )


@app.route('/scene', methods=['GET', 'POST'])
def scene():
    state = _load()
    scene_ids = _scene_ids()

    result = None
    error = None
    form_data = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()
        scene_id = form_data.get('scene_id', '')

        if not scene_id:
            error = 'Select a scene.'
        else:
            builder = SceneBuilder(state)
            r = builder.build(
                scene_id=scene_id,
                aspect=form_data.get('format', 'landscape'),
            )
            if r.get('error'):
                error = r['error']
            else:
                log = PromptLog()
                eid = log.record(
                    prompt_type='scene',
                    prompt=r['prompt'],
                    source_layers=r['sources'],
                    scene_id=scene_id,
                    timeline=form_data.get('timeline', 'a'),
                )
                result = {'id': eid, 'prompt': r['prompt'], 'sources': r['sources']}

    return render_template(
        'scene.html',
        scene_ids=scene_ids,
        timelines=TIMELINES,
        formats=FORMATS,
        result=result,
        error=error,
        form_data=form_data,
    )


@app.route('/log')
def log_view():
    log = PromptLog()
    filter_type = request.args.get('type') or None
    filter_status = request.args.get('status') or None
    last = min(int(request.args.get('last', 50)), 200)

    entries = log.list_entries(
        last=last,
        approved_only=(filter_status == 'approved'),
        failed_only=(filter_status == 'rejected'),
        prompt_type=filter_type,
    )
    return render_template(
        'log.html',
        entries=list(reversed(entries)),
        filter_type=filter_type,
        filter_status=filter_status,
    )


@app.route('/review/<prompt_id>', methods=['GET', 'POST'])
def review(prompt_id):
    log = PromptLog()
    entry = log.get(prompt_id)

    if not entry:
        return render_template('error.html', message=f"Prompt ID '{prompt_id}' not found."), 404

    if request.method == 'POST':
        dimensions = {}
        notes = {}
        for key in RUBRIC:
            raw = request.form.get(key, '').strip()
            dimensions[key] = float(raw) if raw else None
            note = request.form.get(f'{key}_note', '').strip()
            if note:
                notes[key] = note

        engine = ReviewEngine()
        overall = engine._weighted_average(dimensions)
        scores = {
            'dimensions': dimensions,
            'notes': notes,
            'overall': round(overall, 2),
            'approved': overall >= 7.0,
            'rejected': overall < 5.0,
        }
        log.update_review(prompt_id, scores)
        return redirect(url_for('log_view'))

    return render_template('review.html', entry=entry, rubric=RUBRIC)


@app.route('/patterns')
def patterns():
    state = _load()
    log = PromptLog()
    successful = log.get_successful_fragments()
    failed = [f for f in state.failure_library if not f.get('archived')]
    return render_template('patterns.html', successful=successful, failed=failed)


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
