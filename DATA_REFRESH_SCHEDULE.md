# Data Refresh Schedule

This is the default server refresh cadence for production. The UI "Last updated"
indicator reflects each view's own refresh interval.

- News (latest + weighted): every 5 minutes
- Macro indicators: every 5 minutes
- Market overview/pulse: every 2 minutes
- AI picks (top picks + sector picks): every 12 hours
- Quick wins + hidden gems: every 3 hours
- Smart alerts (program universe): every 15 minutes
- Premarket boost: weekdays at 09:15 ET for quick wins + hidden gems
- User-specific views (watchlist alerts, view analysis, manual scans): on-demand per user

Notes:
- Server refresh jobs run even when no users are online.
- Client requests still honor cache TTLs to avoid unnecessary API usage.
