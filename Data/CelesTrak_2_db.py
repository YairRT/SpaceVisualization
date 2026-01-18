import sqlite3
from datetime import datetime, timezone
import httpx

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
DB_PATH = "tles.sqlite3"
GROUP = "active"  # change e.g. "stations", "starlink", etc.


def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS latest_tles (
                    norad_cat_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    line1 TEXT NOT NULL,
                    line2 TEXT NOT NULL,
                    fetched_at_utc TEXT NOT NULL
                    );""")
        con.commit()

def fetch_3le(group: str) -> str:
    params = {'GROUP': group, 'FORMAT': '3LE'}
    r = httpx.get(CELESTRAK_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text

def parse_3le(text: str):
    # Now we get (norad_id, name, line1, line2) of the TLE info to use later in SGP4 
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i in range(0, len(lines)-2, 3):
        name, line1, line2 = lines[i], lines[i+1], lines[i+2]
        if not (line1.startswith('1') and line2.startswith('2')):
            continue
        try:
            norad = int(line1[2:7])
        except ValueError:
            continue
        yield norad, name, line1, line2

def upsert_latest(records, fetched_at_utc: str):

    with sqlite3.connect(DB_PATH) as con:
        con.executemany(
        """
        INSERT INTO latest_tles (norad_cat_id, name, line1, line2, fetched_at_utc)
        VALUES (?,?,?,?,?)
        ON CONFLICT(norad_cat_id) DO UPDATE SET
        name=excluded.name,
        line1=excluded.line1,
        line2=excluded.line2,
        fetched_at_utc=excluded.fetched_at_utc;
        """,
        [(norad, name,l1,l2,fetched_at_utc) for (norad, name, l1, l2) in records],)

        con.commit()


def main():
    init_db()
    fetched_at = datetime.now(timezone.utc).isoformat()
    
    text = fetch_3le(GROUP)
    records = list(parse_3le(text=text))
    upsert_latest(records=records, fetched_at_utc=fetched_at)

    print(f'Upserted {len(records)} satellites into {DB_PATH} (table: latest_tles).')

if __name__ == '__main__':
    main()