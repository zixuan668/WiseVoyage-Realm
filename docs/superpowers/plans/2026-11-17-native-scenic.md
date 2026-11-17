# App native scenic catalog implementation plan

Goal: Replace the App scenic web-view with native uni-app views while keeping real scenic content, audio, server-backed itinerary selection and native guide/tour flow.
Architecture: The scenic page uses packaged images plus a short public API cache; its selection/settings are stored in existing database tables under the authenticated account. Existing RouteTiming and tour-guide pages provide verified route calculations and guide/session creation.
Constraints: No fabricated records or client-only saved states; exclude campus locations; no desktop browser previews; discard responses after account/service switches.

- [x] Add authenticated draft ownership and native scenic API/cache helpers; test account isolation and server writes.
- [x] Replace scenic.vue web-view and message bridge with native detail/catalog/audio/plan views; test loading and late audio/page responses.
- [x] Connect native planning to existing guide selection, preserve route options and back navigation; prefetch public catalog from home.
- [x] Remove this session's browser test script/logs, verify native templates and targeted tests without opening a browser.

Verification: native App compiler passed; native API/page/handoff tests and isolated database ownership/persistence tests passed. No browser preview or device run performed for the native migration. Existing route-map test harness still fails to evaluate an ESM import.
