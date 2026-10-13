"""Lizenzen und Quellarchive der Builds (packaging/third_party_licenses.py,
packaging/gpl_sources.py), ohne Netz."""
import importlib.util
import unittest
from importlib import metadata
from pathlib import Path

import tests  # noqa: F401  (Pfad und sounddevice-Attrappe)

PACKAGING = Path(__file__).resolve().parent.parent / "packaging"


def _script(name: str):
    # Der Ordner packaging/ ist kein Paket (und heißt wie das PyPI-Paket packaging).
    spec = importlib.util.spec_from_file_location(name, PACKAGING / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ThirdPartyLicensesTest(unittest.TestCase):
    def test_every_bundled_part_with_its_text(self):
        licenses = _script("third_party_licenses")
        text = licenses.build()
        names = {licenses._key(d.metadata["Name"]) for d in licenses.bundled()}
        self.assertTrue({"numpy", "sounddevice", "lameenc"} <= names)
        for section in ("## numpy ", "## lameenc ", "## LAME 3.100", "## PortAudio", "## Python ", "## Tcl/Tk",
                        "## Stimmen / Voices"):
            self.assertIn(section, text)
        self.assertIn("GNU LESSER GENERAL PUBLIC LICENSE", text)  # lameenc
        self.assertIn("Permission is hereby granted", text)  # PortAudio
        self.assertNotIn("lessac", text.lower())  # Stimme mit Forschungs-Datensatz
        try:
            metadata.distribution("piper-tts")
        except metadata.PackageNotFoundError:
            return
        self.assertIn("## piper-tts ", text)
        self.assertIn("GNU GENERAL PUBLIC LICENSE", text)
        self.assertEqual(text.count("```") % 2, 0)  # jeder Lizenztext sauber eingefasst


class GplSourcesTest(unittest.TestCase):
    def test_finds_espeak_and_lame_in_the_cmake_files(self):
        sources = _script("gpl_sources")
        self.assertEqual(sources.espeak_ref(
            "ExternalProject_Add(espeak_ng_external\n    GIT_REPOSITORY https://github.com/espeak-ng/espeak-ng.git\n"
            "    GIT_TAG 724808c  # 2026-Apr-06\n"), "724808c")
        url, version, sha = sources.lame_source(
            "    URL https://sourceforge.net/projects/lame/files/lame/3.100/lame-3.100.tar.gz/download\n"
            "    URL_HASH SHA256=DDFE36cab873\n")
        self.assertEqual((version, sha), ("3.100", "ddfe36cab873"))
        self.assertTrue(url.endswith("/download"))
        with self.assertRaises(SystemExit):
            sources.espeak_ref("GIT_TAG fehlt")
        self.assertRegex(sources.pinned("piper-tts"), r"^\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
