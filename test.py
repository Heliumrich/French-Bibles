python -c "
import sqlite3
c = sqlite3.connect('bible.db')
print('translations:', list(c.execute('SELECT id, code FROM translations')))
print('SAC verses:', c.execute('SELECT COUNT(*) FROM verses WHERE translation_id=(SELECT id FROM translations WHERE code=\"SAC\")').fetchone()[0])
"