"""Scene card to prompt converter."""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


class SceneBuilder:
    def __init__(self, canon_state):
        self.state = canon_state

    def build(self, scene_id: str, aspect: str = 'landscape') -> dict:
        card_path = BASE_DIR / 'scenes' / 'cards' / f'{scene_id}.md'

        if not card_path.exists():
            return {'error': f"Scene card '{scene_id}.md' not found in scenes/cards/"}

        card = card_path.read_text()

        location_key = self._extract_section(card, 'LOCATION')
        characters = self._extract_section(card, 'CHARACTERS')
        lighting_key = self._extract_section(card, 'LIGHTING')
        mood = self._extract_section(card, 'MOOD')
        story_intent = self._extract_section(card, 'STORY INTENT')
        shot_type = self._extract_section(card, 'SHOT TYPE')
        prompt_fragment = self._extract_section(card, 'PROMPT FRAGMENT')

        location_prompt = self._resolve_location(location_key)
        lighting_prompt = self._resolve_lighting(lighting_key)
        quality = self._get_quality()
        style = self._get_style()

        blocks = self.state.prompt_blocks
        aspect_ratios = blocks.get('aspect_ratios', {})
        aspect_flag = aspect_ratios.get(aspect, '--ar 16:9') if isinstance(aspect_ratios, dict) else '--ar 16:9'
        mj_flags = blocks.get('mj_flags', {})
        mj_flag_str = mj_flags.get('default', '--v 6.1 --q 2') if isinstance(mj_flags, dict) else '--v 6.1 --q 2'

        if prompt_fragment:
            base = prompt_fragment
        else:
            base = f"{shot_type or 'cinematic still'}, {characters}" if characters else shot_type or 'cinematic still'

        parts = [base, location_prompt or location_key, lighting_prompt, mood, quality, style]
        body = ', '.join(p for p in parts if p and p.strip())
        prompt = f'{body} {aspect_flag} {mj_flag_str}'.strip()

        return {
            'prompt': prompt,
            'sources': {
                'scene_card': f'scenes/cards/{scene_id}.md',
                'location': location_key,
                'lighting': lighting_key,
                'mood': mood,
                'story_intent': story_intent,
                'style_blocks': 'style/prompt_blocks.yaml',
                'aspect_ratio': aspect,
            },
        }

    def _extract_section(self, text: str, section: str) -> str:
        match = re.search(
            rf'##\s*{re.escape(section)}\s*\n(.*?)(?=##|\Z)',
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return ''
        return match.group(1).strip()

    def _resolve_location(self, key: str) -> str:
        for loc in self.state.locations:
            if loc.get('id') == key or loc.get('name', '').lower() == key.lower():
                return loc.get('prompt_fragment', '')
        return ''

    def _resolve_lighting(self, key: str) -> str:
        presets = self.state.lighting_library.get('presets', {})
        if isinstance(presets, dict) and key in presets:
            return presets[key].get('prompt_fragment', '')
        return ''

    def _get_quality(self) -> str:
        val = self.state.prompt_blocks.get('base_quality', [])
        return val[0] if isinstance(val, list) and val else ''

    def _get_style(self) -> str:
        val = self.state.prompt_blocks.get('style_core', [])
        return val[0] if isinstance(val, list) and val else ''
