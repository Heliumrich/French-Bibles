#!/usr/bin/env python3
"""
Remplace les espaces avant : ; ! ? par des espaces insécables
dans toute la table verses.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path("bible.db")

def fix_text(text: str) -> str:
    if not text:
        return text
    # Espace + signe double → espace insécable + signe
    text = re.sub(r" +([:;!?])", "\u00A0\\1", text)
    # Optionnel : aussi pour les guillemets français si tu en as
    text = re.sub(r"« +", "«\u00A0", text)
    text = re.sub(r" +»", "\u00A0»", text)
    return text

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT translation_id, book, chapter, verse, text FROM verses")
    rows = cur.fetchall()

    updated = 0
    for tid, book, chapter, verse, text in rows:
        new_text = fix_text(text)
        if new_text != text:
            cur.execute("""
                UPDATE verses
                SET text = ?
                WHERE translation_id = ? AND book = ? AND chapter = ? AND verse = ?
            """, (new_text, tid, book, chapter, verse))
            updated += 1

    conn.commit()
    conn.close()
    print(f"✓ {updated} versets corrigés")

if __name__ == "__main__":
    main()