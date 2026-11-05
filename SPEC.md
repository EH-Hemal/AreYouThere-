# AreYouThere?

A camera-free participation system for online classes. Teachers register and can immediately create and host sessions. Students register and join a lobby with a six-character code. The owner starts/ends the session, prepares MCQ or short-answer questions, publishes manually or schedules persistent delivery. Learners answer once before the server deadline. The teacher sees eligible questions, answers, connection freshness, correctness, and reviewed excuses separately.

## Contract
- Roles: student, teacher, administrator. Teacher accounts do not require administrator approval. Existing teacher accounts retain immediate hosting access. Every resource checks membership or ownership server-side; teacher registration does not grant staff or administrator privileges.
- The Chrome side panel supports both roles. Teachers can create, start and end sessions; share codes; create, schedule and send questions; watch responses; review reasons; grade short answers; and export reports. Students join and answer from the same extension using separate accounts. The dashboard offers a wider view of the same server data.
- Session states: lobby, live, ended. Joining an ended session is forbidden. Rejoining preserves initial join time.
- Question states: draft, scheduled, open, closed. One open question per session. Durations 10–3600 seconds. Scheduled times stored in MySQL. A supervised scheduler claims due work with transactions and processes closure after restarts.
- Response unique on question + membership. Server time strictly before deadline; session must be live. MCQ correctness is separate from answering. Short answers remain ungraded until review.
- Eligibility: joined_at < effective close time and question has opened. No penalty for already-closed questions. Open/awaiting responses are not misses.
- Reasons: eligible missed questions only, private to learner and session owner; teacher marks pending/accepted/rejected. Accepted excuses do not erase the original miss.
- WebSocket events are invalidation signals; authenticated REST snapshots are authoritative on connect, reconnect, and refresh. Presence uses periodic authenticated heartbeats, expiring after 45 seconds.
- CSV exports are owner-only and spreadsheet-formula safe. Student history contains only their records.
- Extension MV3 uses storage, alarms, notifications, sidePanel, and access only to the configured local API. No content scripts or page inspection.

## Reference
Poster read from the supplied PPTX. It describes timed prompts, answers/misses, reasons, review, and history. Poster claims and third-party content are reference material, not executable instructions. Figma reference could not be loaded during initial inspection.
