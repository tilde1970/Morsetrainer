"""Tagesübung: zehn Minuten ohne Entscheidungen, mit drei Sternen.

Die App stellt die Übung aus dem zusammen, was dran ist (siehe plan()):
Aufwärmen mit Einzelzeichen (fällige Zeichen der Lernkartei bevorzugt),
Hauptteil mit Gruppen, Ausklang mit Wörtern, Rufzeichen oder
Kontinuierlich – je nach Stufe (stage()). Geübt wird in den vorhandenen
Reitern; dieses Modul enthält nur die Regeln und den gespeicherten Stand.

Regeln, die das Hören-Lernen schützen:
- Im Hauptteil bleibt das Tempo fest; angepasst wird von Tag zu Tag
  (next_tempo(), wirksam ab dem nächsten Tag wie der Aufstieg).
  Mitwachsendes Tempo pendelt bei etwa der Hälfte richtig ein, ★ Sauber
  wäre dann nie erreichbar. Solange neue Lektionen kommen, wird es nur
  langsamer, nie schneller: Ein guter Tag bringt schon das neue Zeichen,
  beides zugleich wäre zu steil (wie bei Koch: Tempo fest, Zeichen
  dazu). Schneller wird es erst nach Koch.
- Die Lektion steigt automatisch auf, wirksam ab dem nächsten Tag
  (apply_pending_lesson()); so lohnt es sich nicht, für sichere Sterne in
  der alten Lektion zu bleiben. In den ersten Tagen einer neuen Lektion
  reicht für ★ Sauber ein niedrigerer Anteil.
- Sterne gehen nie verloren; am selben Tag gibt es jeden höchstens einmal.

Gespeichert in der Datenbank unter "daily" (bleibt beim Zurücksetzen der
Gesamtstatistik stehen):
{"lesson", "lesson_since", "pending_lesson", "pending_since",
 "tempo": {"wpm", "effective"}, "pending_tempo", "pending_tempo_since",
 "tempo_best" (höchstes effektives Tagestempo), "icr_limit" (Zeitlimit
 am Ende des letzten Aufwärmens),
 "days": {"JJJJ-MM-TT": {"stars", "minutes", "blocks", "progress", "lesson",
 "tempo" (effektives Tagestempo im Hauptteil, für die Lebenslinie)}}}"""
import math
from dataclasses import dataclass, field
from datetime import date

from morsetrainer.core import db, koch, review, stats, tempo

STATE_KEY = "daily"

TOTAL_MINUTES = 10
# Etwas Spielraum für ★ Dabei: die letzte Eingabe nach Ablauf der Zeit,
# auf Sekunden gerundete Blockenden.
DABEI_TOLERANCE_MIN = 0.25

# Nach der Abschlusslektion 41 (alle Zeichen): „nach Koch“. Die
# Betriebszeichen-Lektionen 42–45 gibt es nur von Hand, nicht hier.
POST_KOCH = koch.FINAL_LESSON + 1
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


def load() -> dict:
    data = db.load_state(STATE_KEY, {})
    if not isinstance(data.get("days"), dict):
        data["days"] = {}
    return data


def save(state: dict) -> None:
    try:
        db.save_state(STATE_KEY, state)
    except (db.Error, OSError):
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


def lesson_charset(lesson: int, learned: str = "") -> str:
    """Zeichensatz einer Lektion; nach Koch alle Zeichen. Betriebszeichen nur,
    wenn sie schon gelernt sind (`learned`: Zeichen in der Lernkartei), damit
    sie wiederholt werden – dann der Zeichensatz der Lektion bis zum letzten
    davon (42–45), so bleibt die Lektion an den Sitzungen erkennbar."""
    if lesson < POST_KOCH:
        return koch.lesson_charset(min(lesson, koch.FINAL_LESSON))
    count = max((koch.PROSIGN_ORDER.index(ch) + 1 for ch in learned if ch in koch.PROSIGN_ORDER), default=0)
    return koch.lesson_charset(koch.FINAL_LESSON + count)


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
    Kopfleiste). Vor 2.23 ging es bis Lektion 45 (nach 44); alles über
    POST_KOCH ist jetzt „nach Koch“."""
    lesson = state.get("lesson")
    if isinstance(lesson, int) and not isinstance(lesson, bool) and lesson >= 1:
        return min(lesson, POST_KOCH)
    return min(max(fallback, 1), POST_KOCH)


def apply_pending_lesson(state: dict, today: date) -> bool:
    """Einen Aufstieg vom Vortag übernehmen. True, wenn die Lektion wechselt."""
    pending, since = state.get("pending_lesson"), state.get("pending_since")
    if not isinstance(pending, int) or not isinstance(since, str) or since >= today.isoformat():
        return False
    state.update(lesson=min(pending, POST_KOCH), lesson_since=today.isoformat(), pending_lesson=None,
                 pending_since=None)
    return True


def apply_pending_tempo(state: dict, today: date) -> bool:
    """Tagestempo vom Vortag übernehmen. True, wenn es sich ändert."""
    pending, since = state.get("pending_tempo"), state.get("pending_tempo_since")
    if not isinstance(pending, dict) or not isinstance(since, str) or since >= today.isoformat():
        return False
    changed = pending != state.get("tempo")
    state.update(tempo=pending, pending_tempo=None, pending_tempo_since=None)
    return changed


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


def warmup_limit(state: dict) -> float:
    """Zeitlimit für das Aufwärmen: weiter, wo das letzte aufgehört hat
    (sonst bräuchte ein Geübter jeden Tag die halbe Aufwärmzeit, bis es
    wieder knapp ist), aber nicht länger als „flüssig“ in der Lernkartei."""
    saved = state.get("icr_limit")
    if isinstance(saved, (int, float)) and not isinstance(saved, bool) and saved > 0:
        return min(float(saved), review.FLUENT_LATENCY_S)
    return review.FLUENT_LATENCY_S


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


def next_tempo(current: dict, result: dict, allow_up: bool = True) -> dict:
    """Tempo für die nächste Tagesübung nach dem Hauptteil: ab
    TEMPO_UP_SHARE beim ersten Versuch eins schneller (nur mit `allow_up`),
    unter TEMPO_DOWN_SHARE eins langsamer, sonst gleich; unter
    TEMPO_MIN_CHARS Zeichen ist die Quote zu zufällig."""
    correct, total = _first_try(result)
    if total < TEMPO_MIN_CHARS:
        return dict(current)
    share = correct / total
    delta = 1 if share >= TEMPO_UP_SHARE and allow_up else -1 if share < TEMPO_DOWN_SHARE else 0
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
    entry.setdefault("lesson", current_lesson(state, 1))  # für den Wochenrückblick
    entry["blocks"].append({"kind": block.kind, "mode": block.mode,
                            **{k: v for k, v in result.items() if k not in ("review_events", "chars")}})
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
        if current.get("effective"):
            entry["tempo"] = current["effective"]
        # Einmal am Tag, wirksam ab morgen: eine zweite Tagesübung läuft im
        # selben Tempo und ändert es nicht noch einmal.
        if current and _first_try(result)[1] >= TEMPO_MIN_CHARS and state.get("pending_tempo_since") != today.isoformat():
            following = next_tempo(current, result, allow_up=lesson >= POST_KOCH)
            state.update(pending_tempo=following, pending_tempo_since=today.isoformat())
            best = state.get("tempo_best")
            best = best if isinstance(best, int) and not isinstance(best, bool) else current["effective"]
            # ★ Weiter nur für ein nie erreichtes Tempo, nicht fürs Zurückkommen.
            if following["effective"] > best:
                progress |= _add_progress(entry, TEMPO_UP)
            state["tempo_best"] = max(best, following["effective"])
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
    return [s for s in STAR_ORDER if isinstance(stars, list) and s in stars]


# --- Rückblick: Zwischenkarte und Abendbilanz ---------------------------------
# Verglichen wird nur, was sich fair vergleichen lässt; es gibt kein
# „schlechter“, nur „besser“, „Stand gehalten“ oder „noch zu wenig Daten“.

WEEK_DAYS = 7
# Reaktionszeit je Zeichen: Median der Zeit nach dem Zeichen, nur aus
# Einzelzeichen bei etwa gleichem Zeichentempo (Mitschreiben in Gruppen
# misst etwas anderes). Verpasste und falsche Antworten zählen als
# unendlich langsam: Sonst sänke der Median schon, wenn ein kürzeres Limit
# die langsamen Antworten zu verpassten macht. „Besser“ erst ab beiden
# Schwellen.
LATENCY_WEEK_MIN = 20
LATENCY_WPM_SPREAD = 2
LATENCY_TODAY_MIN = 10
BETTER_SHARE = 0.15
BETTER_SECONDS = 0.1
# Gruppen: Erstversuch-Anteil bei gleichem effektivem Tempo.
GROUPS_WEEK_MIN_CHARS = 200
GROUPS_BETTER_POINTS = 0.03
MOMENTS_SHOWN = 2
BETTER_SHOWN = 3
BETTER, HELD, FEW = "better", "held", "few"

# „Noch 5 Min“ in der Abendbilanz: einmal am Tag, nur nach einem guten
# Hauptteil, mit anderem Inhalt als heute.
EXTRA = "extra"
EXTRA_MINUTES = 5
EXTRA_MIN_SHARE = TEMPO_DOWN_SHARE
RUFZ_FROM_LESSON = 27   # Rufzeichen brauchen die erste Ziffer (Lektion 23) und genug Zeichen
CONFUSIONS, RUFZ, WORD = "confusions", "rufz", "word"


def _session_files(first: date, last: date):
    """Sitzungsdateien mit Startdatum von `first` bis `last` (einschließlich)."""
    for path in stats.STATS_DIR.glob("20*.jsonl"):
        try:
            day = date.fromisoformat(path.name[:10])
        except ValueError:
            continue
        if first <= day <= last:
            yield path


def latencies(first: date, last: date) -> dict:
    """{Zeichen: {Zeichentempo: [Sekunden]}} aus Einzelzeichen-Sitzungen;
    verpasst oder falsch = math.inf. Angenommene Zeiten zählen nicht."""
    data = {}
    for path in _session_files(first, last):
        wpm = None
        for obj in stats._read_jsonl(path):
            kind = obj.get("type")
            if kind == "config":
                if obj.get("mode") != "single" or obj.get("self_assessed") or obj.get("char_stats") is False:
                    break
                wpm = obj.get("wpm")
                if not isinstance(wpm, int) or isinstance(wpm, bool):
                    break
            elif kind == "char" and wpm is not None:
                value = obj.get("latency_s")
                if obj.get("correct") and isinstance(value, (int, float)) and not isinstance(value, bool):
                    if obj.get("latency_assumed"):
                        continue
                    value = max(value, 0.0)
                else:
                    value = math.inf
                data.setdefault(obj.get("char"), {}).setdefault(wpm, []).append(value)
    return data


def group_shares(first: date, last: date) -> dict:
    """{effektives Tempo: [richtig, gesamt]} beim ersten Versuch in Gruppen
    mit festem Tempo (mitwachsendes Tempo ist nicht vergleichbar)."""
    data = {}
    for path in _session_files(first, last):
        config, summary = stats._config_and_summary(path)
        if (not config or not summary or config.get("mode") != "group" or config.get("self_assessed")
                or config.get("adaptive_tempo") or summary.get("wpm_effective_reached")
                or not summary.get("first_try_total")):
            continue
        try:
            fw = config.get("farnsworth_wpm")
            wpm = tempo.effective(int(config["wpm"]), int(fw) if fw else None)
            counts = data.setdefault(wpm, [0, 0])
            counts[0] += int(summary.get("first_try_correct", 0))
            counts[1] += int(summary["first_try_total"])
        except (KeyError, TypeError, ValueError):
            continue
    return data


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _faster(before: float, now: float) -> bool:
    return before - now >= max(before * BETTER_SHARE, BETTER_SECONDS)


def _latency_pairs(now: dict, before: dict, now_min: int):
    """(Zeichen, jetzt, vorher) mit genug Werten bei vergleichbarem
    Zeichentempo (± LATENCY_WPM_SPREAD)."""
    for char, by_wpm in now.items():
        for wpm, values in by_wpm.items():
            earlier = [v for w, vs in before.get(char, {}).items() if abs(w - wpm) <= LATENCY_WPM_SPREAD for v in vs]
            if len(values) >= now_min and len(earlier) >= LATENCY_WEEK_MIN:
                yield char, values, earlier


def _latency_gains(now: dict, before: dict, now_min: int) -> list:
    """Zeichen, die schneller kamen: [{"kind": "latency", "char", "before",
    "now"}], je Zeichen einmal, größte Verbesserung zuerst. Ein Median von
    unendlich (mehr als die Hälfte verpasst) wird nicht verglichen."""
    gains = {}
    for char, values, earlier in _latency_pairs(now, before, now_min):
        old, new = _median(earlier), _median(values)
        if math.isfinite(old) and math.isfinite(new) and _faster(old, new):
            gain = {"kind": "latency", "char": char, "before": round(old, 2), "now": round(new, 2)}
            if char not in gains or new - old < gains[char]["now"] - gains[char]["before"]:
                gains[char] = gain
    return sorted(gains.values(), key=lambda g: (g["now"] - g["before"], g["char"]))


def char_moments(today: date) -> list:
    """Für die Zwischenkarte: Zeichen, die heute deutlich schneller kommen
    als in den sieben Tagen davor („R sitzt jetzt: 0,41 s“)."""
    now = latencies(today, today)
    before = latencies(date.fromordinal(today.toordinal() - WEEK_DAYS), date.fromordinal(today.toordinal() - 1))
    return _latency_gains(now, before, LATENCY_TODAY_MIN)[:MOMENTS_SHOWN]


def week_comparison(today: date) -> dict:
    """Diese Woche (heute und sechs Tage davor) gegen die Woche davor:
    {"status": BETTER/HELD/FEW, "better": [...]}; Einträge wie in
    _latency_gains oder {"kind": "groups", "wpm", "before", "now"} (Anteile)."""
    day = today.toordinal()
    this_week = (date.fromordinal(day - WEEK_DAYS + 1), today)
    last_week = (date.fromordinal(day - 2 * WEEK_DAYS + 1), date.fromordinal(day - WEEK_DAYS))
    now, before = latencies(*this_week), latencies(*last_week)
    compared = any(True for _ in _latency_pairs(now, before, LATENCY_WEEK_MIN))
    better = _latency_gains(now, before, LATENCY_WEEK_MIN)
    groups_now, groups_before = group_shares(*this_week), group_shares(*last_week)
    for wpm in sorted(groups_now, reverse=True):
        (new_ok, new_total), (old_ok, old_total) = groups_now[wpm], groups_before.get(wpm, (0, 0))
        if new_total < GROUPS_WEEK_MIN_CHARS or old_total < GROUPS_WEEK_MIN_CHARS:
            continue
        compared = True
        old, new = old_ok / old_total, new_ok / new_total
        if new - old >= GROUPS_BETTER_POINTS:
            better.insert(0, {"kind": "groups", "wpm": wpm, "before": round(old, 3), "now": round(new, 3)})
    status = BETTER if better else HELD if compared else FEW
    return {"status": status, "better": better[:BETTER_SHOWN]}


def block_summary(block: Block, result: dict, due: str = "") -> dict:
    """Zahlen für die Zwischenkarte: richtig/gesamt (Hauptteil beim ersten
    Versuch), beste Serie und beim Aufwärmen die geübten fälligen Zeichen
    und wie viele davon heute sicher saßen (wie die Lernkartei: genug
    Versuche, fast alle flüssig)."""
    correct, total = _first_try(result) if block.kind == MAIN else (result.get("correct", 0), result.get("total", 0))
    summary = {"kind": block.kind, "mode": block.mode, "correct": correct, "total": total,
               "streak": result.get("best_streak", 0)}
    if block.kind == WARMUP and due:
        chars = result.get("chars", {})
        practiced = [ch for ch in due if ch in chars]
        sure = [ch for ch in practiced
                if chars[ch][0] >= review.MIN_ATTEMPTS and chars[ch][1] / chars[ch][0] >= review.SURE_SHARE]
        summary.update(due_practiced=len(practiced), due_sure=len(sure))
    return summary


def _main_result(entry: dict):
    """Ergebnis des letzten Hauptteils des Tages, sonst None."""
    mains = [b for b in entry.get("blocks", []) if isinstance(b, dict) and b.get("kind") == MAIN]
    return mains[-1] if mains else None


def lesson_outlook(state: dict, today: date):
    """„Fast geschafft“: {"lesson", "pending": True} wenn der Aufstieg
    vorgemerkt ist, sonst {"lesson", "missing": Prozentpunkte} bis zum
    Koch-Kriterium im heutigen Hauptteil; None nach Koch oder ohne genug
    Zeichen."""
    lesson = current_lesson(state, 1)
    if state.get("pending_lesson"):
        return {"lesson": state["pending_lesson"], "pending": True}
    main = _main_result(state.get("days", {}).get(today.isoformat(), {}))
    if lesson >= POST_KOCH or main is None:
        return None
    correct, total = _first_try(main)
    if total < CLEAN_MIN_CHARS:
        return None
    missing = max(round(koch.ADVANCE_ACCURACY_PCT - correct / total * 100), 1)
    return {"lesson": lesson + 1, "missing": missing}


def extra_offer(state: dict, today: date, lesson: int, confusion_chars: str):
    """„Noch 5 Min“: (Art, Zeichensatz) oder None. Nur einmal am Tag und nur,
    wenn der Hauptteil heute mindestens EXTRA_MIN_SHARE hatte; Inhalt
    anders als heute: die häufigsten Verwechslungen, sonst ein
    Rufz-Durchgang, sonst Wörter."""
    entry = state.get("days", {}).get(today.isoformat(), {})
    main = _main_result(entry)
    if entry.get(EXTRA) or main is None:
        return None
    correct, total = _first_try(main)
    if not total or correct / total < EXTRA_MIN_SHARE:
        return None
    if len(confusion_chars) >= 2:
        return CONFUSIONS, confusion_chars
    if lesson >= RUFZ_FROM_LESSON:
        return RUFZ, ""
    if lesson >= WORDS_FROM_LESSON:
        return WORD, ""
    return None
