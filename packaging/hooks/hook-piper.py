"""PyInstaller-Hook für Piper (Sprachausgabe im Reiter Sprechen).

Statt --collect-all piper nur, was die deutsche Stimme braucht: die
Aussprachedaten von espeak-ng ohne die Wörterbücher der übrigen rund 115
Sprachen und ohne die Modelle für Hebräisch und Arabisch (zusammen gut
40 MB). Der Python-Code bleibt vollständig, piper.voice importiert ihn."""
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

KEEP_DICTS = ("de_dict", "en_dict")

datas = [
    (src, dest) for src, dest in collect_data_files("piper")
    if not src.endswith(".onnx") and not (src.endswith("_dict") and not src.endswith(KEEP_DICTS))
]
binaries = collect_dynamic_libs("piper")
hiddenimports = collect_submodules("piper", filter=lambda name: ".train" not in name)
