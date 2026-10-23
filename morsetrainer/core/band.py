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
- Flatterfading: schnelles Zittern (rund 5 Hz), wie bei Aurora oder auf dem
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
from morsetrainer.core.storage import is_key

# Schlüssel der Störungen; BandConditions.enabled/levels sind danach
# indiziert.
EFFECTS = ("noise", "qrn", "qsb", "chirp", "ssb", "cw_qrm", "strength", "storm", "agc", "flutter", "carrier",
           "smps", "plc", "fence", "clicks")

NOISE_LOOP_SECONDS = 20
PASSBAND_HZ = (300, 2700)
# Rauschen als Rauschabstand S/N in dB, gemessen im Empfängerfilter
# (300–2700 Hz, Rauschbandbreite NOISE_BANDWIDTH_HZ) gegenüber dem
# ungeschwächten Signal (Dauerstrich, Effektivwert SIGNAL_RMS): Regler
# 0 % … 100 % gleichmäßig über SNR_DB_RANGE. Das Ohr hört CW wie durch ein
# Filter von etwa 50 Hz, dort ist der Abstand rund EAR_GAIN_DB größer.
SNR_DB_RANGE = (20.0, -10.0)
SIGNAL_RMS = AMPLITUDE / math.sqrt(2)
NOISE_BANDWIDTH_HZ = 1927  # Flanken des Filters eingerechnet (Test prüft gegen _noise_bandwidth)
EAR_GAIN_DB = 10 * math.log10(NOISE_BANDWIDTH_HZ / 50)
# Lauter als das wird das Rauschen (nach dem Filter) nicht; stattdessen wird alles Übrige
# leiser, wie bei der Regelung (AGC) eines Empfängers. So übersteuert auch
# ein Signal unter dem Rauschen nichts.
NOISE_RMS_CAP = 0.2
# So lange gleiten Rauschen, AGC und Störpegel nach einer Änderung hinüber
# (statt zu springen; beim Zuschalten ein sanftes Einblenden).
GAIN_GLIDE_SECONDS = 0.02

# Knackstörungen: mittlere Anzahl pro Sekunde, Länge und Stärke (ein
# Vielfaches von MAX_QRN_RMS bei Regler auf 100 %).
CRASH_RATE_PER_SECOND = 0.25
CRASH_SECONDS = (0.03, 0.2)
CRASH_GAIN = (2.0, 5.0)
# Eine Knackstörung ist eine Folge sehr kurzer Einzelentladungen
# (CRASH_PULSE_SECONDS lang, im Mittel CRASH_PULSE_GAP_SECONDS auseinander,
# nach hinten seltener), keine glatte Rauschwolke; Spitzen wie bei echtem
# Gewitter-QRN, CRASH_PULSE_BOOST gleicht die kürzere Dauer zum Teil aus.
CRASH_PULSE_SECONDS = (0.0002, 0.002)
CRASH_PULSE_GAP_SECONDS = 0.006
CRASH_PULSE_BOOST = 3.0
CRASH_PULSE_FADE = 0.93  # jede Entladung etwas schwächer als die vorige
MAX_QRN_RMS = 0.25

# Stärkeunterschiede: Grundstärke der Stationen (Station 0 ist gut zu
# hören; die Werte gelten für Regler auf 50 %, 100 % macht die Unterschiede
# doppelt so groß).
STRENGTH_FIRST = (0.9, 1.0)
STRENGTH_OTHERS = (0.35, 1.0)
# QSB und Flatterfading wie auf dem Band: Rice-Fading, also ein fester
# Anteil plus Streuung, die sich zufällig überlagert (komplexes
# Gauß-Rauschen mit der Bandbreite *_BANDWIDTH_HZ). Der Regler setzt das
# Verhältnis K von festem Anteil zu Streuung (rice_k): wenig Regler = großes
# K = flache Schwankungen, 100 % = K 0 = Rayleigh mit gelegentlich sehr
# tiefen, kurzen Löchern. Der Verlauf ist je Station eine nahtlose Schleife
# aus dem Startwert (im Netzwerk für alle gleich).
QSB_BANDWIDTH_HZ = 0.08  # tiefe Löcher (unter −10 dB) im Mittel alle 20 s, gestreut 7–50 s
QSB_RATE_HZ = 20  # so oft wird der Verlauf erzeugt, dazwischen interpoliert
QSB_LOOP_SECONDS = 600

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
SSB_CREST_LIMIT = 2.5  # Spitzen werden um dieses Vielfache des Effektivwerts weich begrenzt
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
# Ab dieser Abweichung der Tonhöhe entsteht das CW-QRM neu (sonst stimmte
# etwa „Zero-Beat“ nach dem Verstellen der Tonhöhe nicht mehr).
QRM_PITCH_TOLERANCE_HZ = 5
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
# Flatterfading (Polarlicht, Mehrwege): wie QSB, aber mit 8 Hz Spreizung;
# die Stärke zittert dann rund 5-mal je Sekunde.
FLUTTER_BANDWIDTH_HZ = 8.0
FLUTTER_RATE_HZ = 100
FLUTTER_LOOP_SECONDS = 60
# Signalgeführte AGC: Fehlt das Signal (Pause, tiefes Fading), regelt der
# Empfänger hoch, das Rauschen wird lauter – höchstens bis zur Lautstärke
# des Signals und um SIGNAL_AGC_MAX_DB. Sie folgt dem Signal sofort und
# lässt mit SIGNAL_AGC_RELEASE_SECONDS los; beim Ton bleibt der
# Rauschabstand also, wie er eingestellt ist.
SIGNAL_AGC_MAX_DB = 12.0
# Eigener Mithörton 3 dB leiser als eine volle Station: Zusammen mit dem
# Bandgeräusch begrenzte soft_limit sonst merklich oft (bei „leicht“ gut
# 2 % der Samples).
SIDETONE_GAIN = 10 ** (-3 / 20)
SIGNAL_AGC_RELEASE_SECONDS = 0.25
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
FENCE_TICK_SECONDS = 0.005
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
FILTER_ORDER = 8  # steile Flanken wie ein Quarz- oder DSP-Filter (300 Hz neben der Mitte −13 dB)
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
        speech = _normalized(np.fft.irfft(shifted, n)).astype(np.float64)
        # Wie ein Sprachprozessor am Sender: Spitzen weich gedrückt, sonst wäre der Crest-Faktor
        # (Spitze zu Effektivwert) mit rund 18 dB weit über dem echter, verdichteter Sprache.
        _ssb_loop = _normalized(SSB_CREST_LIMIT * np.tanh(speech / SSB_CREST_LIMIT))
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
    # Jedes Stück gleich als float32: alle erst in float64 zu sammeln kostete
    # bei 150 s Schleife über 100 MB zusätzlich.
    parts = [
        (build_text(text, wpm, freq + offset, chirp=chirp) if station == 0
         else silence(rng.uniform(*CW_QRM_PAUSE_SECONDS))).astype(np.float32)
        for station, text in qso.transmissions
    ]
    return np.concatenate(parts)


# Stückgröße für die Hüllkurve in _keyed (Abtastwerte).
ENVELOPE_CHUNK = 1 << 20


def _keyed(magnitude: np.ndarray, window: int):
    """1, wo der gleitende Mittelwert von `magnitude` über `window` Werte
    über 30 % seines Höchstwerts liegt, sonst 0 (int8, `window` kürzer);
    None ohne Signal. In Stücken gerechnet: Die ganze Schleife in float64
    hielte zwei Kopien von je über 50 MB."""
    count = len(magnitude) - window

    def envelope(start):
        total = np.cumsum(magnitude[start:start + ENVELOPE_CHUNK + window], dtype=np.float64)
        return (total[window:] - total[:-window]) / window

    starts = range(0, count, ENVELOPE_CHUNK)
    top = max((envelope(start).max() for start in starts), default=0.0)
    if top <= 0:
        return None
    return np.concatenate([(envelope(start) > 0.3 * top).astype(np.int8) for start in starts])


def _key_clicks(loop: np.ndarray, rng) -> np.ndarray:
    """Tastklicks zum CW-QRM `loop`: an jeder Flanke seiner Tastung ein
    kurzer, breitbandiger Klick (Spitze 1); gleich lang wie `loop`, damit
    beide mit derselben Position laufen."""
    window = int(0.005 * SAMPLE_RATE)
    clicks = np.zeros(len(loop), dtype=np.float32)
    if len(loop) <= window:
        return clicks
    keyed = _keyed(np.abs(loop), window)
    if keyed is None:
        return clicks
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
        self.cw_qrm_freq = None  # Tonhöhe, zu der cw_qrm den Abstand hält
        self.filter = None  # ((Breite, Tonhöhe), Impulsantwort) oder None
        self._filter_spectra = {}
        self.strengths = [self.rng.uniform(*STRENGTH_FIRST)] + [
            self.rng.uniform(*STRENGTH_OTHERS) for _ in range(station_count - 1)
        ]
        # Startwerte der Fading-Schleifen je Station (letzter Eintrag: CW-QRM);
        # die Schleifen selbst entstehen erst, wenn QSB bzw. Flattern läuft.
        self.qsb = [int(self.rng.integers(2 ** 63)) for _ in range(station_count + 1)]
        chirpy = [self.rng.random() < CHIRP_PROBABILITY for _ in range(station_count)]
        if not any(chirpy):
            chirpy[int(self.rng.integers(station_count))] = True
        self.chirps = [
            (self.rng.uniform(*CHIRP_DELTA_HZ) * self.rng.choice((-1, 1)), self.rng.uniform(*CHIRP_TAU_SECONDS))
            if c else None
            for c in chirpy
        ]
        self.flutter = [int(self.rng.integers(2 ** 63)) for _ in range(station_count + 1)]
        self._fading_loops = {}  # (Art, Startwert) -> komplexe Schleife
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
        self.pitch_gain = 1.0  # Empfängerfilter bei der Tonhöhe (prepare)
        self.rewind()

    def prepare(self, freq: int, qrm_freq=None) -> None:
        """Erzeugt die Störsignale, die gerade eingeschaltet sind (einmalig,
        neu bei anderem QRM-Abstand oder anderer Tonhöhe), und das CW-Filter
        um `freq`. Das CW-QRM hält seinen Abstand zu `qrm_freq` (sonst
        `freq`): Bei leicht verstimmten Stationen bleibt der Nachbar auf
        seiner Frequenz, statt mit jedem Ruf neu zu entstehen."""
        self.freq = freq
        # Ohne schmales CW-Filter formt das Empfängerfilter (300–2700 Hz) auch
        # das Signal: Bei sehr tiefem Ton ist es leiser, das Rauschen nicht.
        # Bezug 600 Hz, wo der Rauschabstand geeicht ist; höher wird es nicht lauter.
        gains = _passband_gain(np.array([float(freq), 600.0]))
        self.pitch_gain = min(float(gains[0] / gains[1]), 1.0)
        qrm_freq = freq if qrm_freq is None else qrm_freq
        if self.enabled["ssb"] and self.ssb is None:
            self.ssb = _ssb_babble_loop()
        if self.enabled["smps"] and self.smps is None:
            self.smps = _smps_buzz_loop()
        if self.enabled["plc"] and self.plc is None:
            self.plc = _plc_data_loop()
        neighbour = self.enabled["cw_qrm"] or self.enabled["clicks"]
        moved = self.cw_qrm_freq is not None and abs(qrm_freq - self.cw_qrm_freq) > QRM_PITCH_TOLERANCE_HZ
        if neighbour and (self.cw_qrm is None or self.cw_qrm_offset != self.qrm_offset or moved):
            offset = self.qrm_offset
            if self.cw_qrm is None or self.cw_qrm_offset != offset:
                self.qrm_builds += 1  # neuer Nachbar; nur andere Tonhöhe: derselbe, verschoben
            qrm_rng = np.random.default_rng([self.qrm_seed, self.qrm_builds - 1])
            loop = _cw_qrm_loop(qrm_rng, qrm_freq, QRM_OFFSETS[offset])
            # Erst die Klicks, dann die Schleife: mix() nimmt beide nur, wenn
            # sie zusammenpassen.
            self.key_clicks = _key_clicks(loop, qrm_rng)
            self.cw_qrm = loop
            self.cw_qrm_pos %= len(self.cw_qrm)
            self.cw_qrm_offset = offset
            self.cw_qrm_freq = qrm_freq
        if self.filter_width == DEFAULT_FILTER:
            self.filter = None
            self.noise = _shaped_noise_loop()
        else:
            self.noise = _filter_noise_loop()
            if self.filter is None or self.filter[0] != (self.filter_width, freq):
                self.filter = ((self.filter_width, freq), filter_ir(self.filter_width, freq).astype(np.float64))
        # Die Schwundschleifen aller Stationen jetzt, nicht im ersten Block: Bei vielen Stationen
        # kostet das sonst einen Block mehr Zeit, als der Puffer fasst.
        for kind in ("qsb", "flutter"):
            if self.enabled[kind]:
                for seed in getattr(self, kind):
                    self._fading_loop(kind, seed)

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
        self.gains = {}  # zuletzt verwendete Pegel (für _smooth)
        self.signal_hold = 0.0  # Signalspitze, auf die die AGC zuletzt regelte
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
        twin.gains = dict(self.gains)
        return twin

    def process(self, block: np.ndarray, station: int) -> np.ndarray:
        """Ein Block einer einzelnen Station, mit QSB und Hintergrund."""
        return self.mix([(block, station)], len(block))

    def mix(self, sources, n: int, receiver_agc: bool = True) -> np.ndarray:
        """Mischt mehrere gleichzeitige Signale [(Block, Station), …] zu
        einem Block der Länge `n` (kürzere Blöcke werden mit Stille
        aufgefüllt) und legt Rauschen/QRM darunter, alles durch das
        CW-Filter. Station None steht für den eigenen Mithörton (kein QSB,
        keine AGC, nicht gefiltert). Die signalgeführte AGC regelt auch in
        Blöcken ohne Station weiter (das Rauschen steigt dann weich an);
        `receiver_agc=False` lässt sie aus (Messungen des reinen Rauschens)."""
        noise_rms, agc = self.noise_and_agc()
        # Die AGC hebt höchstens bis zur Signalstärke, gemessen beim
        # Rauschabstand mit Lautstärke 100 %: So bleibt „Lautstärke der
        # Störgeräusche“ (auch „bei mir leiser“ im Netzwerk) in den Pausen wirksam.
        boost = (10 ** (noise_snr_db(self.levels["noise"]) / 20)
                 if noise_rms > 0 and self.background_gain > 0 else 1.0)
        agc_level = agc  # volle Signalspitze = AMPLITUDE · agc
        # Verstellt jemand Regler oder Schalter mitten im Ton, gleiten die
        # Pegel kurz hinüber, statt hörbar zu springen.
        noise_rms = self._smooth("noise", noise_rms, n)
        agc = self._smooth("agc", agc, n)
        out = np.zeros(n, dtype=np.float64)
        sidetone = np.zeros(n, dtype=np.float64)
        for block, station in sources:
            block = block[:n]
            if station is None:
                sidetone[:len(block)] += block * SIDETONE_GAIN
            elif station == VOICE:
                sidetone[:len(block)] += block
            else:
                pitch = self.pitch_gain if self.filter is None else 1.0
                out[:len(block)] += block * (self.station_gain(station, len(block)) * pitch
                                             * _head(agc, len(block)))
        receiver = self._signal_agc(out, boost, AMPLITUDE * agc_level, n) if receiver_agc else 1.0
        levels = self.levels
        if np.any(noise_rms):
            self.noise_pos, noise = _loop_slice(self.noise, self.noise_pos, n)
            out += noise * noise_rms
        out *= receiver  # die AGC hebt Stationen und Rauschen an, nicht die Störer neben ihnen
        # Knacker (QRN, Gewitter, Weidezaun) werden nicht gepumpt: sie kommen schneller als die
        # AGC und gehen ungedämpft durch, erst danach bricht das Signal ein.
        impulses = np.zeros(n, dtype=np.float64)
        if self._on("qrn"):
            impulses += self._crashes(n) * (MAX_QRN_RMS * levels["qrn"])
        if self._on("storm"):
            impulses += self._storm(n) * (MAX_QRN_RMS * levels["storm"])
        if self._on("fence"):
            impulses += self._fence(n) * (MAX_FENCE_RMS * levels["fence"])
        crashes = np.abs(impulses) if self._on("agc") else None  # Knacker, auf die die AGC reagiert
        background = np.zeros(n, dtype=np.float64)
        # Können parallel in prepare() entstehen.
        ssb, smps, plc, cw_qrm, clicks = self.ssb, self.smps, self.plc, self.cw_qrm, self.key_clicks
        for key, source, peak in (("ssb", ssb, MAX_SSB_RMS), ("smps", smps, MAX_SMPS_RMS),
                                  ("plc", plc, MAX_PLC_RMS)):
            if source is None:
                continue
            gain = self._smooth(key, peak * levels[key] if self._on(key) else 0.0, n)
            if np.any(gain):
                pos, part = _loop_slice(source, getattr(self, key + "_pos"), n)
                setattr(self, key + "_pos", pos)
                background += part * gain
        if cw_qrm is not None:
            neighbour_gain = self._smooth("cw_qrm", levels["cw_qrm"] if self._on("cw_qrm") else 0.0, n)
            click_gain = self._smooth("clicks", MAX_CLICK_AMPLITUDE * levels["clicks"] if self._on("clicks") else 0.0, n)
            if np.any(neighbour_gain) or np.any(click_gain):
                pos = self.cw_qrm_pos % len(cw_qrm)
                self.cw_qrm_pos, part = _loop_slice(cw_qrm, pos, n)
                fading = self._fading(len(self.qsb) - 1, n) if self._on("qsb") else 1.0
                neighbour = fading * self._flutter(len(self.flutter) - 1, n)
                background += part * neighbour * neighbour_gain
                if clicks is not None and len(clicks) == len(cw_qrm):
                    background += _loop_slice(clicks, pos, n)[1] * neighbour * click_gain
        if self._on("carrier"):
            background += self._carrier(n) * (MAX_CARRIER_AMPLITUDE * levels["carrier"])
        background_gain = self._smooth("background", self.background_gain, n) * agc
        out += background * background_gain
        if crashes is not None:
            out *= self._pump(crashes * self.background_gain, n)
        out += impulses * background_gain
        out = self._filtered(out)
        self.sample_pos += n
        return soft_limit(out + sidetone).astype(np.float32)

    def _signal_agc(self, signal: np.ndarray, boost: float, full: float, n: int):
        """Verstärkung der signalgeführten AGC je Sample (1 beim vollen Ton mit
        Spitze `full`, bis `boost`, höchstens SIGNAL_AGC_MAX_DB, ohne Signal). Die
        Signalspitze folgt sofort und klingt mit SIGNAL_AGC_RELEASE_SECONDS
        ab; laufendes Maximum im Logarithmus wie bei _pump."""
        boost = min(boost, 10 ** (SIGNAL_AGC_MAX_DB / 20))
        if boost <= 1.0:
            self.signal_hold = 0.0
            return 1.0
        if n == 0:
            return 1.0  # leerer Block: nichts zu regeln, die Spitze bleibt
        k = -1.0 / (SAMPLE_RATE * SIGNAL_AGC_RELEASE_SECONDS)
        t = np.arange(n)
        level = np.abs(signal)
        with np.errstate(divide="ignore"):
            marks = np.log(level) - k * t
            carried = math.log(self.signal_hold) + k if self.signal_hold > 0 else -math.inf
        hold = np.exp(np.maximum(np.maximum.accumulate(marks), carried) + k * t)
        self.signal_hold = float(hold[-1])
        return 1 + (boost - 1) * np.clip(1 - hold / full, 0, 1)

    def _smooth(self, key: str, value: float, n: int):
        """`value` für einen Block von `n` Samples; hat sich der Pegel seit
        dem letzten Block geändert, gleitet er in GAIN_GLIDE_SECONDS vom alten
        Wert hinüber (sonst bleibt es eine Zahl, das spart Rechenzeit)."""
        before = self.gains.get(key)
        self.gains[key] = value
        if before is None or before == value:
            return value
        glide = min(n, int(GAIN_GLIDE_SECONDS * SAMPLE_RATE))
        ramp = np.full(n, value, dtype=np.float64)
        ramp[:glide] = np.linspace(before, value, glide, endpoint=False)
        return ramp

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
        # Der Deckel gilt für das Rauschen hinter dem Filter: Ein schmales Filter lässt
        # weniger davon durch, das Signal muss dafür nicht leiser werden.
        cap = NOISE_RMS_CAP * 10 ** (filter_noise_db(self.filter_width) / 20)
        if rms <= cap:
            return rms, 1.0
        return cap, cap / rms

    def station_gain(self, station, n: int):
        """Lautstärke einer Station über die nächsten `n` Samples
        (Stärkeunterschiede und QSB); 1, wenn beides aus ist oder für den
        eigenen Mithörton (None)."""
        if station is None:
            return 1.0
        station %= len(self.strengths)
        gain = 1.0
        if self._on("strength"):
            gain = max(1 - (1 - self.strengths[station]) * 2 * self.levels["strength"], 0.05)
        if self._on("qsb"):
            gain = gain * self._fading(station, n)
        if self._on("flutter"):
            gain = gain * self._flutter(station, n)
        return gain

    def _flutter(self, index: int, n: int):
        """Flatterfading (0 … 1) über die nächsten `n` Samples; 1 ohne."""
        if not self._on("flutter"):
            return 1.0
        loop = self._fading_loop("flutter", self.flutter[index % len(self.flutter)])
        return rice_gain(_loop_at(loop, FLUTTER_RATE_HZ, self.sample_pos, n), self.levels["flutter"])

    def _fading_loop(self, kind: str, seed: int) -> np.ndarray:
        key = (kind, seed)
        loop = self._fading_loops.get(key)
        if loop is None:
            if kind == "qsb":
                loop = _gauss_loop(seed, QSB_LOOP_SECONDS, QSB_RATE_HZ, QSB_BANDWIDTH_HZ)
            else:
                loop = _gauss_loop(seed, FLUTTER_LOOP_SECONDS, FLUTTER_RATE_HZ, FLUTTER_BANDWIDTH_HZ)
            self._fading_loops[key] = loop
        return loop

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
        """AGC-Pumpen: Verstärkung je Sample (1 = ungeregelt). Ein Knacker
        über AGC_PUMP_THRESHOLD drückt sie genau dort herunter, wo er kommt,
        danach erholt sie sich mit AGC_PUMP_RELEASE_SECONDS – unabhängig
        davon, wie die Wiedergabe in Blöcke geteilt ist."""
        k = -1.0 / (SAMPLE_RATE * AGC_PUMP_RELEASE_SECONDS)  # log der Erholung je Sample
        t = np.arange(n)
        depth = AGC_PUMP_MAX_DEPTH * self.levels["agc"] * np.minimum(crashes[:n] / (2 * AGC_PUMP_THRESHOLD), 1)
        hit = (crashes[:n] > AGC_PUMP_THRESHOLD) & (depth > 0)
        # Tiefe = max über alle früheren Treffer s von depth[s]·e^(k·(t−s)),
        # mitsamt dem Rest aus dem vorigen Block: im Logarithmus ein laufendes
        # Maximum (ohne Schleife über die Samples).
        with np.errstate(divide="ignore"):
            marks = np.where(hit, np.log(np.where(hit, depth, 1.0)) - k * t, -np.inf)
            carried = math.log(self.pump) + k if self.pump > 0 else -math.inf
        best = np.maximum(np.maximum.accumulate(marks) if n else marks, carried)
        pump = np.where(np.isfinite(best), np.exp(best + k * t), 0.0)
        self.pump = float(pump[-1]) if n else self.pump
        return 1 - pump

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

    def _fading(self, index: int, n: int) -> np.ndarray:
        """QSB-Verlauf (0 … 1) der Station `index` über die nächsten `n` Samples
        (der letzte Index ist das CW-QRM)."""
        loop = self._fading_loop("qsb", self.qsb[index % len(self.qsb)])
        return rice_gain(_loop_at(loop, QSB_RATE_HZ, self.sample_pos, n), self.levels["qsb"])

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
        """Eine Knackstörung: unregelmäßige Folge kurzer Entladungen, die
        nach hinten seltener und schwächer werden."""
        length = int(self.rng.uniform(*CRASH_SECONDS) * SAMPLE_RATE)
        out = np.zeros(length, dtype=np.float32)
        strength = self.rng.uniform(*CRASH_GAIN) * CRASH_PULSE_BOOST
        t = 0
        while t < length:
            width = int(self.rng.uniform(*CRASH_PULSE_SECONDS) * SAMPLE_RATE) + 2
            start = int(self.rng.integers(len(self.noise) - width))
            pulse = self.noise[start:start + width] * np.exp(-np.arange(width) / (width / 3))
            end = min(t + width, length)
            out[t:end] += pulse[:end - t] * strength * self.rng.uniform(0.3, 1.0)
            gap = self.rng.exponential(CRASH_PULSE_GAP_SECONDS * (1 + 3 * t / length))
            t += int(gap * SAMPLE_RATE) + width
            strength *= CRASH_PULSE_FADE
        return out


def noise_snr_db(level: float, gain: float = 1.0) -> float:
    """Rauschabstand in dB im Empfängerfilter (NOISE_BANDWIDTH_HZ) für Regler
    `level` (0..1) und die Lautstärke der Störgeräusche `gain` (größer = mehr
    Rauschen)."""
    snr = SNR_DB_RANGE[0] + (SNR_DB_RANGE[1] - SNR_DB_RANGE[0]) * level
    return snr - 20 * math.log10(gain) if gain > 0 else math.inf


def chirp_max_hz(level: float) -> float:
    """Größte Frequenzablage beim Tasten für Regler `level` (chirp_for)."""
    return CHIRP_DELTA_HZ[1] * 2 * level


def _gauss_loop(seed: int, seconds: float, rate: float, bandwidth_hz: float) -> np.ndarray:
    """Komplexes Gauß-Rauschen (Leistung 1) mit gaußförmigem Spektrum der
    Breite `bandwidth_hz`, `rate` Werte je Sekunde; per FFT erzeugt und daher
    als Schleife nahtlos."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    spectrum = rng.normal(size=n) + 1j * rng.normal(size=n)
    spectrum *= np.exp(-(np.fft.fftfreq(n, 1 / rate) / bandwidth_hz) ** 2)
    z = np.fft.ifft(spectrum)
    # complex64 reicht für eine Verstärkung und halbiert den Speicher (Run-Modus: viele Stationen).
    return (z / np.sqrt(np.mean(np.abs(z) ** 2))).astype(np.complex64)


def _loop_at(loop: np.ndarray, rate: float, start: int, n: int) -> np.ndarray:
    """Werte der Schleife `loop` (`rate` je Sekunde) für die Samples
    start … start+n, linear interpoliert."""
    t = (start + np.arange(n)) * (rate / SAMPLE_RATE)
    i = np.floor(t).astype(np.int64)
    frac = t - i
    i %= len(loop)
    return loop[i] * (1 - frac) + loop[(i + 1) % len(loop)] * frac


def rice_k(level: float) -> float:
    """Regler (0 … 1) → Rice-Faktor K: leicht 30 % ≈ 4,3 (flache
    Schwankungen), mittel 50 % ≈ 1,9, stark 80 % ≈ 0,25, 100 % = 0 (Rayleigh).
    Bis 50 % wird 0,3 abgezogen, darüber läuft der Abzug mit K gegen null, damit
    der Regler bis zum Ende wirkt."""
    rest = 1 - level
    return max(10 * rest ** 2.2 - 0.3 * min(1.0, (rest / 0.5) ** 2.2), 0.0)


def rice_gain(scatter: np.ndarray, level: float) -> np.ndarray:
    """Fading-Verstärkung (höchstens 1) aus dem Streuanteil `scatter`
    (komplex, Leistung 1) bei Regler `level`."""
    k = rice_k(level)
    return np.minimum(np.abs(math.sqrt(k / (k + 1)) + math.sqrt(1 / (k + 1)) * scatter), 1.0)


def _head(gain, n: int):
    """Die ersten `n` Werte eines Pegelverlaufs (oder die Zahl selbst)."""
    return gain[:n] if isinstance(gain, np.ndarray) else gain


def _loop_slice(loop: np.ndarray, pos: int, n: int):
    """Nächste `n` Samples einer Endlosschleife ab `pos`; (neue Position, Samples)."""
    idx = (pos + np.arange(n)) % len(loop)
    return int((pos + n) % len(loop)), loop[idx]

# Stufen als Schnellwahl in der zentralen Einstellung und als Maßstab für
# das Diplom QRN-fest: Störung -> Pegel.
# Rauschabstand (noise_snr_db): leicht +8 dB, mittel +2 dB, stark −4 dB im
# Empfängerfilter (im Ohr rund 16 dB mehr); dazu wachsen QSB und weitere Störungen.
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


def pitch_loss_db(freq, filter_width: int = DEFAULT_FILTER) -> float:
    """So viel leiser ist das Signal bei der Tonhöhe `freq` als bei 600 Hz:
    Ohne schmales Filter dämpft das Empfängerfilter sehr tiefe Töne (300 Hz
    etwa 3 dB), das Rauschen nicht. Das schmale Filter wandert mit der
    Tonhöhe, dann 0."""
    if freq is None or filter_width != DEFAULT_FILTER:
        return 0.0
    gains = _passband_gain(np.array([float(freq), 600.0]))
    return max(-20 * math.log10(min(float(gains[0] / gains[1]), 1.0)), 0.0)


def _noise_level_db(db: float) -> float:
    """`db` Rauschabstand als Pegel des Reglers Rauschen (0..1)."""
    return db / abs(SNR_DB_RANGE[0] - SNR_DB_RANGE[1])


def pitch_compensated(spec: dict, freq) -> dict:
    """`spec` mit um pitch_loss_db schwächerem Rauschen (auf ganze Prozent
    aufgerundet), damit eine Stufe bei tiefem Ton nicht schwerer ist als bei
    600 Hz; preset_rank(…, freq) rechnet den Verlust wieder gut."""
    loss = pitch_loss_db(freq, spec.get("filter", DEFAULT_FILTER))
    if not loss or "noise" not in spec["levels"]:
        return spec
    levels = dict(spec["levels"])
    levels["noise"] = max(math.ceil((levels["noise"] - _noise_level_db(loss)) * 100 - 1e-6) / 100, 0.0)
    return {**spec, "levels": levels}


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
    if is_key(data.get("qrm_offset"), QRM_OFFSETS):
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


def preset_rank(spec, freq=None):
    """Schwerste Stufe aus PRESETS, die die Spec mindestens erreicht (jede
    Störung der Stufe mindestens so stark), oder None. Die Lautstärke zählt
    hier nicht; das Diplom prüft sie getrennt. Ein schmales Filter nimmt
    Rauschen weg; das Rauschen zählt dann um so viel schwächer, bei jeder
    Tonhöhe gleich. Bei sehr tiefer Tonhöhe `freq` ohne schmales Filter ist
    das Signal leiser (pitch_loss_db); das Rauschen zählt um so viel stärker."""
    levels = dict(spec["levels"]) if spec else {}
    if spec and "noise" in levels:
        width = spec.get("filter", DEFAULT_FILTER)
        levels["noise"] += _noise_level_db(pitch_loss_db(freq, width) - filter_noise_db(width))
    rank = None
    for preset, wanted in PRESETS.items():  # leicht -> stark
        if all(levels.get(effect, 0.0) >= level - 1e-9 for effect, level in wanted.items()):
            rank = preset
    return rank
