"""Prompt log — JSON-based storage for all prompt assemblies and review results."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_PATH = Path(__file__).parent.parent / 'outputs' / 'prompt_log.json'


class PromptLog:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_PATH.exists():
            LOG_PATH.write_text(json.dumps({'entries': []}, indent=2))

    def _load(self) -> dict:
        return json.loads(LOG_PATH.read_text())

    def _save(self, data: dict):
        LOG_PATH.write_text(json.dumps(data, indent=2, default=str))

    def record(self, prompt_type: str, prompt: str, source_layers: dict, **kwargs) -> str:
        data = self._load()
        uid = str(uuid.uuid4())[:4]
        entry_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uid

        entry = {
            'id': entry_id,
            'type': prompt_type,
            'created': datetime.now().isoformat(),
            'prompt': prompt,
            'source_layers': source_layers,
            'review': None,
            'approved': False,
            'rejected': False,
        }
        entry.update({k: v for k, v in kwargs.items()})

        data['entries'].append(entry)
        self._save(data)
        return entry_id

    def get(self, entry_id: str) -> Optional[dict]:
        data = self._load()
        for e in data['entries']:
            if e['id'] == entry_id:
                return e
        return None

    def update_review(self, entry_id: str, scores: dict):
        data = self._load()
        for e in data['entries']:
            if e['id'] == entry_id:
                e['review'] = scores
                e['approved'] = scores.get('approved', False)
                e['rejected'] = scores.get('rejected', False)
                break
        self._save(data)

    def list_entries(
        self,
        last: int = 10,
        approved_only: bool = False,
        failed_only: bool = False,
        prompt_type: Optional[str] = None,
    ) -> list:
        data = self._load()
        entries = data['entries']

        if approved_only:
            entries = [e for e in entries if e.get('approved')]
        elif failed_only:
            entries = [e for e in entries if e.get('rejected')]

        if prompt_type:
            entries = [e for e in entries if e.get('type') == prompt_type]

        return entries[-last:]

    def get_successful_fragments(self) -> list:
        data = self._load()
        fragments = []
        for e in data['entries']:
            if not e.get('approved'):
                continue
            review = e.get('review') or {}
            dims = review.get('dimensions') or {}
            for dim, score in dims.items():
                if score is not None and score >= 8.0:
                    fragments.append({
                        'fragment': e.get('prompt', '')[:80],
                        'category': dim,
                        'score': score,
                        'prompt_id': e['id'],
                    })
        return fragments
