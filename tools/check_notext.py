"""1.6.0 no-text check (docs/PLAN_1.6.0.md section 4.4):   python tools/check_notext.py

Apart from the reeling minigame, Fishing Voyage shows no text on screen. This fails on:

  actionbar      setActionBar / setTitle / updateSubtitle in a script
  message        sendMessage in a script
  command        a title / titleraw / tellraw / say / msg / tell / w / me command (scripts, BP JSON, functions)
  form           ActionFormData / ModalFormData / MessageFormData in a script
  lore           setLore(...) whose literal text is anything but symbols (◆ ✿ ✦ ★, glyph characters,
                 spaces and § formatting codes), or a translated / rawtext line
  interact_text  an entity's interact button label
  nametag        a script giving an entity or item a literal name (a player's own name tag is fine)

The check is regex based: it reads literal text only (a variable's value is not followed).

KNOWN EXCEPTIONS
  PERMANENT  the reeling minigame and what belongs to it (section 4.2), plus game-shown text.
  TEMPORARY  text that 1.6.0 is still removing. When a step removes one, delete its line below: a temporary
             exception that no longer matches anything fails the check ("stale"), so the list stays honest.
             Step 15 of the plan ends with only PERMANENT entries left.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "Kaleidoscope Fishing Voyage [BP]")
SCRIPTS = os.path.join(BP, "scripts")

PERMANENT, TEMPORARY = "permanent", "temporary"
# (path under the BP, kind) -> (permanent | temporary, why)
EXCEPTIONS = {
    ("scripts/fishing/rod.js", "actionbar"): (PERMANENT, "reeling minigame: the track, the fish and the progress bar"),
    ("scripts/fishing/minigame.js", "actionbar"): (PERMANENT, "reeling minigame (section 4.2)"),
    ("scripts/fishing/minigameSwitch.js", "message"): (PERMANENT, "reply to an operator's /scriptevent kaleidoscope_fishing:minigame"),
    ("scripts/journal/settings.js", "form"): (PERMANENT, "journal settings page (minigame style, operator switch; 22.1 #8), if it moves to its own file"),
    ("entities/fishing_skiff.json", "interact_text"): (PERMANENT, "vanilla's own boat label (action.interact.ride.boat), as on every boat; without it touch screens may lose the board button"),
    ("scripts/journal/journal.js", "form"): (TEMPORARY, "journal pages (step 6); the settings page keeps text: move it to journal/settings.js, then delete this line"),
    ("scripts/journal/recipes.js", "form"): (TEMPORARY, "journal recipe pages (step 6)"),
    ("scripts/blocks/pond.js", "form"): (TEMPORARY, "fish pond list (step 8: hand net instead)"),
    ("scripts/tools/basket.js", "form"): (TEMPORARY, "fish creel list (step 7: glyph grid)"),
    ("scripts/tools/basket.js", "lore"): (TEMPORARY, "fish creel \"N / 64\" (step 7: five looks instead)"),
}

SYMBOLS = set(" ◆✿✦★●○×✔✘") | {chr(c) for c in range(0xE000, 0xF900)}


def lines_of(text, pos):
    return text.count("\n", 0, pos) + 1


def call_args(text, start):
    """The argument text of a call whose '(' is at text[start - 1] (strings and nesting respected)."""
    depth, q, i = 0, "", start
    while i < len(text):
        c = text[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = ""
        elif c in "\"'`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return text[start:i]
            depth -= 1
        i += 1
    return text[start:]


def literal_text(args):
    """The static text of every string / template literal in an argument list (template ${...} dropped)."""
    out = []
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', args, re.S):
        s = m.group(1) if m.group(1) is not None else m.group(2) if m.group(2) is not None else m.group(3)
        if m.group(3) is not None:
            s = re.sub(r"\$\{[^}]*\}", "", s)
        s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda u: chr(int(u.group(1), 16)), s)
        out.append(s)
    return out


def not_symbols(s):
    return re.sub(r"§.", "", s).strip(" ") and any(ch not in SYMBOLS for ch in re.sub(r"§.", "", s))


COMMAND = re.compile(r"""^\s*/?(title|titleraw|tellraw|say|msg|tell|w|me)\s""")


def scan_script(rel, text):
    found = []
    for m in re.finditer(r"\b(setActionBar|setTitle|updateSubtitle)\s*\(", text):
        found.append(("actionbar", lines_of(text, m.start()), m.group(1)))
    for m in re.finditer(r"\bsendMessage\s*\(", text):
        found.append(("message", lines_of(text, m.start()), "sendMessage"))
    for m in re.finditer(r"\b(ActionFormData|ModalFormData|MessageFormData)\b", text):
        found.append(("form", lines_of(text, m.start()), m.group(1)))
    for m in re.finditer(r"\brunCommand(?:Async)?\s*\(", text):
        for s in literal_text(call_args(text, m.end())):
            if COMMAND.match(s):
                found.append(("command", lines_of(text, m.start()), s.strip()[:40]))
    for m in re.finditer(r"\.setLore\s*\(", text):
        args = call_args(text, m.end())
        bad = [s for s in literal_text(args) if not_symbols(s)]
        if re.search(r"\b(translate|rawtext|text)\s*:", args):
            bad.append("translate/rawtext")
        if bad:
            found.append(("lore", lines_of(text, m.start()), ", ".join(repr(b) for b in bad)[:60]))
    for m in re.finditer(r"\.nameTag\s*=\s*(?=[\"'`{])", text):
        found.append(("nametag", lines_of(text, m.start()), text[m.end():m.end() + 30].split("\n")[0]))
    return found


def scan_json(rel, data):
    found = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "interact_text":
                    found.append(("interact_text", 0, f"{path}.{k} = {v}"))
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, str) and COMMAND.match(o):
            found.append(("command", 0, f"{path} = {o[:40]}"))
    walk(data, "")
    return found


def main():
    findings = []                                   # (rel, kind, line, what)
    for d, _, files in os.walk(SCRIPTS):
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, BP).replace(os.sep, "/")
            if not f.endswith(".js") or rel.startswith("scripts/data/"):
                continue                            # data/: generated tables (Cookery's guidebook text is its own book, 4.3)
            for kind, line, what in scan_script(rel, open(p, encoding="utf-8").read()):
                findings.append((rel, kind, line, what))
    for d, _, files in os.walk(BP):
        if os.path.relpath(d, BP).replace(os.sep, "/").startswith("scripts"):
            continue
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, BP).replace(os.sep, "/")
            if f.endswith(".json"):
                try:
                    data = json.loads(re.sub(r"(?m)^\s*//.*$", "", open(p, encoding="utf-8-sig").read()))
                except Exception:
                    continue
                for kind, line, what in scan_json(rel, data):
                    findings.append((rel, kind, line, what))
            elif f.endswith(".mcfunction"):
                for i, l in enumerate(open(p, encoding="utf-8"), 1):
                    if COMMAND.match(l):
                        findings.append((rel, "command", i, l.strip()[:40]))
    bad, used = [], set()
    for rel, kind, line, what in findings:
        if (rel, kind) in EXCEPTIONS:
            used.add((rel, kind))
        else:
            bad.append(f"NOTEXT {kind:13} {rel}{':' + str(line) if line else ''}  {what}")
    stale = [f"STALE  {kind:13} {rel}  (temporary exception no longer needed: delete it from EXCEPTIONS in tools/check_notext.py)"
             for (rel, kind), (life, _) in EXCEPTIONS.items() if life == TEMPORARY and (rel, kind) not in used]
    for l in bad + stale:
        print(l)
    temp = sorted(f"{r} ({k})" for (r, k), (life, _) in EXCEPTIONS.items() if life == TEMPORARY)
    if bad or stale:
        print(f"no-text check FAILED: {len(bad)} new text place(s), {len(stale)} stale exception(s). Text on screen is only "
              "allowed for the reeling minigame (docs/PLAN_1.6.0.md 4.2); show it with models, particles, sounds or glyphs.")
        sys.exit(1)
    print(f"no-text check passed: {len(findings)} known text place(s); {len(temp)} temporary exception(s) left: {', '.join(temp)}")


if __name__ == "__main__":
    main()
