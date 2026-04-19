"""Canon loader — reads and validates all Codex source files."""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

BASE_DIR = Path(__file__).parent.parent


@dataclass
class CanonState:
    world_rules_loaded: bool = False
    episode_canon: dict = field(default_factory=dict)
    characters: dict = field(default_factory=dict)
    locations: list = field(default_factory=list)
    lighting_library: dict = field(default_factory=dict)
    prompt_blocks: dict = field(default_factory=dict)
    failure_library: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class CanonLoader:
    def __init__(self):
        self.base = BASE_DIR
        self.state = CanonState()

    def load_all(self, timeline: str = 'a') -> CanonState:
        self._load_world_rules()
        self._load_episode_canon()
        self._load_characters(timeline)
        self._load_locations()
        self._load_lighting()
        self._load_prompt_blocks()
        self._load_failure_library()
        return self.state

    def _load_world_rules(self):
        path = self.base / 'canon' / 'world_rules.md'
        if path.exists() and self._has_content(path):
            self.state.world_rules_loaded = True
        elif path.exists():
            self.state.warnings.append('world_rules.md exists but is not yet filled in')
        else:
            self.state.warnings.append('canon/world_rules.md not found')

    def _load_episode_canon(self):
        canon_dir = self.base / 'canon'
        if not canon_dir.exists():
            self.state.warnings.append('canon/ directory not found')
            return
        for f in sorted(canon_dir.glob('episode_*.md')):
            episode_id = f.stem.replace('episode_', '')
            self.state.episode_canon[episode_id] = f.read_text()

    def _load_characters(self, timeline: str):
        chars_dir = self.base / 'characters'
        if not chars_dir.exists():
            self.state.warnings.append('characters/ directory not found')
            return

        for char_dir in sorted(chars_dir.iterdir()):
            if not char_dir.is_dir():
                continue
            name = char_dir.name
            dossier = char_dir / 'dossier.md'
            state_card = char_dir / 'state_cards' / f'timeline_{timeline}.md'

            char_data = {
                'dossier': dossier.read_text() if dossier.exists() else None,
                'state': state_card.read_text() if state_card.exists() else None,
                'prompts': {},
            }

            prompts_dir = char_dir / 'prompts'
            if prompts_dir.exists():
                for p in sorted(prompts_dir.glob('*.txt')):
                    char_data['prompts'][p.stem] = p.read_text()

            self.state.characters[name] = char_data

            if not dossier.exists():
                self.state.warnings.append(f'{name}: dossier.md missing')
            elif not self._has_content(dossier):
                self.state.warnings.append(f'{name}: dossier.md not yet filled in')

            if not state_card.exists():
                self.state.warnings.append(f'{name}: state_cards/timeline_{timeline}.md missing')

    def _load_locations(self):
        path = self.base / 'scenes' / 'locations.yaml'
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                self.state.locations = data.get('locations', []) if data else []
        else:
            self.state.warnings.append('scenes/locations.yaml not found')

    def _load_lighting(self):
        path = self.base / 'scenes' / 'lighting_library.yaml'
        if path.exists():
            with open(path) as f:
                self.state.lighting_library = yaml.safe_load(f) or {}
        else:
            self.state.warnings.append('scenes/lighting_library.yaml not found')

    def _load_prompt_blocks(self):
        path = self.base / 'style' / 'prompt_blocks.yaml'
        if path.exists():
            with open(path) as f:
                self.state.prompt_blocks = yaml.safe_load(f) or {}
        else:
            self.state.warnings.append('style/prompt_blocks.yaml not found')

    def _load_failure_library(self):
        path = self.base / 'style' / 'failure_library.yaml'
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                self.state.failure_library = data.get('failures', []) if data else []

    @staticmethod
    def _has_content(path: Path) -> bool:
        text = path.read_text()
        return '[FILL IN]' not in text and len(text.strip()) > 100
