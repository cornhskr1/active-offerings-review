"""Reuse immutable date formatters without changing review date semantics."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = re.search(r'<script>([\s\S]*)</script>', (ROOT / 'index.html').read_text()).group(1).split('// interactions')[0]

class ReviewDateFormatterTests(unittest.TestCase):
    def test_equivalent_dates_and_bounded_formatter_construction(self):
        body = r'''
const assert=require('node:assert/strict');
const original={
 fmtDateTime(v){if(!v)return '—';try{return new Intl.DateTimeFormat('en-US',{timeZone:CT,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(new Date(v))}catch(_){return String(v)}},
 ctKey(v){if(/^\d{4}-\d{2}-\d{2}$/.test(String(v||'')))return String(v);try{const p=new Intl.DateTimeFormat('en-CA',{timeZone:CT,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(v));const g=t=>p.find(x=>x.type===t)?.value;return `${g('year')}-${g('month')}-${g('day')}`}catch(_){return ''}},
 prettyDay(key){const d=new Date(`${key}T12:00:00-05:00`);return new Intl.DateTimeFormat('en-US',{timeZone:CT,weekday:'short',month:'short',day:'numeric'}).format(d)},
 eventTime(v){if(/^\d{4}-\d{2}-\d{2}$/.test(String(v||'')))return 'DATE ONLY';if(!v)return 'TBA';if(/^\d{4}-\d{2}-\d{2}T\d{1,2}:/.test(v)&&!/[zZ]|[+-]\d\d:?\d\d$/.test(v)){return v.split('T')[1]||'TBA'}try{return new Intl.DateTimeFormat('en-US',{timeZone:CT,hour:'numeric',minute:'2-digit'}).format(new Date(v))}catch(_){return String(v).replace(/^.*T/,'')}}
};
const values=[null,undefined,'','invalid','2026-10-19','2026-10-19T13:45','2026-10-19T13:45:00Z','2026-10-19T13:45:00+09:00',
 '2026-03-08T07:59:59Z','2026-03-08T08:00:00Z','2026-11-01T06:59:59Z','2026-11-01T07:00:00Z',
 '2026-10-19T04:59:59Z','2026-10-19T05:00:00Z'];
for(let day=1;day<=28;day++)for(let month=1;month<=12;month++)values.push(`2026-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}T23:59:59Z`);
for(const value of values)for(const [name,fn]of Object.entries({fmtDateTime,ctKey,eventTime}))assert.equal(fn(value),original[name](value),`${name}: ${value}`);
for(const value of ['2026-03-08','2026-11-01','2026-10-19','2027-01-01'])assert.equal(prettyDay(value),original.prettyDay(value));
assert.throws(()=>prettyDay('invalid'),RangeError);
const Constructor=Intl.DateTimeFormat;let calls=0;
Intl.DateTimeFormat=function(...args){calls++;return new Constructor(...args)};
for(let i=0;i<1000;i++){ctKey('2026-10-19T04:59:59Z');fmtDateTime('2026-10-19T04:59:59Z');eventTime('2026-10-19T04:59:59Z');prettyDay('2026-10-19');}
Intl.DateTimeFormat=Constructor;assert.equal(calls,0,'Repeated review formatting must not recreate Intl formatters');
'''
        subprocess.run(['node'], input=SCRIPT+'\n'+body, text=True, cwd=ROOT, check=True)
