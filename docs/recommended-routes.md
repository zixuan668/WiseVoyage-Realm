# Enriched Summer Palace recommendations

The eight curated routes live in `data/summer_palace_recommended_routes.json`. Each profile contains an ordered itinerary, an observation focus for every stop, three highlights, an audience description and practical advice in Chinese and English. They are project-authored suggestions based on the attraction material, not official published itineraries.

## Apply to an existing database

Start with the complete 16-attraction Summer Palace dataset. Run from the repository root:

```
.venv/Scripts/python.exe scripts/sync_recommended_routes.py
.venv/Scripts/python.exe scripts/sync_recommended_routes.py --apply
```

The first command previews measured distances and times. The second backs up existing route tables under `work_dirs/recommended-routes/`, updates matching preset names while keeping IDs, and adds missing presets. It does not update attractions, knowledge documents, digital guides or custom routes. Running it again does not duplicate presets. This is intentionally separate from the older six-attraction demo seed, which is not suitable for the complete dataset.

## Timing and presentation

The current content package contains the reviewed visit estimates for all 16 Summer Palace attractions. Import the package for a new deployment; later operator edits remain supported. Runtime planning includes walking, visits and breaks rather than a fixed attraction count.

Distances, per-leg walking times, stop durations, rest time and totals come from `route_overview` and the existing OSM pedestrian graph. No line-of-sight distances or boat shortcuts are used. Timings exclude admission, queues, entry/exit walking and live detours. The island branches explicitly require returning across the bridge. This content does not certify accessibility or live opening.

The public `/tour-session/routes` response contains concise bilingual editorial text, ordered stop focuses and geometry-free leg summaries. Full geometry remains in the existing itinerary overview endpoint. If an operator changes a route's name, city or stop order, it no longer receives mismatched curated prose. The visitor can inspect the detail drawer without changing their current selection, then apply its exact ordered stop IDs.

The existing automatic card carousel is retained. It pauses while a route detail drawer is open and restarts its interval after closing. The detail view includes all stops, walking segments, duration breakdown and practical advice. Card thumbnails use the already bundled attraction covers.

Selected-itinerary distance, total time and timing breakdown appear at the top of the sticky My itinerary panel beside the attraction cards. Route & timing opens the shared walking map and per-leg details in a drawer; the tour launch panel provides the same entry point. Closing the drawer preserves the selection and browsing position. The map at the top no longer repeats the timing block.
