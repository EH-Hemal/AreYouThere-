# AreYouThere?

A camera-free class participation system: React + TypeScript teacher dashboard, a teacher-and-student Manifest V3 extension, Django REST Framework + Channels, real MySQL storage, Redis delivery, and a persistent database scheduler.

## Your local setup

This computer already had MySQL 8.0.44, Python 3.13, Node 22, Chrome, Edge and VS Code. The original MySQL administrator password was unavailable. This project therefore reuses the **installed MySQL binaries** with an isolated data directory on **127.0.0.1:3307**. Your existing MySQL80 service on port 3306, its accounts, and its databases are unchanged. No old password was recovered or reset.

MySQL's optional allocator crashed the standalone instance on this Windows build. The project uses local copies of its executable and required DLLs, omitting the optional `jemalloc.dll` so MySQL uses its standard allocator. The installed files were not changed. This follows the allocator fallback described in [MySQL’s bug tracker](https://bugs.mysql.com/bug.php?id=108985).

The separate application database is `areyouthere`. Automated verification uses `test_areyouthere`. Database credentials and Django's secret are generated locally in ignored `.env`. Isolated instance administrator credentials are in ignored `.runtime/mysql-local.json`. Keep `.env`, `.runtime` and `.tools` private and out of source control.

Redis delivery uses project-local **Memurai Developer 4.1.2**, the native Windows compatibility option referenced by [Redis documentation](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-windows/). Its vendor MSI was verified against SHA-256 `11d009c8e93912e1899b5263d0e7d78907903913e1672b30020612ada6d27446` and extracted locally without installing a service. It listens only on loopback port 6379. Developer edition is for development, prohibits production use, and stops after ten days; relaunch it for local development. Use official Redis on the production server.

## Open the project

- Double-click **Launch.cmd**. It starts the local database and Redis when needed, applies migrations, and launches the backend, scheduler, and dashboard. A small control window opens the dashboard for you.
- Dashboard: [http://127.0.0.1:5173](http://127.0.0.1:5173).
- Your generated administrator login is in **.runtime/admin-login.txt**. The launcher has a button to open this private file. It can manage accounts in Django admin. Teacher and student registration both work immediately without administrator approval.
- Double-click **Stop.cmd** to stop the project's dashboard, backend, and scheduler. MySQL/Redis stay running so data is safe; they bind only to this computer. No system MySQL service is stopped.
- **Setup.cmd** repeats dependency installation and local configuration if dependencies have been removed. Normal use only needs Launch.cmd.

Do not launch a second backend while the verification backend is using port 8000. The final delivered workspace runs the real `areyouthere` database. See PLAN.md for evidence.

## Teacher and student Chrome extension

The ready-to-load extension is **dist/extension**. The ZIP for distribution is **dist/areyouthere-extension.zip**. Chrome requires the user to authorize loading an unpacked local extension:

1. Open `chrome://extensions` in Chrome.
2. Enable Developer mode, select **Load unpacked**, and choose this project's **dist/extension** folder.
3. Pin AreYouThere?, then click its icon to open the side panel.
4. Sign in or create an account as **Teacher** or **Student**. Teachers can create and start sessions, share codes, prepare and send questions, watch participation, review reasons, grade short answers, and export reports directly in the side panel. Students enter the session's six-character code and answer there. Keep the student panel open for immediate questions and connection heartbeats.

For two separate Chrome profiles, install the unpacked extension in each profile. The teacher can use the extension alone; the dashboard is an optional roomier view of the same MySQL-backed class. When the unpacked extension's files change, click **Reload** on its card at `chrome://extensions` in each profile to use the latest build.

The extension has no content scripts and cannot read class pages. Its permissions are storage, alarms, notifications, sidePanel, and the configured API host. While the panel is closed, its MV3 alarm checks approximately every 30 seconds and updates the icon badge and a notification for new questions. Very short questions can finish between background checks; keep the side panel open during class. Chrome controls notification availability and alarm timing.

The actual packaged MV3 extension was tested with installed Microsoft Edge's Chromium extension runtime, including a teacher-hosted question and student answer. The dashboard was tested with installed Google Chrome. On 2026-10-22, the extension was loaded into your normal Chrome profile through its extension manager, with your requested folder selection. It is enabled and pinned. Chrome's command-line extension loading is disabled in the installed branded version; the steps above apply when installing in another profile or computer.

## Classroom workflow

Register as a teacher in the extension or dashboard and create a session immediately. Share its code and let students join the lobby. Start the session, add MCQ or short-answer questions, and send them now or choose a future local delivery time. Only the teacher who owns the class can control or export it. Existing teacher accounts that previously waited for approval can also host immediately after updating.

Each question has a server-controlled deadline and one immutable answer per eligible student. Incorrect answers still count as participation. Short answers can be graded from the student's detail dialog. Questions closed before a student joined are excluded from their eligibility. Students can explain eligible missed responses; teachers excuse or reject reasons with an optional note. Excusing a miss preserves the original miss and records the excuse separately.

The live table supports search, connection filters and review filters. Student views include their own session history. Session reports and formula-safe CSV exports preserve participation, correctness, connection freshness, and reason reviews separately.

## Architecture and recovery

`backend/core/services.py` holds transitions and snapshot calculations. Writers acquire a MySQL session row lock before question transitions and submissions. A database uniqueness constraint also prevents duplicate answers. The scheduler polls MySQL every second, claims due work under that same lock, closes expired questions, and safely resumes after a restart. Overlapping scheduled questions wait in order. A session must be live for delivery.

Channels uses Redis for cross-process invalidation events. Clients fetch authorized snapshots over REST on connect, refresh, reconnect, and at eight-second fallback intervals. Sockets use short-lived signed authorization tickets. A 15-second heartbeat updates connection freshness; it expires after 45 seconds. Background extension polling does not pretend the student's panel is connected. API tokens expire after seven days. Sign-out revokes the account's token on all devices.

No camera, microphone, browsing history, page content or screen recording is collected. Only class account/membership data, responses, optional missed-response reasons and heartbeat timestamps are stored.

## Development and verification

The project includes backend tests for access control, deadlines, duplicate submission, eligibility, reasons, grading, CSV safety, persistent scheduling, and socket reconnect. Browser tests drive the actual extension and dashboard against **test_areyouthere**. Test records never populate the real application database. `seed_demo` is an explicit, separate management command and is never part of setup or launch.

For developers, `npm run build` checks TypeScript, builds both interfaces, and packages the extension. `.venv/Scripts/python backend/manage.py test core --keepdb --noinput` runs MySQL-backed backend tests. Browser verification is orchestrated by `scripts/verify.py` or **Verify.cmd**. Screenshots and actual results are summarized in PLAN.md. See SPEC.md and DESIGN.md for rules and interface decisions. See DEPLOYMENT.md for production configuration.

The build helper limits native worker concurrency and defaults Node's heap to 512 MB, which avoids the memory-allocation failures observed on this computer. These limits apply only to the build process and do not change Windows settings.
#   A r e Y o u T h e r e -  
 