"""Module de traduction centralisé pour Maj."""
import gettext
import os
import xml.etree.ElementTree as ET
from typing import Callable

_translator: Callable[[str], str] = gettext.gettext
lang_code: str = 'fr'


def _read_inkscape_language() -> str | None:
    """Lit la langue définie dans preferences.xml d'Inkscape."""
    # Chemins possibles selon OS
    paths = [
        os.path.expanduser("~/.config/inkscape/preferences.xml"),  # Linux
        os.path.join(os.environ.get("APPDATA", ""), "Inkscape", "preferences.xml"),  # Windows
        os.path.expanduser("~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/preferences.xml"),  # macOS
    ]

    for path in paths:
        if os.path.exists(path):
            try:
                tree = ET.parse(path)
                root = tree.getroot()
                ui_group = root.find(".//group[@id='ui']")
                if ui_group is not None:
                    lang = ui_group.get("language")
                    if lang:
                        return lang.split('_')[0]
            except Exception:
                pass

    return None


def _read_system_language() -> str | None:
    """Récupère la langue du système via les variables d'environnement."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return value.split(':')[0].split('_')[0]
    return None


def setup(localedir: str) -> None:
    """Configure la traduction en suivant la priorité :
    1. Langue définie dans preferences.xml
    2. Langue du système
    3. Français par défaut
    """
    global _translator, lang_code

    lang = _read_inkscape_language()
    if not lang:
        lang = _read_system_language()
    if not lang:
        lang = "fr"

    lang_code = lang

    trans = gettext.translation('Maj', localedir=localedir, languages=[lang_code], fallback=True)
    _translator = trans.gettext


def _(message: str) -> str:
    """Traduit un message en utilisant le traducteur configuré."""
    return _translator(message)
