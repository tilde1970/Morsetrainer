"""Kurzwellen-Bandbedingungen für den QSO-Modus, alles einzeln zuschaltbar
und mit eigenem Pegel (0..1, siehe EFFECTS):

- Rauschen: Bandrauschen, wie es aus einem SSB-/CW-Empfänger kommt (auf
  ca. 300–2700 Hz begrenzt, leicht zu den Höhen abfallend).
- QRN: vereinzelte Knackstörungen, z. B. von Gewittern.
- QSB: jede Station schwankt langsam in der Lautstärke (Fading).
- Stärkeunterschiede: jede Station kommt unterschiedlich stark an,
  unabhängig vom QSB.
- Chirp: einige Stationen haben einen schlecht stabilisierten Sender, der
  beim Tasten kurz neben der Frequenz liegt („zwitschert“).
- SSB-QRM: eine verstimmte SSB-Station auf der Nachbarfrequenz.
  Synthetisch erzeugt (Sägezahn-Stimme durch wechselnde Vokal-Formanten,
  Silben, Wörter, Sprecherwechsel), also unverständlich, klingt aber nach
  Sprache.
- CW-QRM: ein Contest-Run auf der Nachbarfrequenz, weit daneben, nah dran
  oder fast auf der eigenen Frequenz (Zero-Beat); mit eigenem QSB.

Weitere Störungen (nicht Teil der Stufen):

- Gewitter: Knackstörungen in Schüben, wie ein Sommergewitter auf 80/160 m.
- AGC-Pumpen: nach einem starken Knacker regelt der Empfänger kurz
  herunter, das Signal bricht 100–300 ms ein.
- Flatterfading: schnelles Zittern (5–15 Hz), wie bei Aurora oder auf dem
  Polarweg.
- Träger: jemand stimmt nahe der Frequenz ab, ein Dauerton kommt und geht.
- Schaltnetzteil: rauer Brummteppich im Takt der gleichgerichteten
  Netzspannung (100 Hz), dazu ein wandernder, brummender Pfeifton.
- PLC (Powerline): breitbandiges Rauschen in Datenpaketen, in Pausen nur
  ein kurzes Leuchtfeuer im festen Takt.
- Weidezaun: ein harter Ticker etwa einmal pro Sekunde, sehr regelmäßig.
- Tastklicks: der Nachbar-Run (CW-QRM) tastet hart; seine Klicks an jeder
  Flanke sind breitbandig und gehen auch durch ein schmales Filter, selbst
  wenn sein Ton draußen bleibt.

Dazu ein wählbares CW-Filter (2,4 kHz = nur das SSB-Filter, 500 Hz, 250 Hz) um die
eigene Tonhöhe: Signale, Rauschen und QRM laufen hindurch, der eigene
Mithörton nicht.

Rauschen und SSB-QRM werden einmal als Schleife per FFT geformt. Weil
die FFT-Synthese periodisch ist, geht das Ende nahtlos in den Anfang über;
so kostet das laufende Mischen fast nichts."""
import copy
import functools
import math
import random
import time

import numpy as np

from morsetrainer.core.morse import AMPLITUDE, SAMPLE_RATE, build_text, silence

# Schlüssel der Störungen; BandConditions.enabled/levels sind danach
# indiziert.
EFFECTS = ("noise", "qrn", "qsb", "chirp", "ssb", "cw_qrm", "strength", "storm", "agc", "flutter", "carrier",
           "smps", "plc", "fence", "clicks")

NOISE_LOOP_SECONDS = 20
PASSBAND_HZ = (300, 2700)
# Rauschen als Rauschabstand S/N in dB, gemessen in der Bandbreite des
# Empfängerfilters (rund 2,4 kHz) gegenüber dem ungeschwächten Signal
# (Dauerstrich, Effektivwert SIGNAL_RMS): Regler 0 % … 100 % gleichmäßig
# über SNR_DB_RANGE. Das Ohr hört CW wie durch ein Filter von etwa 50 Hz,
# dort ist der Abstand rund EAR_GAIN_DB größer.
SNR_DB_RANGE = (20.0, -10.0)
SIGNAL_RMS = AMPLITUDE / math.sqrt(2)
EAR_GAIN_DB = 10 * math.log10(2400 / 50)
# Lauter als das wird das Rauschen nicht; stattdessen wird alles Übrige
# leiser, wie bei der Regelung (AGC) eines Empfängers. So übersteuert auch
# ein Signal unter dem Rauschen nichts.
NOISE_RMS_CAP = 0.2

# Knackstörungen: mittlere Anzahl pro Sekunde, Länge und Stärke (ein
# Vielfaches von MAX_QRN_RMS bei Regler auf 100 %).
CRASH_RATE_PER_SECOND = 0.25
CRASH_SECONDS = (0.03, 0.2)
CRASH_GAIN = (2.0, 5.0)
MAX_QRN_RMS = 0.25

# Stärkeunterschiede: Grundstärke der Stationen (Station 0 ist gut zu
# hören; die Werte gelten für Regler auf 50 %, 100 % macht die Unterschiede
# doppelt so groß). QSB: Fading. Die Tiefe des Fadings folgt dem Regler (100 % = QSB_MAX_DEPTH,
# rund −26 dB im tiefsten Loch) mit wenig Streuung je Station, damit die
# Stufe und nicht der Zufall die Schwierigkeit bestimmt. Zwei überlagerte
# Schwingungen ungleicher Periode machen den Verlauf unregelmäßig.
STRENGTH_FIRST = (0.9, 1.0)
STRENGTH_OTHERS = (0.35, 1.0)
QSB_PERIOD_SECONDS = (6.0, 30.0)
QSB_SECOND_RATIO = (2.2, 3.4)   # zweite Schwingung so viel schneller
QSB_SECOND_WEIGHT = 0.5
QSB_MAX_DEPTH = 0.95
QSB_DEPTH_SPREAD = (0.85, 1.15)

# Chirp: Anteil der Stationen mit „zwitscherndem“ Sender (mindestens eine),
# Frequenzablage beim Tasten (bei Regler auf 50 %; skaliert linear) und
# Zeitkonstante, mit der sie abklingt.
CHIRP_PROBABILITY = 0.4
CHIRP_DELTA_HZ = (15, 60)
CHIRP_TAU_SECONDS = (0.01, 0.04)

# SSB-QRM: Länge der Schleife, Verstimmung und Pegel (Effektivwert)
# bei Regler auf 100 %.
SSB_LOOP_SECONDS = 40
SSB_SHIFT_HZ = (200, 900)
MAX_SSB_RMS = 0.2
# Formanten (F1, F2, F3) einiger Vokale in Hz.
VOWEL_FORMANTS = (
    (730, 1090, 2440), (530, 1840, 2480), (270, 2290, 3010), (570, 840, 2410),
    (300, 870, 2240), (660, 1720, 2410), (490, 1350, 1690),
)

# CW-QRM: Abstand zur eigenen Frequenz (wählbar) und Tempo; bei Regler auf
# 100 % so laut wie die eigenen Stationen. „weit“ nimmt ein schmales Filter
# weg, „nah“ und „Zero-Beat“ nicht – dann hilft nur selektives Hören.
QRM_OFFSETS = {"far": (300, 500), "near": (50, 200), "zero": (0, 15)}
DEFAULT_QRM_OFFSET = "far"
CW_QRM_WPM = (22, 32)
CW_QRM_PAUSE_SECONDS = (1.0, 2.5)  # dort, wo seine (nicht hörbaren) Anrufer senden

# Gewitter: Pausen zwischen den Schüben, ihre Länge und wie dicht es darin
# knackt (Knacker pro Sekunde bei Regler auf 100 %).
STORM_PAUSE_SECONDS = (4.0, 15.0)
STORM_BURST_SECONDS = (1.0, 4.0)
STORM_RATE_PER_SECOND = 6.0
# AGC-Pumpen: ab diesem Spitzenwert eines Knackers regelt der Empfänger
# herunter, höchstens um AGC_PUMP_MAX_DEPTH (Regler 100 %), und erholt sich
# mit der Zeitkonstante AGC_PUMP_RELEASE_SECONDS (nach rund 0,3 s fast ganz).
AGC_PUMP_THRESHOLD = 0.15
AGC_PUMP_MAX_DEPTH = 0.9
AGC_PUMP_RELEASE_SECONDS = 0.1
# Flatterfading: drei überlagerte Schwingungen in diesem Bereich, Tiefe bei
# Regler 100 %.
FLUTTER_HZ = (5.0, 15.0)
FLUTTER_MAX_DEPTH = 0.8
# Träger: Abstand zur eigenen Tonhöhe, langsames Wandern, an und aus.
CARRIER_OFFSET_HZ = (30, 250)
CARRIER_DRIFT_HZ = 15
CARRIER_ON_SECONDS = (3.0, 10.0)
CARRIER_OFF_SECONDS = (5.0, 20.0)
CARRIER_RAMP_SECONDS = 0.05
MAX_CARRIER_AMPLITUDE = AMPLITUDE * 0.8
# Schaltnetzteil: Länge der Schleife, Netzfrequenz, Pfeifton (Bereich,
# Wandern) und Pegel (Effektivwert) bei Regler 100 %.
SMPS_LOOP_SECONDS = 10
MAINS_HZ = 50
SMPS_WHISTLE_HZ = (350, 1100)
SMPS_WHISTLE_DRIFT_HZ = 40
MAX_SMPS_RMS = 0.15
# PLC: Datenverkehr in Schüben aus kurzen Rahmen, dazwischen nur das
# Leuchtfeuer; Pegel bei Regler 100 %.
PLC_LOOP_SECONDS = 12
PLC_BUSY_SECONDS = (0.4, 2.5)
PLC_IDLE_SECONDS = (0.3, 1.5)
PLC_FRAME_SECONDS = (0.002, 0.012)
PLC_FRAME_GAP_SECONDS = (0.0003, 0.002)
PLC_BEACON_PERIOD_SECONDS = 0.04
PLC_BEACON_SECONDS = 0.002
MAX_PLC_RMS = 0.2
# Weidezaun: Abstand der Ticker (je Band fest, kaum Schwankung), Länge und
# Pegel bei Regler 100 %.
FENCE_PERIOD_SECONDS = (1.0, 1.5)
FENCE_JITTER_SECONDS = 0.01
FENCE_TICK_SECONDS = 0.012
MAX_FENCE_RMS = 0.3
# Tastklicks: Länge eines Klicks und Spitzenpegel bei Regler 100 % (vor dem
# Filter; ein schmales Filter lässt davon nur einen Teil durch).
CLICK_SECONDS = 0.004
MAX_CLICK_AMPLITUDE = AMPLITUDE * 1.5

# CW-Filter: Bandbreite (-3 dB) um die eigene Tonhöhe. 2400 ist das
# SSB-Filter, das Rauschen und SSB-QRM ohnehin schon formt; dann wird
# nichts zusätzlich gefiltert. Steile Flanken (Butterworth-Ordnung) und
# minimale Phase: kausal wie ein echtes Filter, das schmale klingelt leicht.
FILTER_WIDTHS = (2400, 500, 250)
DEFAULT_FILTER = 2400
FILTER_ORDER = 4
FILTER_IR_SECONDS = 0.06
FILTER_FFT_SIZE = 2 ** 15

# Station für die Sprachansage im Mischer (widgets/announcer.py): wie der
# Mithörton ohne Filter, QSB und AGC, aber eigens abbrechbar.
VOICE = "voice"

_noise_loop = None
_flat_noise_loop = None
_ssb_loop = None
_smps_loop = None
_plc_loop = None


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


def _noise_bandwidth(gain: np.ndarray, f: np.ndarray) -> float:
    """Rauschbandbreite in Hz einer Verstärkung über den Frequenzen `f`."""
    return float(np.sum(gain ** 2) * (f[1] - f[0]))


def _filter_noise_loop() -> np.ndarray:
    """Rauschen für das schmale CW-Filter: flach statt durch die Flanken des
    SSB-Filters, mit derselben Dichte wie _shaped_noise_loop in der Mitte
    des Durchlassbereichs. Wie bei einem Gerät mit ZF-CW-Filter liegt das
    Filter so um die eigene Tonhöhe, ohne an die untere Flanke bei 300 Hz zu
    stoßen: Es nimmt bei jeder Tonhöhe gleich viel Rauschen weg."""
    global _flat_noise_loop
    if _flat_noise_loop is None:
        n = NOISE_LOOP_SECONDS * SAMPLE_RATE
        f = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
        spectrum = np.fft.rfft(np.random.default_rng().standard_normal(n))
        spectrum[0] = 0.0
        flat = _normalized(np.fft.irfft(spectrum, n))
        scale = np.sqrt(_noise_bandwidth(np.ones_like(f), f) / _noise_bandwidth(_passband_gain(f), f))
        _flat_noise_loop = (flat * scale).astype(np.float32)
    return _flat_noise_loop


# --- SSB-QRM -------------------------------------------------------------
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
def _cw_qrm_loop(rng, freq: int, offset_range=QRM_OFFSETS[DEFAULT_QRM_OFFSET]) -> np.ndarray:
    """Nur die Run-Station eines Contest-Runs auf der Nachbarfrequenz; ihre
    Anrufer sind zu schwach und fallen in die Pausen."""
    # Erst hier importiert: qso_text lädt die Rufzeichenliste aus den
    # Modi, und die Modi importieren dieses Modul.
    from morsetrainer.core import qso_text
    offset = rng.uniform(*offset_range) * rng.choice((-1, 1))
    if not 250 <= freq + offset <= 1200:
        offset = -offset
    wpm = int(rng.integers(*CW_QRM_WPM))
    chirp = (rng.uniform(*CHIRP_DELTA_HZ), rng.uniform(*CHIRP_TAU_SECONDS)) if rng.random() < 0.3 else None
    # qso_text würfelt mit dem Modul random: für den Text kurz aus `rng`
    # gesät, damit gleicher Startwert gleiches QRM ergibt (Netzwerk).
    state = random.getstate()
    random.seed(int(rng.integers(2 ** 63)))
    try:
        kind = random.choice([k for k in qso_text.QSO_TYPES if k != qso_text.RAGCHEW])
        qso = qso_text.generate_qso(kind, qso_text.LENGTH_LONG)
    finally:
        random.setstate(state)
    parts = [
        build_text(text, wpm, freq + offset, chirp=chirp) if station == 0
        else silence(rng.uniform(*CW_QRM_PAUSE_SECONDS))
        for station, text in qso.transmissions
    ]
    return np.concatenate(parts).astype(np.float32)


def _key_clicks(loop: np.ndarray, rng) -> np.ndarray:
    """Tastklicks zum CW-QRM `loop`: an jeder Flanke seiner Tastung ein
    kurzer, breitbandiger Klick (Spitze 1); gleich lang wie `loop`, damit
    beide mit derselben Position laufen."""
    window = int(0.005 * SAMPLE_RATE)
    clicks = np.zeros(len(loop), dtype=np.float32)
    if len(loop) <= window:
        return clicks
    total = np.cumsum(np.abs(loop), dtype=np.float64)
    envelope = (total[window:] - total[:-window]) / window
    if envelope.max() <= 0:
        return clicks
    keyed = (envelope > 0.3 * envelope.max()).astype(np.int8)
    edges = np.flatnonzero(np.diff(keyed)) + window // 2
    noise = _shaped_noise_loop()
    length = int(CLICK_SECONDS * SAMPLE_RATE)
    decay = np.exp(-np.arange(length) / (length / 5))
    for edge in edges:
        if edge + length > len(loop):
            break
        start = int(rng.integers(len(noise) - length))
        click = noise[start:start + length] * decay
        clicks[edge:edge + length] += click / np.max(np.abs(click)) * rng.uniform(0.7, 1.0)
    return clicks


# --- Menschengemachte Störungen ---------------------------------------------------
def _in_passband(x: np.ndarray) -> np.ndarray:
    """`x` durch das Empfängerfilter, auf Effektivwert 1 (periodisch, also
    als nahtlose Schleife brauchbar)."""
    n = len(x)
    spectrum = np.fft.rfft(x) * _passband_gain(np.fft.rfftfreq(n, 1 / SAMPLE_RATE))
    spectrum[0] = 0.0
    return _normalized(np.fft.irfft(spectrum, n))


def _smps_buzz_loop() -> np.ndarray:
    """Schaltnetzteil: Rauschen, das im Takt der gleichgerichteten
    Netzspannung pulst (rauer 100-Hz-Brumm), dazu ein Pfeifton, der langsam
    wandert und mitbrummt. Wanderung und Ton gehen in der Schleife ganz auf,
    damit sie nahtlos weiterläuft."""
    global _smps_loop
    if _smps_loop is None:
        rng = np.random.default_rng()
        n = SMPS_LOOP_SECONDS * SAMPLE_RATE
        t = np.arange(n) / SAMPLE_RATE
        pulse = np.abs(np.sin(2 * np.pi * MAINS_HZ * t)) ** 8
        carpet = _normalized(rng.standard_normal(n) * pulse)
        f0 = round(rng.uniform(*SMPS_WHISTLE_HZ) * SMPS_LOOP_SECONDS) / SMPS_LOOP_SECONDS
        drift = SMPS_WHISTLE_DRIFT_HZ * SMPS_LOOP_SECONDS / (2 * np.pi) * (
            1 - np.cos(2 * np.pi * t / SMPS_LOOP_SECONDS))
        whistle = np.sin(2 * np.pi * (f0 * t + drift)) * (0.4 + 0.6 * pulse ** 0.25)
        _smps_loop = _in_passband(0.8 * carpet + 1.4 * whistle)
    return _smps_loop


def _plc_data_loop() -> np.ndarray:
    """PLC: breitbandiges Rauschen, an- und ausgetastet wie Datenpakete –
    im Wechsel Verkehr (dicht gepackte Rahmen) und Ruhe (nur das
    Leuchtfeuer im festen Takt)."""
    global _plc_loop
    if _plc_loop is None:
        rng = np.random.default_rng()
        n = PLC_LOOP_SECONDS * SAMPLE_RATE
        gate = np.zeros(n)
        pos, busy = 0, True
        period, beacon = int(PLC_BEACON_PERIOD_SECONDS * SAMPLE_RATE), int(PLC_BEACON_SECONDS * SAMPLE_RATE)
        while pos < n:
            end = min(pos + int(rng.uniform(*(PLC_BUSY_SECONDS if busy else PLC_IDLE_SECONDS)) * SAMPLE_RATE), n)
            if busy:
                p = pos
                while p < end:
                    frame = int(rng.uniform(*PLC_FRAME_SECONDS) * SAMPLE_RATE)
                    gate[p:min(p + frame, end)] = 1.0
                    p += frame + int(rng.uniform(*PLC_FRAME_GAP_SECONDS) * SAMPLE_RATE)
            else:
                for p in range(pos, end, period):
                    gate[p:min(p + beacon, end)] = 1.0
            pos, busy = end, not busy
        edge = int(0.0002 * SAMPLE_RATE)  # weiche Flanken statt harter Klicks
        gate = np.convolve(gate, np.ones(edge) / edge, "same")
        _plc_loop = _in_passband(rng.standard_normal(n) * gate)
    return _plc_loop


# --- CW-Filter -------------------------------------------------------------------
def filter_response(width: int, freq: float, f: np.ndarray) -> np.ndarray:
    """Betrag des Filters bei den Frequenzen `f`: Butterworth-Flanken,
    symmetrisch um `freq`."""
    return 1 / np.sqrt(1 + ((f - freq) / (width / 2)) ** (2 * FILTER_ORDER))


def filter_ir(width: int, freq: float) -> np.ndarray:
    """Impulsantwort des CW-Filters (minimalphasig über das Cepstrum),
    auf FILTER_IR_SECONDS gekürzt und bei `freq` auf Verstärkung 1."""
    n = FILTER_FFT_SIZE
    f = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    log_mag = np.log(np.maximum(filter_response(width, freq, f), 1e-5))
    cepstrum = np.fft.irfft(log_mag, n)
    folded = np.zeros(n)
    folded[0], folded[n // 2] = cepstrum[0], cepstrum[n // 2]
    folded[1:n // 2] = 2 * cepstrum[1:n // 2]
    h = np.fft.irfft(np.exp(np.fft.rfft(folded)), n)[:int(FILTER_IR_SECONDS * SAMPLE_RATE)]
    fade = len(h) // 5
    h[-fade:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fade))
    t = np.arange(len(h)) / SAMPLE_RATE
    return h / abs(np.sum(h * np.exp(-2j * np.pi * freq * t)))


@functools.lru_cache(maxsize=None)
def filter_noise_db(width: int) -> float:
    """So viel weniger Bandrauschen lässt das Filter durch als das
    SSB-Filter allein (2,4 kHz); unabhängig von der Tonhöhe, weil das
    Filter mit ihr wandert (siehe _filter_noise_loop)."""
    if width == DEFAULT_FILTER:
        return 0.0
    f = np.fft.rfftfreq(FILTER_FFT_SIZE, 1 / SAMPLE_RATE)
    narrow = filter_response(width, f[-1] / 2, f)
    return float(10 * np.log10(_noise_bandwidth(_passband_gain(f), f) / _noise_bandwidth(narrow, f)))


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
    die Schleifen nicht erst im Audio-Thread erzeugt werden.
    `background_gain` skaliert alle Störgeräusche gemeinsam (nicht die
    Stationen selbst), z. B. um sie gegenüber den Zeichen leiser zu machen."""

    def __init__(self, station_count: int, seed=None):
        """`seed`: gleicher Wert, gleiche Stationen und gleiches Fading (im
        Netzwerk hören so alle Teilnehmer dieselben Bedingungen)."""
        self.rng = np.random.default_rng(seed)
        self.noise = _shaped_noise_loop()
        self.enabled = dict.fromkeys(EFFECTS, False)
        self.levels = dict.fromkeys(EFFECTS, 0.5)
        self.background_gain = 1.0
        self.filter_width = DEFAULT_FILTER
        self.qrm_offset = DEFAULT_QRM_OFFSET
        self.ssb = None
        self.smps = None
        self.plc = None
        self.cw_qrm = None
        self.key_clicks = None  # Tastklicks zu cw_qrm, gleich lang
        self.cw_qrm_offset = None  # QRM_OFFSETS-Schlüssel, mit dem cw_qrm entstand
        self.filter = None  # ((Breite, Tonhöhe), Impulsantwort) oder None
        self._filter_spectra = {}
        self.strengths = [self.rng.uniform(*STRENGTH_FIRST)] + [
            self.rng.uniform(*STRENGTH_OTHERS) for _ in range(station_count - 1)
        ]
        self.qsb = []  # je Station (Frequenz, Phase, Frequenz 2, Phase 2, Streuung der Tiefe)
        for _ in range(station_count):
            freq = 1 / self.rng.uniform(*QSB_PERIOD_SECONDS)
            self.qsb.append((freq, self.rng.uniform(0, 2 * np.pi), freq * self.rng.uniform(*QSB_SECOND_RATIO),
                             self.rng.uniform(0, 2 * np.pi), self.rng.uniform(*QSB_DEPTH_SPREAD)))
        chirpy = [self.rng.random() < CHIRP_PROBABILITY for _ in range(station_count)]
        if not any(chirpy):
            chirpy[int(self.rng.integers(station_count))] = True
        self.chirps = [
            (self.rng.uniform(*CHIRP_DELTA_HZ) * self.rng.choice((-1, 1)), self.rng.uniform(*CHIRP_TAU_SECONDS))
            if c else None
            for c in chirpy
        ]
        # Eigenes Fading des CW-QRM (wie eine weitere Station).
        freq = 1 / self.rng.uniform(*QSB_PERIOD_SECONDS)
        self.qrm_qsb = (freq, self.rng.uniform(0, 2 * np.pi), freq * self.rng.uniform(*QSB_SECOND_RATIO),
                        self.rng.uniform(0, 2 * np.pi), self.rng.uniform(*QSB_DEPTH_SPREAD))
        # Flatterfading je Station (letzter Eintrag: CW-QRM): drei Schwingungen.
        self.flutter = [[(self.rng.uniform(*FLUTTER_HZ), self.rng.uniform(0, 2 * np.pi)) for _ in range(3)]
                        for _ in range(station_count + 1)]
        self.carrier_offset = self.rng.uniform(*CARRIER_OFFSET_HZ) * self.rng.choice((-1, 1))
        self.carrier_drift_hz = 1 / self.rng.uniform(8.0, 20.0)  # so schnell wandert er hin und her
        # Das CW-QRM würfelt aus einem eigenen Strom: Wie viele Zufallszahlen
        # sein Text braucht, verschiebt sonst Gewitter, Träger und Knacker
        # (im Netzwerk hörte dann jeder Teilnehmer andere).
        self.qrm_seed = int(self.rng.integers(2 ** 63))
        self.qrm_builds = 0
        # Ebenso Weidezaun und künftige Störungen: Ihr Strom hängt nur am
        # Startwert und verschiebt die übrigen nicht (ältere Teilnehmer im
        # Netzwerk hören dann noch dieselben Gewitter und Träger).
        self.extra_rng = np.random.default_rng([self.qrm_seed, 1 << 40])
        self.fence_period = self.extra_rng.uniform(*FENCE_PERIOD_SECONDS)
        self.freq = 600
        self.rewind()

    def prepare(self, freq: int) -> None:
        """Erzeugt die Störsignale, die gerade eingeschaltet sind (einmalig,
        neu bei anderem QRM-Abstand), und das CW-Filter um `freq`."""
        self.freq = freq
        if self.enabled["ssb"] and self.ssb is None:
            self.ssb = _ssb_babble_loop()
        if self.enabled["smps"] and self.smps is None:
            self.smps = _smps_buzz_loop()
        if self.enabled["plc"] and self.plc is None:
            self.plc = _plc_data_loop()
        neighbour = self.enabled["cw_qrm"] or self.enabled["clicks"]
        if neighbour and (self.cw_qrm is None or self.cw_qrm_offset != self.qrm_offset):
            offset = self.qrm_offset
            qrm_rng = np.random.default_rng([self.qrm_seed, self.qrm_builds])
            self.qrm_builds += 1
            loop = _cw_qrm_loop(qrm_rng, freq, QRM_OFFSETS[offset])
            # Erst die Klicks, dann die Schleife: mix() nimmt beide nur, wenn
            # sie zusammenpassen.
            self.key_clicks = _key_clicks(loop, qrm_rng)
            self.cw_qrm = loop
            self.cw_qrm_pos %= len(self.cw_qrm)
            self.cw_qrm_offset = offset
        if self.filter_width == DEFAULT_FILTER:
            self.filter = None
            self.noise = _shaped_noise_loop()
        else:
            self.noise = _filter_noise_loop()
            if self.filter is None or self.filter[0] != (self.filter_width, freq):
                self.filter = ((self.filter_width, freq), filter_ir(self.filter_width, freq).astype(np.float64))

    def _on(self, effect: str) -> bool:
        return self.enabled[effect] and self.levels[effect] > 0

    @property
    def active(self) -> bool:
        """Ist irgendeine Störung hörbar eingeschaltet? Chirp zählt nicht, er
        verändert nur die Stationen selbst."""
        return any(self._on(effect) for effect in EFFECTS if effect != "chirp")

    @property
    def has_background(self) -> bool:
        """Ist auch ohne die eigenen Stationen etwas zu hören?"""
        return any(self._on(effect) for effect in ("noise", "qrn", "ssb", "cw_qrm", "storm", "carrier", "smps",
                                                    "plc", "fence", "clicks"))

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
        self.smps_pos = int(self.extra_rng.integers(SMPS_LOOP_SECONDS * SAMPLE_RATE))
        self.plc_pos = int(self.extra_rng.integers(PLC_LOOP_SECONDS * SAMPLE_RATE))
        self.fence_next = self.sample_pos + int(self.extra_rng.uniform(0, self.fence_period) * SAMPLE_RATE)
        self.fence_buf = np.zeros(0, dtype=np.float32)  # Rest eines laufenden Tickers
        self.crash = np.zeros(0, dtype=np.float32)  # Rest einer laufenden Knackstörung
        self.storm_crash = np.zeros(0, dtype=np.float32)
        self.storm_start = self.sample_pos + int(self.rng.uniform(*STORM_PAUSE_SECONDS) * SAMPLE_RATE)
        self.storm_end = self.storm_start + int(self.rng.uniform(*STORM_BURST_SECONDS) * SAMPLE_RATE)
        self.pump = 0.0  # wie weit die AGC gerade heruntergeregelt hat (0 … 1)
        self.carrier_phase = 0.0
        self.carrier_on = False
        self.carrier_edge = self.sample_pos - SAMPLE_RATE  # letzter Wechsel an/aus (für die Flanke)
        self.carrier_switch = self.sample_pos + int(self.rng.uniform(*CARRIER_OFF_SECONDS) * SAMPLE_RATE / 3)
        self.filter_tail = np.zeros(0)  # Nachklingen des Filters in den nächsten Block
        self.clock = None  # time.time() zu sample_pos 0, ab dem ersten catch_up()

    def catch_up(self) -> None:
        """Für Wiedergaben mit Pausen dazwischen (Abfragemodi): Fading,
        Rauschen und Nachbar-QRM laufen in der Zwischenzeit weiter wie auf dem
        Band, statt bei jeder Sequenz an derselben Stelle zu beginnen. Schon
        berechnete, noch nicht gehörte Samples zählen als Vorlauf."""
        now = time.time()
        if self.clock is None:
            self.clock = now - self.sample_pos / SAMPLE_RATE
        gap = int((now - self.clock) * SAMPLE_RATE) - self.sample_pos
        if gap <= 0:
            return
        self.sample_pos += gap
        self.noise_pos = (self.noise_pos + gap) % len(self.noise)
        self.ssb_pos = (self.ssb_pos + gap) % (SSB_LOOP_SECONDS * SAMPLE_RATE)
        self.smps_pos = (self.smps_pos + gap) % (SMPS_LOOP_SECONDS * SAMPLE_RATE)
        self.plc_pos = (self.plc_pos + gap) % (PLC_LOOP_SECONDS * SAMPLE_RATE)
        self.fence_buf = np.zeros(0, dtype=np.float32)
        if self.cw_qrm is not None:
            self.cw_qrm_pos = (self.cw_qrm_pos + gap) % len(self.cw_qrm)
        self.crash = np.zeros(0, dtype=np.float32)
        self.storm_crash = np.zeros(0, dtype=np.float32)
        self.pump = 0.0
        self.filter_tail = np.zeros(0)

    def fork(self) -> "BandConditions":
        """Kopie, die von hier an eigenständig weiterläuft (eigene
        Positionen, laufende Knacker und Ticker, eigener Zufall), etwa für das
        Bandgeräusch in der Antwortpause in einem anderen Thread. Schalter und
        Pegel teilt sie mit dem Original; Änderungen daran wirken auf beide."""
        twin = copy.copy(self)
        twin.rng = np.random.default_rng(self.rng.integers(2 ** 63))
        twin.extra_rng = np.random.default_rng(self.rng.integers(2 ** 63))
        twin.crash = self.crash.copy()
        twin.storm_crash = self.storm_crash.copy()
        twin.fence_buf = self.fence_buf.copy()
        twin.filter_tail = np.zeros(0)
        twin._filter_spectra = {}
        return twin

    def process(self, block: np.ndarray, station: int) -> np.ndarray:
        """Ein Block einer einzelnen Station, mit QSB und Hintergrund."""
        return self.mix([(block, station)], len(block))

    def mix(self, sources, n: int) -> np.ndarray:
        """Mischt mehrere gleichzeitige Signale [(Block, Station), …] zu
        einem Block der Länge `n` (kürzere Blöcke werden mit Stille
        aufgefüllt) und legt Rauschen/QRM darunter, alles durch das
        CW-Filter. Station None steht für den eigenen Mithörton (kein QSB,
        keine AGC, nicht gefiltert)."""
        noise_rms, agc = self.noise_and_agc()
        out = np.zeros(n, dtype=np.float64)
        sidetone = np.zeros(n, dtype=np.float64)
        for block, station in sources:
            block = block[:n]
            if station is None or station == VOICE:
                sidetone[:len(block)] += block
            else:
                out[:len(block)] += block * (self.station_gain(station, len(block)) * agc)
        levels = self.levels
        if self._on("noise"):
            self.noise_pos, noise = _loop_slice(self.noise, self.noise_pos, n)
            out += noise * noise_rms
        background = np.zeros(n, dtype=np.float64)
        if self._on("qrn"):
            background += self._crashes(n) * (MAX_QRN_RMS * levels["qrn"])
        if self._on("storm"):
            background += self._storm(n) * (MAX_QRN_RMS * levels["storm"])
        if self._on("fence"):
            background += self._fence(n) * (MAX_FENCE_RMS * levels["fence"])
        crashes = np.abs(background) if self._on("agc") else None  # Knacker, auf die die AGC reagiert
        # Können parallel in prepare() entstehen.
        ssb, smps, plc, cw_qrm, clicks = self.ssb, self.smps, self.plc, self.cw_qrm, self.key_clicks
        if self._on("ssb") and ssb is not None:
            self.ssb_pos, part = _loop_slice(ssb, self.ssb_pos, n)
            background += part * (MAX_SSB_RMS * levels["ssb"])
        if self._on("smps") and smps is not None:
            self.smps_pos, part = _loop_slice(smps, self.smps_pos, n)
            background += part * (MAX_SMPS_RMS * levels["smps"])
        if self._on("plc") and plc is not None:
            self.plc_pos, part = _loop_slice(plc, self.plc_pos, n)
            background += part * (MAX_PLC_RMS * levels["plc"])
        if (self._on("cw_qrm") or self._on("clicks")) and cw_qrm is not None:
            pos = self.cw_qrm_pos % len(cw_qrm)
            self.cw_qrm_pos, part = _loop_slice(cw_qrm, pos, n)
            fading = self._fading(self.qrm_qsb, n) if self._on("qsb") else 1.0
            neighbour = fading * self._flutter(len(self.flutter) - 1, n)
            if self._on("cw_qrm"):
                background += part * neighbour * levels["cw_qrm"]
            if self._on("clicks") and clicks is not None and len(clicks) == len(cw_qrm):
                background += _loop_slice(clicks, pos, n)[1] * neighbour * (MAX_CLICK_AMPLITUDE * levels["clicks"])
        if self._on("carrier"):
            background += self._carrier(n) * (MAX_CARRIER_AMPLITUDE * levels["carrier"])
        out += background * (self.background_gain * agc)
        if crashes is not None:
            out *= self._pump(crashes * self.background_gain, n)
        out = self._filtered(out)
        self.sample_pos += n
        return soft_limit(out + sidetone).astype(np.float32)

    def _filtered(self, x: np.ndarray) -> np.ndarray:
        """x durch das CW-Filter (Overlap-Add per FFT; das Nachklingen geht in
        den nächsten Block). Ohne schmales Filter unverändert."""
        current = self.filter  # kann parallel in prepare() wechseln
        if current is None:
            return x
        h = current[1]
        n, tail_len = len(x), len(h) - 1
        size = 1 << (n + tail_len - 1).bit_length()
        key = (current[0], size)
        spectrum = self._filter_spectra.get(key)
        if spectrum is None:
            spectrum = self._filter_spectra[key] = np.fft.rfft(h, size)
        y = np.fft.irfft(np.fft.rfft(x, size) * spectrum, size)[:n + tail_len]
        tail = self.filter_tail
        if len(tail) == tail_len:
            y[:tail_len] += tail
        self.filter_tail = y[n:]
        return y[:n]

    def noise_and_agc(self):
        """(Effektivwert des Rauschens, Faktor für alles Übrige). Der
        Rauschabstand folgt Regler und Lautstärke (noise_snr_db); wäre das
        Rauschen lauter als NOISE_RMS_CAP, werden stattdessen die Signale
        leiser (AGC)."""
        if not self._on("noise") or self.background_gain <= 0:
            return 0.0, 1.0
        rms = SIGNAL_RMS * 10 ** (-noise_snr_db(self.levels["noise"], self.background_gain) / 20)
        if rms <= NOISE_RMS_CAP:
            return rms, 1.0
        return NOISE_RMS_CAP, NOISE_RMS_CAP / rms

    def station_gain(self, station, n: int):
        """Lautstärke einer Station über die nächsten `n` Samples
        (Stärkeunterschiede und QSB); 1, wenn beides aus ist oder für den
        eigenen Mithörton (None)."""
        if station is None:
            return 1.0
        station %= len(self.qsb)
        gain = 1.0
        if self._on("strength"):
            gain = max(1 - (1 - self.strengths[station]) * 2 * self.levels["strength"], 0.05)
        if self._on("qsb"):
            gain = gain * self._fading(self.qsb[station], n)
        if self._on("flutter"):
            gain = gain * self._flutter(station, n)
        return gain

    def _flutter(self, index: int, n: int):
        """Flatterfading (0 … 1) über die nächsten `n` Samples; 1 ohne."""
        if not self._on("flutter"):
            return 1.0
        t = (self.sample_pos + np.arange(n)) / SAMPLE_RATE
        wave = sum(np.sin(2 * np.pi * freq * t + phase) for freq, phase in self.flutter[index % len(self.flutter)])
        dip = 0.5 * (1 + wave / 3)  # 0 … 1
        return 1 - FLUTTER_MAX_DEPTH * self.levels["flutter"] * dip

    def _storm(self, n: int) -> np.ndarray:
        """Gewitter: zwischen Pausen ein Schub dichter Knacker."""
        start = self.sample_pos
        if start >= self.storm_end:
            # Schub vorbei (oder nach einer Pause, catch_up): den nächsten planen.
            self.storm_start = start + int(self.rng.uniform(*STORM_PAUSE_SECONDS) * SAMPLE_RATE)
            self.storm_end = self.storm_start + int(self.rng.uniform(*STORM_BURST_SECONDS) * SAMPLE_RATE)
        in_burst = self.storm_start <= start < self.storm_end
        if in_burst and self.rng.random() < STORM_RATE_PER_SECOND * n / SAMPLE_RATE:
            crash = self._make_crash()
            if len(self.storm_crash) < len(crash):
                self.storm_crash = np.concatenate([self.storm_crash, np.zeros(len(crash) - len(self.storm_crash),
                                                                              dtype=np.float32)])
            self.storm_crash[:len(crash)] += crash
        out = np.zeros(n, dtype=np.float32)
        part = self.storm_crash[:n]
        out[:len(part)] = part
        self.storm_crash = self.storm_crash[n:]
        return out

    def _fence(self, n: int) -> np.ndarray:
        """Weidezaun: ein Ticker je fence_period, kaum schwankend; ein Ticker
        kann in den nächsten Block reichen."""
        start = self.sample_pos
        if self.fence_next < start:  # nach einer Pause (catch_up): neu einreihen
            self.fence_next = start + int(self.extra_rng.uniform(0, self.fence_period) * SAMPLE_RATE)
        buf = self.fence_buf
        while self.fence_next < start + n:
            offset = self.fence_next - start
            tick = self._make_tick()
            if len(buf) < offset + len(tick):
                buf = np.concatenate([buf, np.zeros(offset + len(tick) - len(buf), dtype=np.float32)])
            buf[offset:offset + len(tick)] += tick
            jitter = self.extra_rng.uniform(-FENCE_JITTER_SECONDS, FENCE_JITTER_SECONDS)
            self.fence_next += int((self.fence_period + jitter) * SAMPLE_RATE)
        out = np.zeros(n, dtype=np.float32)
        part = buf[:n]
        out[:len(part)] = part
        self.fence_buf = buf[n:]
        return out

    def _make_tick(self) -> np.ndarray:
        """Ein Ticker des Weidezauns: harter Einsatz, sehr kurzes Abklingen."""
        length = int(FENCE_TICK_SECONDS * SAMPLE_RATE)
        start = int(self.extra_rng.integers(len(self.noise) - length))
        envelope = np.exp(-np.arange(length) / (length / 8))
        return (self.noise[start:start + length] * envelope * self.extra_rng.uniform(1.0, 1.2)).astype(np.float32)

    def _pump(self, crashes: np.ndarray, n: int) -> np.ndarray:
        """AGC-Pumpen: Verstärkung über den Block (1 = ungeregelt). Ein Knacker
        über AGC_PUMP_THRESHOLD drückt sie sofort herunter, danach erholt sie
        sich langsam."""
        before = self.pump
        peak = float(np.max(crashes)) if len(crashes) else 0.0
        if peak > AGC_PUMP_THRESHOLD:
            self.pump = max(self.pump, AGC_PUMP_MAX_DEPTH * self.levels["agc"] * min(peak / (2 * AGC_PUMP_THRESHOLD), 1))
        else:
            self.pump *= math.exp(-n / SAMPLE_RATE / AGC_PUMP_RELEASE_SECONDS)
        return 1 - np.linspace(before, self.pump, n)

    def _carrier(self, n: int) -> np.ndarray:
        """Träger nahe der eigenen Frequenz: wandert langsam, kommt und geht
        mit weichen Flanken; die Phase läuft über die Blöcke durch."""
        start = self.sample_pos
        if start >= self.carrier_switch:
            self.carrier_on = not self.carrier_on
            seconds = self.rng.uniform(*(CARRIER_ON_SECONDS if self.carrier_on else CARRIER_OFF_SECONDS))
            self.carrier_switch = start + int(seconds * SAMPLE_RATE)
            self.carrier_edge = start
        t = start / SAMPLE_RATE
        freq = self.freq + self.carrier_offset + CARRIER_DRIFT_HZ * math.sin(2 * math.pi * self.carrier_drift_hz * t)
        phases = self.carrier_phase + 2 * math.pi * freq * np.arange(1, n + 1) / SAMPLE_RATE
        self.carrier_phase = float(phases[-1] % (2 * math.pi))
        since = (start + np.arange(n) - self.carrier_edge) / SAMPLE_RATE
        ramp = np.clip(since / CARRIER_RAMP_SECONDS, 0, 1)
        envelope = ramp if self.carrier_on else 1 - ramp
        return np.sin(phases) * envelope

    def _fading(self, params, n: int) -> np.ndarray:
        """Fading-Verlauf (0 … 1) über die nächsten `n` Samples."""
        freq, phase, freq2, phase2, spread = params
        level = self.levels["qsb"]
        t = (self.sample_pos + np.arange(n)) / SAMPLE_RATE
        wave = (np.sin(2 * np.pi * freq * t + phase) + QSB_SECOND_WEIGHT * np.sin(2 * np.pi * freq2 * t + phase2))
        dip = 0.5 * (1 + wave / (1 + QSB_SECOND_WEIGHT))  # 0 … 1
        return 1 - min(level * QSB_MAX_DEPTH * spread, QSB_MAX_DEPTH) * dip

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


def noise_snr_db(level: float, gain: float = 1.0) -> float:
    """Rauschabstand in dB (2,4 kHz) für Regler `level` (0..1) und die
    Lautstärke der Störgeräusche `gain` (größer = mehr Rauschen)."""
    snr = SNR_DB_RANGE[0] + (SNR_DB_RANGE[1] - SNR_DB_RANGE[0]) * level
    return snr - 20 * math.log10(gain) if gain > 0 else math.inf


def chirp_max_hz(level: float) -> float:
    """Größte Frequenzablage beim Tasten für Regler `level` (chirp_for)."""
    return CHIRP_DELTA_HZ[1] * 2 * level


def _loop_slice(loop: np.ndarray, pos: int, n: int):
    """Nächste `n` Samples einer Endlosschleife ab `pos`; (neue Position, Samples)."""
    idx = (pos + np.arange(n)) % len(loop)
    return int((pos + n) % len(loop)), loop[idx]

# Stufen als Schnellwahl in der zentralen Einstellung und als Maßstab für
# das Diplom QRN-fest: Störung -> Pegel.
# Rauschabstand (noise_snr_db): leicht +8 dB, mittel +2 dB, stark −4 dB in
# 2,4 kHz (im Ohr rund 17 dB mehr); dazu wachsen QSB und weitere Störungen.
PRESETS = {
    "light": {"noise": 0.4, "qsb": 0.3},
    "medium": {"noise": 0.6, "qrn": 0.3, "qsb": 0.5},
    "heavy": {"noise": 0.8, "qrn": 0.5, "qsb": 0.8, "cw_qrm": 0.3},
}
# Rauschen schon vor dem ersten und noch nach dem letzten Zeichen.
PRESET_LEAD_SECONDS = (0.4, 0.3)
PRESET_BLOCK_SECONDS = 0.02
# Rauschen weich ein- und ausblenden (Kopfhörer); liegt ganz im Vor- bzw.
# Nachlauf, die Zeichen bleiben unberührt.
PRESET_FADE_SECONDS = 0.04


def preset_conditions(preset: str, freq: int) -> BandConditions:
    """BandConditions für eine Station mit den Pegeln aus PRESETS."""
    band = BandConditions(1)
    for effect, level in PRESETS[preset].items():
        band.enabled[effect] = True
        band.levels[effect] = level
    band.prepare(freq)
    return band


def apply_preset(band: BandConditions, samples: np.ndarray) -> tuple[np.ndarray, float]:
    """Legt die Bandbedingungen unter `samples` (Station 0), mit etwas
    Rauschen davor und danach. Gibt (Samples, Vorlauf in Sekunden) zurück.
    Zwischen zwei Aufrufen laufen die Bedingungen mit der Uhr weiter
    (catch_up), auch beim Wiederholen derselben Sequenz."""
    lead, tail = PRESET_LEAD_SECONDS
    padded = np.concatenate([silence(lead), samples, silence(tail)])
    band.catch_up()
    block = int(SAMPLE_RATE * PRESET_BLOCK_SECONDS)
    # Blockweise wie im QSO-Modus, damit Knackstörungen im richtigen Takt kommen.
    out = np.concatenate([band.mix([(padded[i:i + block], 0)], len(padded[i:i + block]))
                          for i in range(0, len(padded), block)])
    fade = min(int(PRESET_FADE_SECONDS * SAMPLE_RATE), len(out) // 2)
    if fade:
        ramp = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade))).astype(np.float32)
        out[:fade] *= ramp
        out[-fade:] *= ramp[::-1]
    return out, lead


# --- Zentrale Einstellung --------------------------------------------------
# Eine „Spec“ ist ein schlichtes dict, wie es gespeichert und im Netzwerk
# verschickt wird: {"levels": {Störung: Pegel 0..1, nur eingeschaltete},
# "gain": Lautstärke der Störgeräusche (background_gain)}, optional "filter"
# (aus FILTER_WIDTHS) und "qrm_offset" (Schlüssel aus QRM_OFFSETS); fehlen
# sie (etwa von einem älteren Trainer im Netzwerk), gelten 2,4 kHz und „weit“.
GAIN_RANGE = (0.1, 1.5)
# Optional "seed" (0 … SEED_LIMIT − 1): Zufallswert für BandConditions, im
# Netzwerk vom Trainer je Durchgang gewählt.
SEED_LIMIT = 2 ** 31


def spec_from_preset(preset: str) -> dict:
    """Spec für eine Stufe aus PRESETS ("light", "medium", "heavy") mit
    normaler Lautstärke der Störgeräusche."""
    return {"levels": dict(PRESETS[preset]), "gain": 1.0}


def _number(value) -> bool:
    """Endliche Zahl (JSON erlaubt auch NaN und Infinity)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def clean_spec(data):
    """Prüft eine Spec aus einer Datei oder vom Netzwerk; None, wenn sie
    unbrauchbar ist. Unbekannte Störungen fallen weg, Werte werden begrenzt."""
    if not isinstance(data, dict) or not isinstance(data.get("levels"), dict):
        return None
    levels = {}
    for effect, level in data["levels"].items():
        if effect in EFFECTS and _number(level):
            levels[effect] = min(max(float(level), 0.0), 1.0)
    gain = data.get("gain", 1.0)
    if not _number(gain):
        gain = 1.0
    spec = {"levels": levels, "gain": min(max(float(gain), GAIN_RANGE[0]), GAIN_RANGE[1])}
    if data.get("filter") in FILTER_WIDTHS and not isinstance(data.get("filter"), bool):
        spec["filter"] = data["filter"]
    if data.get("qrm_offset") in QRM_OFFSETS:
        spec["qrm_offset"] = data["qrm_offset"]
    seed = data.get("seed")
    if isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed < SEED_LIMIT:
        spec["seed"] = seed
    return spec


def apply_spec(band: BandConditions, spec) -> None:
    """Überträgt eine Spec auf BandConditions (None: alles aus). Auch
    während der Wiedergabe; danach band.prepare() aufrufen."""
    levels = spec["levels"] if spec else {}
    for effect in EFFECTS:
        band.enabled[effect] = effect in levels
        if effect in levels:
            band.levels[effect] = levels[effect]
    band.background_gain = spec["gain"] if spec else 1.0
    band.filter_width = spec.get("filter", DEFAULT_FILTER) if spec else DEFAULT_FILTER
    band.qrm_offset = spec.get("qrm_offset", DEFAULT_QRM_OFFSET) if spec else DEFAULT_QRM_OFFSET


def conditions(spec, freq: int, stations: int = 1) -> BandConditions:
    """Fertige BandConditions für `stations` Stationen nach `spec` (None: ohne
    Störungen), mit dem Zufallswert aus der Spec und den Störsignalen für die
    Tonhöhe `freq` schon erzeugt."""
    band = BandConditions(stations, spec.get("seed") if spec else None)
    apply_spec(band, spec)
    band.prepare(freq)
    return band


def spec_key(spec) -> tuple:
    """Hashbarer Schlüssel einer Spec, z. B. für einen Cache."""
    return (tuple(sorted(spec["levels"].items())), spec["gain"], spec.get("seed"),
            spec.get("filter", DEFAULT_FILTER), spec.get("qrm_offset", DEFAULT_QRM_OFFSET))


def preset_rank(spec):
    """Schwerste Stufe aus PRESETS, die die Spec mindestens erreicht (jede
    Störung der Stufe mindestens so stark), oder None. Die Lautstärke zählt
    hier nicht; das Diplom prüft sie getrennt. Ein schmales Filter nimmt
    Rauschen weg; das Rauschen zählt dann um so viel schwächer, bei jeder
    Tonhöhe gleich."""
    levels = dict(spec["levels"]) if spec else {}
    if spec and "noise" in levels:
        levels["noise"] -= filter_noise_db(spec.get("filter", DEFAULT_FILTER)) / abs(
            SNR_DB_RANGE[0] - SNR_DB_RANGE[1])
    rank = None
    for preset, wanted in PRESETS.items():  # leicht -> stark
        if all(levels.get(effect, 0.0) >= level - 1e-9 for effect, level in wanted.items()):
            rank = preset
    return rank
