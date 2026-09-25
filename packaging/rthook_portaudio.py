"""PyInstaller-Laufzeithook (Linux): sounddevice sucht PortAudio über
ctypes.util.find_library, das nur Systembibliotheken kennt. Die mitgelieferte
libportaudio.so.2 aus dem Paket soll Vorrang haben."""
import ctypes.util
import os
import sys

_find_library = ctypes.util.find_library


def _find_bundled(name):
    if name == "portaudio":
        path = os.path.join(sys._MEIPASS, "libportaudio.so.2")
        if os.path.exists(path):
            return path
    return _find_library(name)


ctypes.util.find_library = _find_bundled
