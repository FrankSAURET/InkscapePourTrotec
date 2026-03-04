"""Installation, désinstallation des extensions."""
from i18n import _
from core.config import Config

class Installer:
    def __init__(self, config: Config):
        self.config = config

    def install(self, extension):
        # TODO: Installer une extension
        pass

    def uninstall(self, extension):
        # TODO: Désinstaller une extension
        pass
