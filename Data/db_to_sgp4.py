from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Iterable, List, Optional, Tuple

from sgp4.api import Satrec, jday

@dataclass
class TLERow:
    norad_cat_id: int
    name: str
    line1: str
    line2: str


@dataclass
class PropResult:
    norad_cat_id: int
    name: str
    t_utc: str
    r_km: Tuple[float, float, float] # position (x,y,z) in km
    v_km_s: Tuple[float, float, float] # velocity (vx,vy,vz) in km/s

 
def load_latest_tles(db_path: str, limit:int):

    sql_query = """
    SELECT norad_cat_id, name, line1, line2
    FROM latest_tles
    ORDER BY norad_cat_id 
    """

    if limit is not 0:
        sql_query += 'LIMIT ?'
    
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(sql_query, () if limit is 0 else (limit,))
        rows = cur.fetchmany()
    
    out: List[TLERow] = []

    for norad_cat_id, name, line1, line2 in rows:
        out.append(TLERow(norad_cat_id, name, line1.strip(), line2.strip()))        

    return out

def utc_time_into_future(minutes: int = 0):
    # Returns the current UTC time + minutes into the future
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def datetime_to_jday(dt_utc: datetime):
    # Convert datetime UTC --> (jd, fr) needed by sgp4

    return jday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute,
                dt_utc.minute + (dt_utc.microsecond/1e6))

def propagate_tles(tles: Iterable[TLERow], t_utc: datetime):
    jd, fr = datetime_to_jday(t_utc)
    results: List[PropResult] = []
    count_errors = 0

    for tle in tles:
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        e, r, v = sat.sgp4(jd, fr) # r: km, v: km/s

        if e != 0:
            # Here we could print the errors using another module (sgp4.api.SGP4_ERRORS)
            count_errors += 1
            continue
        
        current_satellite = PropResult(norad_cat_id=tle.norad_cat_id, name=tle.name,
                                       t_utc=t_utc.isoformat().replace("+00:00", "Z"),
                                       r_km=(float(r[0]),float(r[1]),float(r[2])),
                                       v_km_s=(float(v[0]),float(v[1]),float(v[2])))

        results.append(current_satellite)
    
    return results

if __name__ == '__main__':

    ap = argparse.ArgumentParser(description='Read TLEs from local DB and propagate them to SGP4 (r,v)')
    ap.add_argument('--db', default='tles.sqlite3', help='Path to DB')
    ap.add_argument('--limit', type=int, default=20, help='Amount of satellites to propagaet')
    ap.add_argument('--future_min', type=int, default=60,help='# of minutes into the future that we want to project')

    args = ap.parse_args()

    t_utc = utc_time_into_future(args.future_min)
    tles = load_latest_tles(args.db, args.limit)

    if not tles:
        raise SystemExit('No TLEs found in the DB')
    
    results = propagate_tles(tles=tles, t_utc=t_utc)

    print(f'Propageted {len(results)} satellites to time {t_utc.isoformat().replace("+00:00", "Z")}')

    print("Format: NORAD  NAME | r_km=(x,y,z) | v_km_s=(vx,vy,vz)  [TEME]")
    for res in results:
        print(
            f"{res.norad_cat_id:>6}  {res.name[:28]:<28} | "
            f"r_km=({res.r_km[0]: .3f},{res.r_km[1]: .3f},{res.r_km[2]: .3f}) | "
            f"v_km_s=({res.v_km_s[0]: .6f},{res.v_km_s[1]: .6f},{res.v_km_s[2]: .6f})"
        )
    

###
'''
Notes:
* Now the SGP4 data appears to be only reading the first line of the database and acting on it
        To do: Check why this is happening
    
* After this we could start visualizing things and we'll be done with the MVP
'''
