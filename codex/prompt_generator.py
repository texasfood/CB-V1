"""Prompt assembly engine — builds MidJourney prompts from canon components."""

import re
from typing import Optional


class PromptGenerator:
    def __init__(self, canon_state):
        self.state = canon_state
        self.blocks = canon_state.prompt_blocks

    def character_prompt(
        self,
        name: str,
        pose: str,
        timeline: str,
        mood: Optional[str],
        aspect: str,
    ) -> dict:
        char = self.state.characters.get(name, {})

        identity = self._extract_section(char.get('dossier', '') or '', 'PROMPT FRAGMENT')
        state_mod = self._extract_section(char.get('state', '') or '', 'PROMPT MODIFIERS')
        default_mood = self._extract_section(char.get('state', '') or '', 'DEFAULT MOOD')

        pose_key = pose.replace('-', '_')
        pose_template = (char.get('prompts', {}) or {}).get(pose_key, '').strip()
        if not pose_template:
            pose_template = f'{name}, {pose} pose'

        quality = self._pick_list('base_quality')
        style = self._pick_list('style_core')
        mood_text = mood or default_mood or ''
        mj_flags = self._get_mj_flags()
        aspect_flag = self._aspect_flag(aspect)

        parts = [
            pose_template,
            identity,
            state_mod,
            mood_text,
            quality,
            style,
        ]
        body = ', '.join(p for p in parts if p and p.strip())
        prompt = f'{body} {aspect_flag} {mj_flags}'.strip()

        return {
            'prompt': prompt,
            'sources': {
                'canon': 'canon/world_rules.md',
                'character_dossier': f'characters/{name}/dossier.md',
                'state_card': f'characters/{name}/state_cards/timeline_{timeline}.md',
                'pose_template': f'characters/{name}/prompts/{pose_key}.txt',
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
        raw = match.group(1).strip()
        # If the section contains a fenced code block, use only its contents —
        # the surrounding prose is template instructions, not prompt material.
        code_match = re.search(r'```[^\n]*\n(.*?)```', raw, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return raw.strip()

    def _pick_list(self, key: str) -> str:
        val = self.blocks.get(key, [])
        if isinstance(val, list):
            return val[0] if val else ''
        if isinstance(val, str):
            return val
        return ''

    def _get_mj_flags(self) -> str:
        mj = self.blocks.get('mj_flags', {})
        if isinstance(mj, dict):
            return mj.get('default', '--v 6.1 --q 2')
        return '--v 6.1 --q 2'

    def _aspect_flag(self, aspect: str) -> str:
        ratios = self.blocks.get('aspect_ratios', {})
        if isinstance(ratios, dict) and aspect in ratios:
            return ratios[aspect]
        return {
            'portrait': '--ar 2:3',
            'landscape': '--ar 16:9',
            'square': '--ar 1:1',
            'widescreen': '--ar 21:9',
        }.get(aspect, '--ar 2:3')
