"""Tagesübung: zehn Minuten ohne Entscheidungen, mit drei Sternen.

Die App stellt die Übung aus dem zusammen, was dran ist (siehe plan()):
Aufwärmen mit Einzelzeichen (fällige Zeichen der Lernkartei bevorzugt),
Hauptteil mit Gruppen, Ausklang mit Wörtern, Rufzeichen oder
Kontinuierlich – je nach Stufe (stage()). Geübt wird in den vorhandenen
Reitern; dieses Modul enthält nur die Regeln und den gespeicherten Stand.

Regeln, die das Hören-Lernen schützen:
- Im Hauptteil bleibt das Tempo fest; angepasst wird von Tag zu Tag
  (next_tempo()). Mitwachsendes Tempo pendelt bei etwa der Hälfte richtig
  ein, ★ Sauber wäre dann nie erreichbar.
- Die Lektion steigt automatisch auf, wirksam ab dem nächsten Tag
  (apply_pending_lesson()); so lohnt es sich nicht, für sichere Sterne in
  der alten Lektion zu bleiben. In den ersten Tagen einer neuen Lektion
  reicht für ★ Sauber ein niedrigerer Anteil.
- Sterne gehen nie verloren; am selben Tag gibt es jeden höchstens einmal.

Gespeichert in stats/daily.json (bleibt beim Zurücksetzen der
Gesamtstatistik stehen):
{"lesson", "lesson_since", "pending_lesson", "pending_since",
 "tempo": {"wpm", "effective"},
 "days": {"JJJJ-MM-TT": {"stars", "minutes", "blocks", "progress"}}}"""
from dataclasses import dataclass, field
from datetime import date

from morsetrainer.core import koch, stats, storage, tempo

DAILY_FILE_NAME = "daily.json"

TOTAL_MINUTES = 10
# Etwas Spielraum für ★ Dabei: die letzte Eingabe nach Ablauf der Zeit,
# auf Sekunden gerundete Blockenden.
DABEI_TOLERANCE_MIN = 0.25

# Nach Lektion 44 (alle Zeichen samt Betriebszeichen): „nach Koch“.
POST_KOCH = koch.MAX_LESSON + 1
EARLY, WORDS, MIXED, POST = "early", "words", "mixed", "post"
WORDS_FROM_LESSON = 10   # vorher zu wenige Wörter (core/words.py)
CALLS_FROM_LESSON = 30   # vorher zu wenige Rufzeichen aus gelernten Zeichen

# Aufwärmen: fällige Zeichen brauchen je MIN_ATTEMPTS Versuche für die
# Tagesentscheidung der Lernkartei; ab MANY_DUE wird der Block länger.
WARMUP_MINUTES = 3
WARMUP_MAX_MINUTES = 4
WARMUP_POST_MINUTES = 2
MANY_DUE = 8
WARMUP_PER_EXTRA_DUE = 0.25
MAIN_MIN_MINUTES = 4
OUTRO_MINUTES = 2
OUTRO_POST_MINUTES = 4

# Tagestempo: aus dem Hauptteil eines Tages für den nächsten.
TEMPO_MIN_CHARS = 100
TEMPO_UP_SHARE = 0.9
TEMPO_DOWN_SHARE = 0.75

# ★ Sauber: Erstversuch-Anteil im Hauptteil.
CLEAN_MIN_CHARS = koch.ADVANCE_MIN_CHARS
CLEAN_SHARE = 0.9
CLEAN_SHARE_NEW_LESSON = 0.8
NEW_LESSON_DAYS = 3

# ★ Weiter: ein Zeichen erreicht erstmals dieses Fach (Index, 2 = Fach 3).
PROGRESS_BOX = 2

DABEI, SAUBER, WEITER = "dabei", "sauber", "weiter"
STAR_ORDER = (DABEI, SAUBER, WEITER)
LESSON_UP, TEMPO_UP, BOX_PREFIX = "lesson_up", "tempo_up", "box:"

WARMUP, MAIN, OUTRO = "warmup", "main", "outro"


@dataclass
class Block:
    kind: str       # WARMUP, MAIN, OUTRO
    mode: str       # "single", "group", "word", "callsign", "continuous"
    minutes: float
    params: dict = field(default_factory=dict)


def _path():
    return stats.STATS_DIR / DAILY_FILE_NAME


def load() -> dict:
    data = storage.load_json(_path(), {})
    if not isinstance(data, dict):
        return {}
    if not isinstance(data.get("days"), dict):
        data["days"] = {}
    return data


def save(state: dict) -> None:
    try:
        stats.STATS_DIR.mkdir(exist_ok=True)
        storage.write_json_atomic(_path(), state, indent=1, sort_keys=True)
    except OSError:
        pass  # Stand von heute fehlt dann; die Übung selbst ist protokolliert


# --- Stufe und Ablauf ---------------------------------------------------------

def stage(lesson: int) -> str:
    if lesson >= POST_KOCH:
        return POST
    if lesson >= CALLS_FROM_LESSON:
        return MIXED
    if lesson >= WORDS_FROM_LESSON:
        return WORDS
    return EARLY


def lesson_charset(lesson: int) -> str:
    """Zeichensatz einer Lektion; nach Koch alle Zeichen."""
    return koch.lesson_charset(min(lesson, koch.MAX_LESSON))


def warmup_minutes(lesson: int, due_count: int) -> float:
    if stage(lesson) == POST:
        return WARMUP_POST_MINUTES
    extra = max(due_count - MANY_DUE + 1, 0) * WARMUP_PER_EXTRA_DUE
    return min(WARMUP_MINUTES + extra, WARMUP_MAX_MINUTES)


def plan(lesson: int, due_count: int, today: date) -> list:
    """Die Blöcke der heutigen Tagesübung, zusammen TOTAL_MINUTES.
    `due_count`: heute fällige Zeichen der Lernkartei im Zeichensatz; ohne
    sie übt das Aufwärmen die häufigsten Verwechslungen (die App fällt auf
    die schwächsten Zeichen zurück, wenn es keine gibt)."""
    level = stage(lesson)
    focus = "due" if due_count else "confusions"
    warmup = Block(WARMUP, "single", warmup_minutes(lesson, due_count), {"focus": focus})
    if level == POST:
        outro_minutes = OUTRO_POST_MINUTES
        outro = Block(OUTRO, "callsign", outro_minutes)
        main_mode, main_params = "continuous", {"content": "chars", "group_len": 5}
    else:
        outro_minutes = OUTRO_MINUTES
        if level == EARLY:
            outro = Block(OUTRO, "continuous", outro_minutes, {"content": "chars", "group_len": 3})
        elif level == WORDS or today.toordinal() % 2 == 0:
            outro = Block(OUTRO, "word", outro_minutes)
        else:
            outro = Block(OUTRO, "callsign", outro_minutes)
        main_mode, main_params = "group", {}
    main_minutes = max(TOTAL_MINUTES - warmup.minutes - outro_minutes, MAIN_MIN_MINUTES)
    return [warmup, Block(MAIN, main_mode, main_minutes, main_params), outro]


# --- Lektion ------------------------------------------------------------------

def current_lesson(state: dict, fallback: int) -> int:
    """Gespeicherte Lektion, beim ersten Mal `fallback` (Lektion aus der
    Kopfleiste)."""
    lesson = state.get("lesson")
    if isinstance(lesson, int) and not isinstance(lesson, bool) and 1 <= lesson <= POST_KOCH:
        return lesson
    return min(max(fallback, 1), POST_KOCH)


def apply_pending_lesson(state: dict, today: date) -> bool:
    """Einen Aufstieg vom Vortag übernehmen. True, wenn die Lektion wechselt."""
    pending, since = state.get("pending_lesson"), state.get("pending_since")
    if not isinstance(pending, int) or not isinstance(since, str) or since >= today.isoformat():
        return False
    state.update(lesson=pending, lesson_since=today.isoformat(), pending_lesson=None, pending_since=None)
    return True


def is_new_lesson(state: dict, today: date) -> bool:
    """In den ersten NEW_LESSON_DAYS Tagen seit dem Aufstieg."""
    try:
        since = date.fromisoformat(state.get("lesson_since") or "")
    except ValueError:
        return False
    return 0 <= (today - since).days < NEW_LESSON_DAYS


def passes_lesson(result: dict, char_wpm: int) -> bool:
    """Koch-Kriterium im Hauptteil: genug Zeichen, 90 % beim ersten
    Versuch, Zeichen nicht so langsam, dass man mitzählen kann."""
    correct, total = _first_try(result)
    return char_wpm >= koch.SLOW_CHAR_WPM and koch.passed(correct, total)


# --- Tempo --------------------------------------------------------------------

def initial_tempo(wpm: int, fw) -> dict:
    """Tagestempo beim ersten Mal aus der aktuellen Einstellung; die Zeichen
    nicht langsamer als koch.SLOW_CHAR_WPM, das effektive Tempo bleibt."""
    char = max(wpm, koch.SLOW_CHAR_WPM)
    return {"wpm": char, "effective": min(tempo.effective(wpm, fw), char)}


def current_tempo(state: dict, wpm: int, fw) -> dict:
    saved = state.get("tempo")
    if (isinstance(saved, dict) and all(isinstance(saved.get(k), int) for k in ("wpm", "effective"))
            and tempo.LIMITS[0] <= saved["effective"] <= saved["wpm"] <= tempo.LIMITS[1]):
        return {"wpm": saved["wpm"], "effective": saved["effective"]}
    return initial_tempo(wpm, fw)


def next_tempo(current: dict, result: dict) -> dict:
    """Tempo für die nächste Tagesübung nach dem Hauptteil: ab
    TEMPO_UP_SHARE beim ersten Versuch eins schneller, unter
    TEMPO_DOWN_SHARE eins langsamer, sonst gleich; unter TEMPO_MIN_CHARS
    Zeichen ist die Quote zu zufällig."""
    correct, total = _first_try(result)
    if total < TEMPO_MIN_CHARS:
        return dict(current)
    share = correct / total
    delta = 1 if share >= TEMPO_UP_SHARE else -1 if share < TEMPO_DOWN_SHARE else 0
    if not delta:
        return dict(current)
    fw = current["effective"] if current["effective"] < current["wpm"] else None
    wpm, fw = tempo.step(current["wpm"], fw, delta)
    return {"wpm": wpm, "effective": tempo.effective(wpm, fw)}


# --- Ergebnisse und Sterne ---------------------------------------------------

def _first_try(result: dict):
    """(richtig, gesamt) beim ersten Versuch. Gruppen liefern die
    Erstversuch-Zähler; Kontinuierlich zählt überzählige Tasten als Fehler."""
    if "first_try_total" in result:
        return result.get("first_try_correct", 0), result["first_try_total"]
    correct = max(result.get("correct", 0) - result.get("extra_keys", 0), 0)
    return correct, result.get("total", 0)


def day_entry(state: dict, today: date) -> dict:
    entry = state["days"].setdefault(today.isoformat(), {})
    for key, default in (("stars", []), ("blocks", []), ("progress", []), ("minutes", 0.0)):
        if not isinstance(entry.get(key), type(default)):
            entry[key] = default
    return entry


def _add_star(entry: dict, star: str) -> bool:
    if star in entry["stars"]:
        return False
    entry["stars"] = [s for s in STAR_ORDER if s in entry["stars"] or s == star]
    return True


def _add_progress(entry: dict, item: str) -> bool:
    if item in entry["progress"]:
        return False
    entry["progress"].append(item)
    return True


def finish_block(state: dict, today: date, block: Block, result: dict) -> list:
    """Ergebnis eines Blocks übernehmen. `result` aus dem Modus: richtig,
    gesamt, Erstversuche, überzählige Tasten, Minuten, Zeichentempo,
    Hochstufungen der Lernkartei („review_events“). Gibt die dabei neu
    verdienten Sterne zurück (für die Zwischenkarte)."""
    entry = day_entry(state, today)
    entry["blocks"].append({"kind": block.kind, "mode": block.mode,
                            **{k: v for k, v in result.items() if k != "review_events"}})
    entry["minutes"] = round(entry["minutes"] + result.get("minutes", 0.0), 2)
    new_stars = []
    progress = False
    for event in result.get("review_events", []):
        if event.get("first") and event.get("box", 0) >= PROGRESS_BOX:
            progress |= _add_progress(entry, BOX_PREFIX + event["char"])
    if block.kind == MAIN:
        correct, total = _first_try(result)
        lesson = current_lesson(state, 1)
        share = CLEAN_SHARE_NEW_LESSON if is_new_lesson(state, today) else CLEAN_SHARE
        if total >= CLEAN_MIN_CHARS and correct / total >= share and _add_star(entry, SAUBER):
            new_stars.append(SAUBER)
        if (lesson < POST_KOCH and state.get("pending_lesson") is None
                and passes_lesson(result, result.get("wpm", 0))):
            state.update(pending_lesson=lesson + 1, pending_since=today.isoformat())
            progress |= _add_progress(entry, LESSON_UP)
        current = state.get("tempo") or {}
        if current:
            following = next_tempo(current, result)
            if following["effective"] > current["effective"]:
                progress |= _add_progress(entry, TEMPO_UP)
            state["tempo"] = following
    if progress and _add_star(entry, WEITER):
        new_stars.append(WEITER)
    return new_stars


def finish_day(state: dict, today: date, completed: bool) -> list:
    """Am Ende der Tagesübung: ★ Dabei, wenn alle Blöcke zu Ende liefen und
    die Zeit zusammenkam. Gibt die neu verdienten Sterne zurück."""
    entry = day_entry(state, today)
    if completed and entry["minutes"] >= TOTAL_MINUTES - DABEI_TOLERANCE_MIN and _add_star(entry, DABEI):
        return [DABEI]
    return []


def stars_on(state: dict, day: date) -> list:
    entry = state.get("days", {}).get(day.isoformat(), {})
    stars = entry.get("stars", []) if isinstance(entry, dict) else []
    return [s for s in STAR_ORDER if s in stars]
