"""Kurzwellen-Bandbedingungen für den QSO-Modus, alles einzeln zuschaltbar
und mit eigenem Pegel (0..1, siehe EFFECTS):

- Rauschen: Bandrauschen, wie es aus einem SSB-/CW-Empfänger kommt (auf
  ca. 300–2700 Hz begrenzt, leicht zu den Höhen abfallend).
- QRN: vereinzelte Knackstörungen, z. B. von Gewittern.
- QSB: jede Station kommt unterschiedlich stark an und schwankt langsam in
  der Lautstärke (Fading).
- Chirp: einige Stationen haben einen schlecht stabilisierten Sender, der
  beim Tasten kurz neben der Frequenz liegt („zwitschert“).
- SSB-Gebrabbel: eine verstimmte SSB-Station auf der Nachbarfrequenz.
  Synthetisch erzeugt (Sägezahn-Stimme durch wechselnde Vokal-Formanten,
  Silben, Wörter, Sprecherwechsel), also unverständlich, klingt aber nach
  Sprache.
- CW-QRM: ein Contest-Run auf der Nachbarfrequenz, schneller und leiser.

Rauschen und SSB-Gebrabbel werden einmal als Schleife per FFT geformt. Weil
die FFT-Synthese periodisch ist, geht das Ende nahtlos in den Anfang über;
so kostet das laufende Mischen fast nichts."""
import random

import numpy as np

import qso_text
from morse import SAMPLE_RATE, build_text, silence

# Schlüssel der Störungen; BandConditions.enabled/levels sind danach
# indiziert.
EFFECTS = ("noise", "qrn", "qsb", "chirp", "ssb", "cw_qrm")

NOISE_LOOP_SECONDS = 20
PASSBAND_HZ = (300, 2700)
# Rauschpegel (Effektivwert) bei Regler auf 100 %; die Zeichen haben
# Spitzenwert morse.AMPLITUDE (0,5).
MAX_NOISE_RMS = 0.25

# Knackstörungen: mittlere Anzahl pro Sekunde, Länge und Stärke (ein
# Vielfaches von MAX_QRN_RMS bei Regler auf 100 %).
CRASH_RATE_PER_SECOND = 0.25
CRASH_SECONDS = (0.03, 0.2)
CRASH_GAIN = (2.0, 5.0)
MAX_QRN_RMS = 0.25

# QSB: Grundstärke der Stationen (Station 0 ist meist gut zu hören) und
# Fading-Periode/-Tiefe. Die Werte gelten für Regler auf 50 %; 100 % macht
# Stärkeunterschiede und Fading doppelt so tief (Fading höchstens 95 %).
STRENGTH_FIRST = (0.8, 1.0)
STRENGTH_OTHERS = (0.35, 1.0)
QSB_PERIOD_SECONDS = (6.0, 30.0)
QSB_DEPTH = (0.3, 0.85)

# Chirp: Anteil der Stationen mit „zwitscherndem“ Sender (mindestens eine),
# Frequenzablage beim Tasten (bei Regler auf 50 %; skaliert linear) und
# Zeitkonstante, mit der sie abklingt.
CHIRP_PROBABILITY = 0.4
CHIRP_DELTA_HZ = (15, 60)
CHIRP_TAU_SECONDS = (0.01, 0.04)

# SSB-Gebrabbel: Länge der Schleife, Verstimmung und Pegel (Effektivwert)
# bei Regler auf 100 %.
SSB_LOOP_SECONDS = 40
SSB_SHIFT_HZ = (200, 900)
MAX_SSB_RMS = 0.2
# Formanten (F1, F2, F3) einiger Vokale in Hz.
VOWEL_FORMANTS = (
    (730, 1090, 2440), (530, 1840, 2480), (270, 2290, 3010), (570, 840, 2410),
    (300, 870, 2240), (660, 1720, 2410), (490, 1350, 1690),
)

# CW-QRM: Abstand zur eigenen Frequenz und Tempo; bei Regler auf 100 % so
# laut wie die eigenen Stationen.
CW_QRM_OFFSET_HZ = (300, 500)
CW_QRM_WPM = (22, 32)
CW_QRM_PAUSE_SECONDS = (1.0, 2.5)  # dort, wo seine (nicht hörbaren) Anrufer senden

_noise_loop = None
_ssb_loop = None


def _passband_gain(f: np.ndarray) -> np.ndarray:
    """Empfängerfilter: Butterworth-artige Flanken (8. Ordnung) plus
    leichter Höhenabfall."""
    f = np.maximum(f, 1.0)  # Division durch null vermeiden
    lo, hi = PASSBAND_HZ
    return 1 / np.sqrt(1 + (lo / f) ** 8) / np.sqrt(1 + (f / hi) ** 8) * (1000 / np.maximum(f, 1000)) ** 0.3


def _normalized(x: np.ndarray) -> np.ndarray:
    rms = np.sqrt(np.mean(x ** 2))
    return (x / rms if rms else x).astype(np.float32)


def _shaped_noise_loop() -> np.ndarray:
    global _noise_loop
    if _noise_loop is None:
        n = NOISE_LOOP_SECONDS * SAMPLE_RATE
        spectrum = np.fft.rfft(np.random.default_rng().standard_normal(n))
        gain = _passband_gain(np.fft.rfftfreq(n, 1 / SAMPLE_RATE))
        gain[0] = 0.0
        _noise_loop = _normalized(np.fft.irfft(spectrum * gain, n))
    return _noise_loop


# --- SSB-Gebrabbel -------------------------------------------------------------
def _syllable(rng, length: int, pitch: float) -> np.ndarray:
    """Eine Silbe: stimmhaft (Sägezahn mit Tonhöhenverlauf durch
    Vokal-Formanten) oder stimmlos (gefiltertes Rauschen, wie „s“, „f“)."""
    f = np.fft.rfftfreq(length, 1 / SAMPLE_RATE)
    if rng.random() < 0.8:
        t = np.arange(length) / length
        contour = pitch * (1 + rng.uniform(-0.15, 0.15) * t)
        phase = np.cumsum(contour) / SAMPLE_RATE
        source = 2 * (phase % 1) - 1 + rng.standard_normal(length) * 0.05
        formants = VOWEL_FORMANTS[rng.integers(len(VOWEL_FORMANTS))]
        envelope = sum(
            gain / (1 + ((f - freq) / width) ** 2)
            for freq, gain, width in zip(formants, (1.0, 0.5, 0.25), (80, 100, 140))
        )
    else:
        source = rng.standard_normal(length)
        envelope = 0.5 / (1 + ((f - rng.uniform(2500, 5000)) / 1200) ** 2)
    segment = np.fft.irfft(np.fft.rfft(source) * envelope, length)
    window = np.sin(np.pi * np.arange(length) / length) ** 0.7
    return _normalized(segment * window) * rng.uniform(0.5, 1.0)


def _speech_like(rng, seconds: float) -> np.ndarray:
    """Zwei Sprecher (tiefe und höhere Stimme) wechseln sich ab, mit Wort-
    und Satzpausen."""
    total = int(seconds * SAMPLE_RATE)
    out = np.zeros(total + SAMPLE_RATE, dtype=np.float64)
    pitches = (rng.uniform(95, 130), rng.uniform(170, 220))
    speaker = int(rng.integers(2))
    pos = int(0.2 * SAMPLE_RATE)
    while pos < total:
        turn_end = pos + int(rng.uniform(3, 10) * SAMPLE_RATE)
        while pos < min(turn_end, total):
            for _ in range(int(rng.integers(1, 5))):  # Silben pro Wort
                length = int(rng.uniform(0.08, 0.25) * SAMPLE_RATE)
                segment = _syllable(rng, length, pitches[speaker] * rng.uniform(0.85, 1.2))
                end = min(pos + length, len(out))
                out[pos:end] += segment[:end - pos]
                pos += int(length * 0.85)
            pos += int(rng.uniform(0.04, 0.2) * SAMPLE_RATE)
            if rng.random() < 0.12:
                pos += int(rng.uniform(0.3, 0.7) * SAMPLE_RATE)  # Satzpause
        pos += int(rng.uniform(0.3, 1.5) * SAMPLE_RATE)  # Sprecherwechsel
        speaker = 1 - speaker
    return out[:total]


def _ssb_babble_loop() -> np.ndarray:
    """Sprachähnliches Signal, um einige hundert Hz verschoben (die SSB-Station
    ist nicht richtig eingestellt, klingt daher nach „Donald Duck“) und durch
    das Empfängerfilter begrenzt."""
    global _ssb_loop
    if _ssb_loop is None:
        rng = np.random.default_rng()
        speech = _speech_like(rng, SSB_LOOP_SECONDS)
        n = len(speech)
        spectrum = np.fft.rfft(speech)
        shift = int(round(rng.choice((-1, 1)) * rng.uniform(*SSB_SHIFT_HZ) * n / SAMPLE_RATE))
        shifted = np.zeros_like(spectrum)
        if shift >= 0:
            shifted[shift:] = spectrum[:len(spectrum) - shift]
        else:
            shifted[:shift] = spectrum[-shift:]
        shifted *= _passband_gain(np.fft.rfftfreq(n, 1 / SAMPLE_RATE))
        _ssb_loop = _normalized(np.fft.irfft(shifted, n))
    return _ssb_loop


# --- CW-QRM ----------------------------------------------------------------------
def _cw_qrm_loop(rng, freq: int) -> np.ndarray:
    """Nur die Run-Station eines Contest-Runs auf der Nachbarfrequenz; ihre
    Anrufer sind zu schwach und fallen in die Pausen."""
    offset = rng.uniform(*CW_QRM_OFFSET_HZ) * rng.choice((-1, 1))
    if not 250 <= freq + offset <= 1200:
        offset = -offset
    wpm = int(rng.integers(*CW_QRM_WPM))
    chirp = (rng.uniform(*CHIRP_DELTA_HZ), rng.uniform(*CHIRP_TAU_SECONDS)) if rng.random() < 0.3 else None
    kind = random.choice([k for k in qso_text.QSO_TYPES if k != qso_text.RAGCHEW])
    qso = qso_text.generate_qso(kind, qso_text.LENGTH_LONG)
    parts = [
        build_text(text, wpm, freq + offset, chirp=chirp) if station == 0
        else silence(rng.uniform(*CW_QRM_PAUSE_SECONDS))
        for station, text in qso.transmissions
    ]
    return np.concatenate(parts).astype(np.float32)


def soft_limit(x: np.ndarray, knee: float = 0.8) -> np.ndarray:
    """Unterhalb von `knee` unverändert, darüber weich gegen 1 begrenzt;
    starke Knackstörungen übersteuern so nicht hart."""
    mag = np.abs(x)
    over = mag > knee
    if not over.any():
        return x
    limited = knee + (1 - knee) * np.tanh((mag - knee) / (1 - knee))
    return np.where(over, np.sign(x) * limited, x)


class BandConditions:
    """Mischt die Bandbedingungen in die Audio-Blöcke eines QSOs. `enabled`
    und `levels` (je Schlüssel aus EFFECTS) dürfen während der Wiedergabe vom
    GUI-Thread aus geändert werden; danach dort prepare() aufrufen, damit
    die Schleifen nicht erst im Audio-Thread erzeugt werden."""

    def __init__(self, station_count: int):
        self.rng = np.random.default_rng()
        self.noise = _shaped_noise_loop()
        self.enabled = dict.fromkeys(EFFECTS, False)
        self.levels = dict.fromkeys(EFFECTS, 0.5)
        self.ssb = None
        self.cw_qrm = None
        self.strengths = [self.rng.uniform(*STRENGTH_FIRST)] + [
            self.rng.uniform(*STRENGTH_OTHERS) for _ in range(station_count - 1)
        ]
        self.qsb = [
            (1 / self.rng.uniform(*QSB_PERIOD_SECONDS), self.rng.uniform(*QSB_DEPTH), self.rng.uniform(0, 2 * np.pi))
            for _ in range(station_count)
        ]
        chirpy = [self.rng.random() < CHIRP_PROBABILITY for _ in range(station_count)]
        if not any(chirpy):
            chirpy[int(self.rng.integers(station_count))] = True
        self.chirps = [
            (self.rng.uniform(*CHIRP_DELTA_HZ) * self.rng.choice((-1, 1)), self.rng.uniform(*CHIRP_TAU_SECONDS))
            if c else None
            for c in chirpy
        ]
        self.rewind()

    def prepare(self, freq: int) -> None:
        """Erzeugt die Störsignale, die gerade eingeschaltet sind (einmalig)."""
        if self.enabled["ssb"] and self.ssb is None:
            self.ssb = _ssb_babble_loop()
        if self.enabled["cw_qrm"] and self.cw_qrm is None:
            self.cw_qrm = _cw_qrm_loop(self.rng, freq)

    def _on(self, effect: str) -> bool:
        return self.enabled[effect] and self.levels[effect] > 0

    @property
    def active(self) -> bool:
        return any(self._on(effect) for effect in EFFECTS if effect != "chirp")

    @property
    def has_background(self) -> bool:
        """Ist auch ohne die eigenen Stationen etwas zu hören?"""
        return any(self._on(effect) for effect in ("noise", "qrn", "ssb", "cw_qrm"))

    def chirp_for(self, station: int):
        """Chirp-Parameter für morse.build_samples, oder None."""
        chirp = self.chirps[station % len(self.chirps)]
        if chirp is None or not self._on("chirp"):
            return None
        delta, tau = chirp
        return delta * 2 * self.levels["chirp"], tau

    def rewind(self):
        """Für eine neue Wiedergabe (z. B. „Nochmal hören“): gleiche Stationen,
        Fading und Rauschen beginnen von vorn."""
        self.sample_pos = 0
        self.noise_pos = int(self.rng.integers(len(self.noise)))
        self.ssb_pos = int(self.rng.integers(SSB_LOOP_SECONDS * SAMPLE_RATE))
        self.cw_qrm_pos = 0
        self.crash = np.zeros(0, dtype=np.float32)  # Rest einer laufenden Knackstörung

    def process(self, block: np.ndarray, station: int) -> np.ndarray:
        """Ein Block einer einzelnen Station, mit QSB und Hintergrund."""
        return self.mix([(block, station)], len(block))

    def mix(self, sources, n: int) -> np.ndarray:
        """Mischt mehrere gleichzeitige Signale [(Block, Station), …] zu
        einem Block der Länge `n` (kürzere Blöcke werden mit Stille
        aufgefüllt) und legt Rauschen/QRM darunter. Station None steht für
        den eigenen Mithörton (kein QSB)."""
        out = np.zeros(n, dtype=np.float64)
        for block, station in sources:
            out[:len(block)] += block[:n] * self.station_gain(station, len(block[:n]))
        levels = self.levels
        if self._on("noise"):
            self.noise_pos, noise = _loop_slice(self.noise, self.noise_pos, n)
            out += noise * (MAX_NOISE_RMS * levels["noise"])
        if self._on("qrn"):
            out += self._crashes(n) * (MAX_QRN_RMS * levels["qrn"])
        ssb, cw_qrm = self.ssb, self.cw_qrm  # können parallel in prepare() entstehen
        if self._on("ssb") and ssb is not None:
            self.ssb_pos, part = _loop_slice(ssb, self.ssb_pos, n)
            out += part * (MAX_SSB_RMS * levels["ssb"])
        if self._on("cw_qrm") and cw_qrm is not None:
            self.cw_qrm_pos, part = _loop_slice(cw_qrm, self.cw_qrm_pos, n)
            out += part * levels["cw_qrm"]
        self.sample_pos += n
        return soft_limit(out).astype(np.float32)

    def station_gain(self, station, n: int):
        """Lautstärke einer Station über die nächsten `n` Samples (QSB);
        1, wenn QSB aus ist oder für den eigenen Mithörton (None)."""
        if station is None or not self._on("qsb"):
            return 1.0
        station %= len(self.qsb)
        scale = 2 * self.levels["qsb"]
        freq, depth, phase = self.qsb[station]
        t = (self.sample_pos + np.arange(n)) / SAMPLE_RATE
        fading = 1 - min(depth * scale, 0.95) * 0.5 * (1 + np.sin(2 * np.pi * freq * t + phase))
        strength = max(1 - (1 - self.strengths[station]) * scale, 0.05)
        return strength * fading

    def _crashes(self, n: int) -> np.ndarray:
        """Knackstörungen im nächsten Block (meist Stille)."""
        out = np.zeros(n, dtype=np.float32)
        if not len(self.crash) and self.rng.random() < CRASH_RATE_PER_SECOND * n / SAMPLE_RATE:
            self.crash = self._make_crash()
        if len(self.crash):
            part = self.crash[:n]
            out[:len(part)] = part
            self.crash = self.crash[n:]
        return out

    def _make_crash(self) -> np.ndarray:
        length = int(self.rng.uniform(*CRASH_SECONDS) * SAMPLE_RATE)
        start = int(self.rng.integers(len(self.noise) - length))
        # Schneller Anstieg, exponentielles Abklingen.
        envelope = np.exp(-np.arange(length) / (length / 4)) * np.minimum(np.arange(length) / 48, 1)
        return (self.noise[start:start + length] * envelope * self.rng.uniform(*CRASH_GAIN)).astype(np.float32)


def _loop_slice(loop: np.ndarray, pos: int, n: int):
    """Nächste `n` Samples einer Endlosschleife ab `pos`; (neue Position, Samples)."""
    idx = (pos + np.arange(n)) % len(loop)
    return int((pos + n) % len(loop)), loop[idx]