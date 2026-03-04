"""Utilitaires pour les providers de dépôts (GitHub, GitLab, etc.)."""
import json
import os
from typing import Any
from i18n import _

class ProviderUtils:
    def __init__(self, config: Any) -> None:
        """Charge les providers depuis config.repos_providers."""
        self.providers: list[dict[str, Any]] = config.repos_providers

    def get_provider_for_url(self, repo_url: str) -> dict[str, Any] | None:
        """Trouve le provider correspondant à l'URL du dépôt."""
        for provider in self.providers:
            base: str = provider["main_url"].split("{owner}")[0]
            if repo_url.startswith(base):
                return provider
        return None

    def split_repo_url(self, repo_url: str, provider: dict[str, Any]) -> tuple[str, str]:
        """Extrait owner et repo depuis l'URL du dépôt."""
        base: str = provider["main_url"].split("{owner}")[0]
        rest = repo_url[len(base):].strip("/")
        parts = rest.split("/")
        if len(parts) < 2:
            raise ValueError(f"Impossible d'extraire owner/repo depuis {repo_url}")
        return parts[0], parts[1]

    def build_file_url(self, provider: dict[str, Any], owner: str, repo: str, branch: str, path: str) -> str:
        """Construit l'URL d'un fichier brut."""
        return str(provider["download_file_url"].format(
            owner=owner, repo=repo, branch=branch, path=path
        ))
    
    def build_zip_url(self, provider: dict[str, Any], owner: str, repo: str, branch: str) -> str:
        """Construit l'URL ZIP du dossier racine."""
        return str(provider["download_folder_url"].format(
            owner=owner, repo=repo, branch=branch
        ))
