#!/usr/bin/env python3
"""
Ajoute une traduction dans bible.db à partir d'un JSON.
- Une seule transaction (tout ou rien)
- En cas de UNIQUE, log le verset exact puis rollback complet
- Ne modifie jamais le JSON
"""

import json
import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path("bible.db")


def add_translation(json_path: Path, meta: dict):
    if not DB_PATH.exists():
        print("Erreur : bible.db n'existe pas. Lance d'abord create_bible_db.py")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        verses = json.load(f)

    print(f"Lecture : {json_path} ({len(verses)} entrées)")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO translations (
                code, name_short, name_full, authors, year, language,
                description, source_ot, source_nt, license, notes
            ) VALUES (
                :code, :name_short, :name_full, :authors, :year, :language,
                :description, :source_ot, :source_nt, :license, :notes
            )
        """, meta)
        translation_id = cur.lastrowid
        print(f"✓ Traduction {meta['code']} ajoutée (id={translation_id})")

        rows = []
        for i, v in enumerate(verses):
            rows.append((
                translation_id,
                v["book"],
                int(v["chapter"]),
                int(v["verse"]),
                v["text"],
            ))
            if (i + 1) % 5000 == 0:
                print(f"  ... préparé {i + 1} versets")

        try:
            cur.executemany(
                """
                INSERT INTO verses (translation_id, book, chapter, verse, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
        except sqlite3.IntegrityError:
            # Isoler le verset fautif (sans commit intermédiaire)
            conn.rollback()

            # Recréer la traduction après rollback
            cur.execute("""
                INSERT INTO translations (
                    code, name_short, name_full, authors, year, language,
                    description, source_ot, source_nt, license, notes
                ) VALUES (
                    :code, :name_short, :name_full, :authors, :year, :language,
                    :description, :source_ot, :source_nt, :license, :notes
                )
            """, meta)
            translation_id = cur.lastrowid

            for row in rows:
                row = (translation_id, row[1], row[2], row[3], row[4])
                try:
                    cur.execute(
                        """
                        INSERT INTO verses (translation_id, book, chapter, verse, text)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        row,
                    )
                except sqlite3.IntegrityError as e:
                    book, chapter, verse, text = row[1], row[2], row[3], row[4]
                    print()
                    print("=" * 60)
                    print("❌ UNIQUE constraint failed")
                    print(f"   translation_id = {translation_id}  (code={meta['code']})")
                    print(f"   book           = {book}")
                    print(f"   chapter        = {chapter}")
                    print(f"   verse          = {verse}")
                    print(f"   text (80 car.) = {text[:80]!r}...")
                    print(f"   sqlite         : {e}")
                    # Doublon déjà vu dans CE run (même transaction) ?
                    existing = cur.execute(
                        """
                        SELECT text FROM verses
                        WHERE translation_id=? AND book=? AND chapter=? AND verse=?
                        """,
                        (translation_id, book, chapter, verse),
                    ).fetchone()
                    if existing:
                        print(f"   déjà dans ce run = {existing[0][:80]!r}...")
                        print("   → doublon dans le JSON (même book/chapter/verse)")
                    else:
                        print("   déjà dans ce run = (non)")
                        print("   → conflit avec une autre ligne en base (autre translation_id ?)")
                    print("=" * 60)
                    conn.rollback()
                    raise

        conn.commit()
        print(f"✓ {len(rows)} versets importés pour {meta['code']}")

    except sqlite3.IntegrityError as e:
        if "translations" in str(e).lower() or "UNIQUE" in str(e):
            print(f"Import annulé (rollback) : {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Ajoute une traduction dans bible.db")
    parser.add_argument("json_file", help="Fichier JSON des versets")
    parser.add_argument("--code", required=True, help="Code court (ex: BDT, VUL, SAC)")
    parser.add_argument("--name-short", required=True)
    parser.add_argument("--name-full", required=True)
    parser.add_argument("--authors", default="")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--description", default="")
    parser.add_argument("--source-ot", default="")
    parser.add_argument("--source-nt", default="")
    parser.add_argument("--license", default="Domaine public")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    meta = {
        "code": args.code.upper(),
        "name_short": args.name_short,
        "name_full": args.name_full,
        "authors": args.authors,
        "year": args.year,
        "language": "fr" if args.code.upper() != "VUL" else "la",
        "description": args.description,
        "source_ot": args.source_ot,
        "source_nt": args.source_nt,
        "license": args.license,
        "notes": args.notes,
    }

    add_translation(Path(args.json_file), meta)


if __name__ == "__main__":
    main()