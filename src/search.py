#!/usr/bin/env python3
"""
NI Directory - Alfred Script Filter
Searches Native Instruments Expansions by name or genre/style tags.

On first run, scans installed NI products and builds a local expansions.json.
Use 'nidr !refresh' to rescan installed products.
"""
import json
import os
import sys
import time
import glob

MAX_RECENTS = 5
RECENTS_FILE = "recents.json"
EXPANSIONS_FILE = "expansions.json"
TAGS_DB_FILE = "tags_database.json"
IGNORE_LIST_FILE = "ignore_list.json"
NI_PRODUCTS_DIR = "/Users/Shared/Native Instruments/installed_products"


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_json(filename):
    path = os.path.join(get_script_dir(), filename)
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(filename, data):
    path = os.path.join(get_script_dir(), filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def scan_installed_products():
    """Scan NI installed_products directory and build expansions.json."""
    tags_db = load_json(TAGS_DB_FILE)
    if tags_db is None:
        return None, "Could not load tags_database.json"

    if not os.path.isdir(NI_PRODUCTS_DIR):
        return None, f"NI products directory not found: {NI_PRODUCTS_DIR}"

    # Load ignore list (NI instruments/libraries that aren't expansions)
    ignore_data = load_json(IGNORE_LIST_FILE)
    ignore_set = set(ignore_data) if isinstance(ignore_data, list) else set()

    expansions = []
    untagged = []

    for filepath in sorted(glob.glob(os.path.join(NI_PRODUCTS_DIR, "*.json"))):
        name = os.path.splitext(os.path.basename(filepath))[0]

        # Skip ignored products (instruments, libraries, factory content)
        if name in ignore_set:
            continue

        # Check if this product is in our tags database
        if name in tags_db:
            entry = {"name": name, "tags": tags_db[name]["tags"]}
            if tags_db[name].get("type", "Maschine") != "Maschine":
                entry["type"] = tags_db[name]["type"]
            expansions.append(entry)
        else:
            # Check if it looks like an expansion (has ContentDir but no InstallDir)
            try:
                with open(filepath, "r") as f:
                    product_info = json.load(f)
                if "ContentDir" in product_info and "InstallDir" not in product_info:
                    # Likely an expansion we don't have tags for
                    untagged.append(name)
            except (json.JSONDecodeError, IOError):
                pass

    # Add untagged expansions with placeholder
    for name in untagged:
        expansions.append({
            "name": name,
            "tags": "(tags unavailable — submit a PR to add them!)"
        })

    save_json(EXPANSIONS_FILE, expansions)
    return expansions, f"Found {len(expansions)} expansions ({len(untagged)} untagged)"


def load_recents():
    data = load_json(RECENTS_FILE)
    return data if isinstance(data, list) else []


def save_recents(recents):
    save_json(RECENTS_FILE, recents[:MAX_RECENTS])


def update_recents(name):
    recents = load_recents()
    recents = [r for r in recents if r["name"] != name]
    recents.insert(0, {"name": name, "time": time.time()})
    save_recents(recents)


def make_item(exp, recent=False):
    exp_type = exp.get("type", "Maschine")
    prefix = "★ " if recent else ""
    return {
        "uid": exp["name"],
        "title": f"{prefix}{exp['name']}",
        "subtitle": f"[{exp_type}]  {exp['tags']}",
        "arg": exp["name"],
        "autocomplete": exp["name"],
        "icon": {"path": "icon.png"},
        "text": {
            "copy": exp["name"],
            "largetype": f"{exp['name']}\n[{exp_type}]\n\n{exp['tags']}"
        }
    }


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    # Special command: record a selection
    if query.startswith("__record__:"):
        name = query[len("__record__:"):]
        update_recents(name)
        print(name)
        return

    # Refresh command
    if query.strip().lower() == "!refresh":
        expansions, msg = scan_installed_products()
        if expansions is None:
            print(json.dumps({"items": [{"title": f"Error: {msg}", "valid": False}]}))
        else:
            print(json.dumps({"items": [{
                "title": f"✓ Refreshed! {msg}",
                "subtitle": "Your expansion list has been updated",
                "valid": False
            }]}))
        return

    # Load expansions (auto-setup on first run)
    expansions = load_json(EXPANSIONS_FILE)
    if expansions is None:
        expansions, msg = scan_installed_products()
        if expansions is None:
            print(json.dumps({"items": [{
                "title": "Setup failed",
                "subtitle": msg,
                "valid": False
            }]}))
            return

    query_lower = query.lower().strip()
    items = []

    if not query_lower:
        # Show recents first, then all expansions
        recents = load_recents()
        recent_names = {r["name"] for r in recents}
        exp_by_name = {e["name"]: e for e in expansions}

        for r in recents:
            if r["name"] in exp_by_name:
                items.append(make_item(exp_by_name[r["name"]], recent=True))

        for exp in expansions:
            if exp["name"] not in recent_names:
                items.append(make_item(exp))
    else:
        # Search mode
        terms = query_lower.split()
        for exp in expansions:
            searchable = f"{exp['name']} {exp['tags']} {exp.get('type', 'Maschine')}".lower()
            if all(term in searchable for term in terms):
                items.append(make_item(exp))

    if not items:
        items.append({
            "title": f"No results for '{query}'",
            "subtitle": "Try a different search term, or '!refresh' to rescan",
            "valid": False
        })

    print(json.dumps({"items": items}))


if __name__ == "__main__":
    main()
