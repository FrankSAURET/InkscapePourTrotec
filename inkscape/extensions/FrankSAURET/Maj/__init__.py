
import json
import os

info_path = os.path.join(os.path.dirname(__file__), 'Info.json')
try:
	with open(info_path, 'r', encoding='utf-8') as f:
		info = json.load(f)
	__version__ = info.get('version', 'inconnue')
	__author__ = info.get('author', 'inconnu')
except Exception:
	__version__ = 'inconnue'
	__author__ = 'inconnu'

__license__ = "GPLv2"
