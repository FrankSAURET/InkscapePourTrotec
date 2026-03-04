"""Gestion des mises à jour des extensions."""
from i18n import _
from core.config import Config

class Updater:
    def __init__(self, config: Config):
        self.config = config

    def check_updates(self):
        # TODO: Vérifier les mises à jour disponibles
        pass

    def update(self, extension):
        # TODO: Mettre à jour une extension
        pass
