# AreYouThere? development rules

Use Python/Django REST Framework + Channels, MySQL database `areyouthere`, Redis, and React/TypeScript. Do not touch unrelated databases. Keep secrets and runtime files out of Git. Use server timestamps and transactions for session/question transitions and submissions. Never infer participation from connectivity or correctness. A learner is eligible only for questions still open after they joined. Never collect camera, microphone, browser history, or screen content.

Run backend tests against a separate `test_areyouthere` database, frontend typecheck/build, and browser/extension checks when available. Record actual evidence and blockers in PLAN.md. Demo records must be created only by the explicit seed_demo command. Do not claim a check passed when its infrastructure is unavailable.
