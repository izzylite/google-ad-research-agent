# us-cities.json — Data Provenance

**Last regenerated:** 2026-05-14
**Schema:** `{state_code_lower: {city_name_lower: county_name_lower}}` — county values have NO ` county` suffix; the merge_signals filter strips that suffix from `geo_focus` inputs before lookup.
**Phase:** GEO-04 (Phase 11 plan 11-01)

## Sources

The file is composed from two open datasets, joined on `(city, state_code)`:

1. **Population subset** — `plotly/datasets/us-cities-top-1k.csv`
   <https://raw.githubusercontent.com/plotly/datasets/master/us-cities-top-1k.csv>
   Public-domain MIT-licensed Plotly dataset; provides the top 1000 US cities by 2010 Census population. Used as the priority core (these 1000 cities are always present in the JSON).

2. **County lookup** — `millbj92/US-Zip-Codes-JSON/USCities.json`
   <https://raw.githubusercontent.com/millbj92/US-Zip-Codes-JSON/master/USCities.json>
   MIT-licensed; ZIP-Code-derived `(city, state, county)` rows. For each `(city, state)` we keep the dominant county (the one appearing in the most ZIP records). Used to attach a `county` value to each city from source 1, and to pad the file with additional cities up to a ~5000-entry budget while staying under the 200KB size cap.

3. **Manual fixture-required entries** — added/overridden after the automated merge:
   - `tx/lake worth → tarrant` (Lake Worth, TX is a small city; not present in source 2's ZIP-derived data)
   - `ca/hollywood → los angeles` (Hollywood is a neighborhood of Los Angeles, not a separate municipality, so no ZIP record carries it as a city)
   - Spot-checks for the FL `*` set covered by the `us-cities-subset.json` test fixture: lake worth, boca raton, west palm beach, tampa, miami, jacksonville, hollywood.

## Coverage

| Statistic | Value |
|---|---|
| States | 50 + DC (51 total) |
| Cities | ~4800 |
| File size (minified JSON, sort_keys, comma-separator) | ~103 KB |

US territories (Puerto Rico, US Virgin Islands, Guam, American Samoa, Northern Mariana Islands, Federated States of Micronesia, Marshall Islands, Palau) are intentionally excluded — the GEO-03 filter targets US-state Google Ads runs and territories are out of scope for v1.2.

## Schema invariants

- All keys (state codes, city names) are lowercase ASCII.
- County values are lowercase ASCII, with NO trailing `" county"` suffix.
- City names preserve original spelling (no diacritics in source data; if added later, keep Unicode verbatim — the `merge_signals._keyword_drifts_city` filter uses lowercase substring match, which is Unicode-safe).
- Empty-county entries dropped — every value is non-empty.

## Regeneration

This file is data, not code — regenerate only when populations shift materially (Census decennial) or when the city set needs adjustment. The generator is not committed; the JSON itself is the canonical artifact.

To regenerate ad-hoc, fetch the two source URLs above, build `{state: {city: dominant_county}}`, then apply the manual entries listed in "Sources" item 3.
