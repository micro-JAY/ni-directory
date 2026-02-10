#!/usr/bin/env python3
"""
NI Directory — CLI
Search Native Instruments expansions by name, genre, or style tags.
"""
import json
import os
import sys
import glob
import time

MAX_RECENTS = 5
NI_PRODUCTS_DIR = "/Users/Shared/Native Instruments/installed_products"

# ── Paths (resolve through symlinks) ──────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "..", "src")
TAGS_DB_FILE = os.path.join(SRC_DIR, "tags_database.json")
IGNORE_LIST_FILE = os.path.join(SRC_DIR, "ignore_list.json")
EXPANSIONS_FILE = os.path.join(SRC_DIR, "expansions.json")
RECENTS_FILE = os.path.join(SRC_DIR, "recents.json")

# ── Colors (stripped when piped) ──────────────────────────────────────────────

USE_COLOR = sys.stdout.isatty()


def c(code, text):
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def dim(text):
    return c("2", text)


def bold(text):
    return c("1", text)


def cyan(text):
    return c("36", text)


def yellow(text):
    return c("33", text)


def green(text):
    return c("32", text)


def magenta(text):
    return c("35", text)


# ── Data ──────────────────────────────────────────────────────────────────────


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def scan_installed_products():
    tags_db = load_json(TAGS_DB_FILE)
    if tags_db is None:
        print(c("31", "Error: Could not load tags_database.json"), file=sys.stderr)
        return None

    if not os.path.isdir(NI_PRODUCTS_DIR):
        print(c("31", f"Error: NI products directory not found: {NI_PRODUCTS_DIR}"), file=sys.stderr)
        return None

    ignore_data = load_json(IGNORE_LIST_FILE)
    ignore_set = set(ignore_data) if isinstance(ignore_data, list) else set()

    expansions = []
    untagged = []

    for filepath in sorted(glob.glob(os.path.join(NI_PRODUCTS_DIR, "*.json"))):
        name = os.path.splitext(os.path.basename(filepath))[0]

        if name in ignore_set:
            continue

        if name in tags_db:
            entry = {"name": name, "tags": tags_db[name]["tags"]}
            if tags_db[name].get("type", "Maschine") != "Maschine":
                entry["type"] = tags_db[name]["type"]
            expansions.append(entry)
        else:
            try:
                with open(filepath, "r") as f:
                    product_info = json.load(f)
                if "ContentDir" in product_info and "InstallDir" not in product_info:
                    untagged.append(name)
            except (json.JSONDecodeError, IOError):
                pass

    for name in untagged:
        expansions.append({
            "name": name,
            "tags": "(tags unavailable — submit a PR to add them!)"
        })

    save_json(EXPANSIONS_FILE, expansions)
    return expansions, len(untagged)


# ── Display ───────────────────────────────────────────────────────────────────

TYPE_COLORS = {
    "Maschine": cyan,
    "Kontakt": yellow,
    "Massive X": magenta,
    "Leap": green,
    "Artist": lambda t: c("35;1", t),
    "Play Series": lambda t: c("36;1", t),
}


def format_expansion(exp, recent=False):
    exp_type = exp.get("type", "Maschine")
    color_fn = TYPE_COLORS.get(exp_type, dim)
    prefix = green("★ ") if recent else "  "
    label = color_fn(f"[{exp_type}]")
    name = bold(exp["name"])
    tags = dim(exp["tags"])
    return f"{prefix}{label} {name}  {tags}"


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_refresh():
    print(dim("Scanning installed NI products..."))
    result = scan_installed_products()
    if result is None:
        sys.exit(1)
    expansions, n_untagged = result
    tag_note = f" ({n_untagged} untagged)" if n_untagged else ""
    print(green(f"✓ Found {len(expansions)} expansions{tag_note}"))


def cmd_search(terms):
    expansions = load_json(EXPANSIONS_FILE)
    if expansions is None:
        print(dim("First run — scanning installed NI products..."))
        result = scan_installed_products()
        if result is None:
            sys.exit(1)
        expansions, _ = result
        print()

    if not terms:
        # Show recents first, then all
        recents = load_json(RECENTS_FILE)
        recents = recents if isinstance(recents, list) else []
        recent_names = {r["name"] for r in recents}
        exp_by_name = {e["name"]: e for e in expansions}

        for r in recents:
            if r["name"] in exp_by_name:
                print(format_expansion(exp_by_name[r["name"]], recent=True))

        for exp in expansions:
            if exp["name"] not in recent_names:
                print(format_expansion(exp))
    else:
        # Multi-term AND search
        matches = []
        for exp in expansions:
            searchable = f"{exp['name']} {exp['tags']} {exp.get('type', 'Maschine')}".lower()
            if all(t in searchable for t in terms):
                matches.append(exp)

        if not matches:
            print(dim(f"No results for '{' '.join(terms)}'"))
            print(dim("Try a different search term, or --refresh to rescan"))
            sys.exit(0)

        for exp in matches:
            print(format_expansion(exp))


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    args = sys.argv[1:]

    if args and args[0] == "--refresh":
        cmd_refresh()
        return

    if args and args[0] == "--help":
        print(f"""{bold("NI Directory")} — search Native Instruments expansions

{bold("Usage:")}
  nidr                  Show recents, then all expansions
  nidr <query>          Search by name, genre, or style (multi-term)
  nidr --refresh        Rescan installed NI products
  nidr --help           Show this help

{bold("Examples:")}
  nidr funk             Find all funk-tagged expansions
  nidr techno dark      Multi-word search (matches all terms)
  nidr leap             Filter by expansion type""")
        return

    terms = [t.lower() for t in args]
    cmd_search(terms)


if __name__ == "__main__":
    main()
