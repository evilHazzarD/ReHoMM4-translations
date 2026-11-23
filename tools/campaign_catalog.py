"""Builds a catalog of the player-visible strings of a campaign file.

    campaign_catalog.py <language code> <X>     (X: e.g. Campaign.Chaos_Campaign)

reads build/<code>/extract/game_maps.X.h4d, writes build/<code>/catalog/X.json.

Keeps prose and titles (strings with a space), drops object-type keys
such as "mountains.Grass rough.17" (a dot followed by a non-space with no
sentence break). The campaign name and description in the header, and the
first string of each map (its name, which may be one word: "Rivals"), are
always kept, and so are the one-word names of the maps' towns and heroes
(shown_names), after the rest, as "names". Existing translations in the
catalog are preserved."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import campaign_text as ct  # noqa: E402
import lang as L  # noqa: E402


def visible(t):
    if ' ' not in t:
        return False
    if re.search(r'\.\S', t) and not re.search(r'[.!?]["\')]*\s', t):
        return False
    return True


def shown_names(buf, catalog=()):
    """One-word names of towns and heroes in a map's data, in order, that visible() drops: a town's
    name follows its record ("left"/"right" and 55 bytes); a hero's follows 01 09 00 .. 01 0A 00
    and 11 bytes, or its biography (a placeholder hero). A hero carried over from another
    campaign map (carryover_hero) is named only in the scripts, under its translated name.
    The scripts' other conditions (owns_town, has_hero...) name the same objects: the pack replaces
    a string everywhere in the file, so they keep matching. A name only in the scripts (a hero
    under its default name) is left as it is."""
    out = []
    strings = ct.strings(buf)
    for i in range(1, len(strings)):
        pos, s = strings[i]
        t = s.decode('cp1252', 'replace')
        if (t in catalog or t in out or not t[:1].isupper() or re.search(r'[\s._\\/]', t)
                or t[-1].isupper() or t.endswith(('Epi', 'Pro'))):  # voice-over clips: MongoA, WoWPro
            continue
        ppos, ps = strings[i - 1]
        prev, gap = ps.decode('cp1252', 'replace'), pos - (ppos + 2 + len(ps))
        if ((prev in ('left', 'right') and gap == 55)
                or (buf[pos - 20:pos - 17] == b'\x01\t\x00' and buf[pos - 14:pos - 11] == b'\x01\n\x00')
                or (gap == 0 and len(prev) > 40 and ' ' in prev)
                or prev == 'carryover_hero'):
            out.append(t)
    return out


def build(src, out):
    old = {}
    if os.path.exists(out):
        old = {e['en']: e.get(L.FIELD, '') for e in json.load(open(out, encoding='utf-8'))}
    items, seen, last = [], set(), None
    for k, r in enumerate(ct.extract(src)):
        t = r['en']
        part = r['part']
        if part == 'header':
            where = 'campaign name' if not items else 'campaign description'
            ok = len(t) > 1
        else:
            where = 'map %d' % (int(part[3:]) + 1)
            ok = (part != last and t.strip()) or visible(t)
        last = part
        if ok and t not in seen:
            seen.add(t)
            items.append({'id': len(items), 'where': where, 'en': t, L.FIELD: old.get(t, '')})
    b = open(src, 'rb').read()
    maps = [p[2] for p in ct.split_parts(b)[1:]] or [ct.gzip.decompress(b[31:])]  # the tutorial: one map
    for m in maps:
        for t in shown_names(m, seen):
            seen.add(t)
            items.append({'id': len(items), 'where': 'names', 'en': t, L.FIELD: old.get(t, '')})
    json.dump(items, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return items


if __name__ == '__main__':
    lg = L.Language(sys.argv[1])
    os.makedirs(lg.catalog, exist_ok=True)
    out = os.path.join(lg.catalog, sys.argv[2] + '.json')
    items = build(os.path.join(lg.extract, 'game_maps.' + sys.argv[2] + '.h4d'), out)
    print(f'{out}: {len(items)} strings, {sum(len(i["en"].split()) for i in items)} words')
