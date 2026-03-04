"""
Gestion de la configuration globale du gestionnaire d’extensions.
"""
import json
import os
from typing import Any
from i18n import _

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')


class Config:
    def __init__(self, repos: list[str] | None = None, update_frequency: int = 7, colors: dict[str, str] | None = None, subjects: list[str] | None = None, show_only_updates: bool = True, format_text: dict[str, Any] | None = None) -> None:
        # Charger repos.json
        repos_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'repos.json')
        with open(repos_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.repos_providers: list[dict[str, Any]] = data["providers"]

        self.repos: list[str] = repos or []
        self.update_frequency: int = update_frequency
        self.colors: dict[str, str] = colors or {}
        self.subjects: list[str] = subjects or []
        self.show_only_updates: bool = show_only_updates
        self.format_text: dict[str, Any] = format_text or {}


    @classmethod
    def load(cls) -> 'Config':
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            params = data.get('Params', [{}])[0]
            template = data.get('Template', [{}])[0]
            repos = params.get('repos', [])
            update_frequency = params.get('update_frequency', 7)
            subjects = params.get('subjects', [])
            show_only_updates = params.get('show_only_updates', True)
            colors = template.get('colors', {})
            format_text = template.get('format_text', {})
            return cls(repos=repos, update_frequency=update_frequency, colors=colors, subjects=subjects, show_only_updates=show_only_updates, format_text=format_text)
        except Exception:
            return cls()

    def save(self) -> None:
        # Sauvegarde au format imbriqué (Params/Template)
        data = {
            'Params': [
                {
                    'repos': self.repos,
                    'update_frequency': self.update_frequency,
                    'subjects': self.subjects,
                    'show_only_updates': self.show_only_updates
                }
            ],
            'Template': [
                {
                    'colors': self.colors,
                    'format_text': self.format_text
                }
            ]
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
