"""Studio engine — reference image + one-line intent → canon-aware prompt → rendered image.

Uses a single OpenAI key for both jobs:
  1. A text model reads the canon files and writes the massive prompt.
  2. gpt-image-1 renders the picture, using the uploaded reference for consistency.
"""

import base64
import io
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Which OpenAI models to use. Overridable via env so you can bump them without a code change.
TEXT_MODEL = os.environ.get('OPENAI_TEXT_MODEL', 'gpt-4o')
IMAGE_MODEL = os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-1')

SIZE_MAP = {
    'portrait':   '1024x1536',
    'landscape':  '1536x1024',
    'square':     '1024x1024',
    'widescreen': '1536x1024',  # gpt-image-1 has no 21:9; landscape is the closest
}
QUALITY_MAP = {'draft': 'low', 'standard': 'medium', 'high': 'high'}

AR_FLAG = {'portrait': '2:3', 'landscape': '16:9', 'square': '1:1', 'widescreen': '21:9'}


class StudioError(Exception):
    """Raised for expected, user-facing problems (missing key, bad upload, API refusal)."""


# ── Canon context ─────────────────────────────────────────────────────────────

def _read(rel: str) -> str:
    p = BASE_DIR / rel
    return p.read_text() if p.exists() else ''


def build_context(name: str, timeline: str) -> str:
    """Gather every relevant canon layer into one briefing for the prompt-writer."""
    sections = [
        ('WORLD RULES', _read('canon/world_rules.md')),
        ('TIMELINE MAP', _read('canon/timeline_map.md')),
    ]
    if name:
        sections.append(
            (f'{name.upper()} — LOCKED IDENTITY DOSSIER', _read(f'characters/{name}/dossier.md'))
        )
        sections.append(
            (f'{name.upper()} — STATE CARD (TIMELINE {timeline.upper()})',
             _read(f'characters/{name}/state_cards/timeline_{timeline}.md'))
        )
    sections += [
        ('VISUAL DNA', _read('style/visual_dna.md')),
        ('STYLE BLOCKS', _read('style/prompt_blocks.yaml')),
        ('FAILURE LIBRARY — PATTERNS TO AVOID', _read('style/failure_library.yaml')),
    ]
    parts = []
    for title, body in sections:
        if body and body.strip():
            parts.append(f'===== {title} =====\n{body.strip()}')
    return '\n\n'.join(parts)


# ── OpenAI client ─────────────────────────────────────────────────────────────

def has_key() -> bool:
    return bool(os.environ.get('OPENAI_API_KEY'))


def _client():
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise StudioError(
            'OpenAI API key not set. Add OPENAI_API_KEY in your Render dashboard → '
            'Environment, then redeploy.'
        )
    try:
        from openai import OpenAI
    except ImportError:
        raise StudioError('The openai package is not installed. Run: pip install openai')
    return OpenAI(api_key=key)


# ── Reference image prep ──────────────────────────────────────────────────────

def prep_image(file_storage) -> bytes:
    """Normalise any uploaded image to a reasonably sized PNG the API will accept."""
    try:
        from PIL import Image
    except ImportError:
        raise StudioError('Pillow is not installed. Run: pip install Pillow')
    try:
        img = Image.open(file_storage.stream).convert('RGBA')
    except Exception:
        raise StudioError('That file could not be read as an image. Use PNG, JPG, or WebP.')
    img.thumbnail((1536, 1536))
    out = io.BytesIO()
    img.save(out, format='PNG')
    return out.getvalue()


# ── The prompt-writer ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the prompt-writer for the Cyan Black image Codex — a controlled \
still-generation system. You turn a short creative instruction into ONE dense, production-grade \
image prompt that is faithful to the project's locked canon.

Rules:
- OBEY the locked character dossier and world rules. Never contradict a character's fixed identity \
(build, face, hair, silhouette, clothing logic). Visual drift is always wrong.
- Apply the relevant timeline's visual signature (colour grade, environmental state).
- Honour the project's Visual DNA: palette, lighting philosophy, texture, composition.
- AVOID every pattern listed in the failure library.
- If a canon section still contains "[FILL IN]" placeholders, IGNORE those blanks — do not copy \
placeholder text into the prompt. Lean on the reference image and your judgement instead, and list \
what was missing in "missing_canon".
- If a reference image is provided, preserve the subject's identity and the world's look while \
staging the NEW action the user asked for.

Return strict JSON with these keys:
  "prompt": a single dense, comma-led visual description (roughly 120-260 words) written for an \
image-generation model — concrete nouns, materials, light, camera, mood. No "--" flags.
  "midjourney": the same intent rewritten in MidJourney style, ending with the aspect flag.
  "notes": one short sentence on the key creative choices.
  "missing_canon": array of short strings naming canon that was blank or missing (empty if all present).
Respond with JSON only."""


def write_prompt(client, context, intent, name, timeline, aspect, mood, reference_data_url=None):
    brief = [
        f'PROJECT CANON BRIEFING:\n{context}' if context.strip()
        else 'PROJECT CANON BRIEFING: (canon files are still mostly empty — rely on the reference image and intent.)',
        '',
        f'CHARACTER: {name or "unspecified — infer from the reference image"}',
        f'TIMELINE: {timeline.upper()}',
        f'ASPECT / FORMAT: {aspect} (MidJourney flag --ar {AR_FLAG.get(aspect, "2:3")})',
        f'MOOD OVERRIDE: {mood}' if mood else 'MOOD: use the state card / scene-appropriate default',
        '',
        f'WHAT THE USER WANTS IN THIS IMAGE:\n"{intent}"',
        '',
        'Write the prompt now. Return JSON only.',
    ]
    text_block = '\n'.join(brief)

    if reference_data_url:
        user_content = [
            {'type': 'text', 'text': text_block +
             '\n\nA REFERENCE IMAGE is attached — preserve this subject/look while staging the new action.'},
            {'type': 'image_url', 'image_url': {'url': reference_data_url}},
        ]
    else:
        user_content = text_block

    try:
        resp = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_content},
            ],
            response_format={'type': 'json_object'},
            temperature=0.7,
        )
    except Exception as e:
        raise StudioError(f'Prompt-writer call failed: {e}')

    raw = resp.choices[0].message.content or '{}'
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {'prompt': raw, 'midjourney': raw, 'notes': '', 'missing_canon': []}

    if not data.get('prompt'):
        raise StudioError('The prompt-writer returned no prompt. Try rephrasing your instruction.')
    data.setdefault('midjourney', data['prompt'])
    data.setdefault('notes', '')
    data.setdefault('missing_canon', [])
    return data


# ── The image renderer ────────────────────────────────────────────────────────

def generate_image(client, prompt, aspect, quality, reference_bytes=None) -> str:
    """Return a base64 PNG. Uses the edit endpoint when a reference image is supplied."""
    size = SIZE_MAP.get(aspect, '1024x1024')
    q = QUALITY_MAP.get(quality, 'medium')
    try:
        if reference_bytes:
            bio = io.BytesIO(reference_bytes)
            bio.name = 'reference.png'
            result = client.images.edit(
                model=IMAGE_MODEL, image=bio, prompt=prompt, size=size, quality=q,
            )
        else:
            result = client.images.generate(
                model=IMAGE_MODEL, prompt=prompt, size=size, quality=q,
            )
    except Exception as e:
        msg = str(e)
        if 'content_policy' in msg or 'safety' in msg.lower():
            raise StudioError('The image request was blocked by the safety system. Adjust the instruction.')
        raise StudioError(f'Image generation failed: {msg}')

    b64 = result.data[0].b64_json
    if not b64:
        raise StudioError('The image model returned no image. Try again or lower the quality.')
    return b64


# ── Persistence helper ────────────────────────────────────────────────────────

def save_image(b64: str, entry_id: str):
    """Best-effort save to disk. Returns the path, or None if it couldn't be written."""
    data_dir = os.environ.get('CODEX_DATA_DIR')
    base = Path(data_dir) if data_dir else BASE_DIR / 'outputs'
    try:
        d = base / 'generated'
        d.mkdir(parents=True, exist_ok=True)
        p = d / f'{entry_id}.png'
        p.write_bytes(base64.b64decode(b64))
        return str(p)
    except Exception:
        return None
