"""Gestion des dépôts d'extensions (GitHub, ZIP, local)."""
import json
from i18n import _
from core.config import Config

class RepoManager:
    def __init__(self, config: Config):
        self.config = config
        self.repos = self.load_repos()

    def load_repos(self):
        # TODO: Charger la liste des dépôts depuis la config
        return []

    def add_repo(self, repo):
        # TODO: Ajouter un dépôt
        pass

    def remove_repo(self, repo):
        # TODO: Supprimer un dépôt
        pass

    def list_extensions(self):
        # TODO: Lister les extensions valides dans chaque repo
        return []
