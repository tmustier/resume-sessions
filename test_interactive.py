#!/usr/bin/env python3
"""
Manual test script for the interactive session selector.
Run this in a real terminal: uv run python test_interactive.py
"""

import sys

sys.path.insert(0, "src")

from resume_sessions import (
    find_pi_sessions,
    parse_session_file,
    project_name_to_path,
    load_titles_for_session,
    run_interactive_selector,
)


def main():
    print("Loading sessions...")
    sessions = find_pi_sessions()

    if not sessions:
        print("No sessions found!")
        return

    # Limit to 20 most recent
    sessions = sessions[:20]

    # Enrich with parsed data
    print(f"Parsing {len(sessions)} sessions...")
    for s in sessions:
        parsed = parse_session_file(s["path"])
        s.update(parsed)

    # Build titles map
    titles_map = {}
    for s in sessions:
        project_path = project_name_to_path(s["project"])
        titles = load_titles_for_session(s["id"], project_path)
        if titles:
            titles_map[s["id"]] = titles

    print(f"Found titles for {len(titles_map)} sessions")
    print()
    print("Starting interactive selector...")
    print("  ↑↓ to navigate")
    print("  / to search")
    print("  Enter to select")
    print("  q to quit")
    print()

    selected = run_interactive_selector(sessions, titles_map)

    if selected:
        print(f"\nSelected: {selected}")
        print(f"To resume: pi --resume {selected}")
    else:
        print("\nCancelled")


if __name__ == "__main__":
    main()
