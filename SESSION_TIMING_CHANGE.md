# Extension session discovery and timing

Requested on 2026-11-06. Implemented and verified as recorded in PLAN.md.

- Teachers run the video meeting in another tab and create a separate AreYouThere session entirely in the extension.
- Session creation collects a class name and generates the existing random join code.
- Signed-in students see a directory of lobby/live classes, select a class, and enter its code to join. The directory must not expose join codes, questions, answers, or member lists. The server must verify that the supplied code belongs to the selected class.
- Add class duration and question delivery settings to the extension create-session form: manual, fixed intervals, or random intervals within teacher-selected minimum and maximum bounds.
- Automatic delivery uses teacher-prepared questions in queue order. Random mode randomizes delivery timing. Timers and the next delivery timestamp persist in MySQL and are advanced by the existing scheduler, including after restart.
- Recovery is a delayed missed-response explanation, as clarified by the user. After the main answer deadline, wait the configured recovery delay, then automatically show a reason form to eligible students who did not answer. Accept reasons only until the recovery deadline. Review and excusing remain separate from answers and correctness. Existing sessions retain their previous unrestricted reason flow; newly created sessions configure the timed recovery flow.
- Proposed class duration behavior: countdown begins at Start session, with automatic end at its server deadline. Explicit teacher End closes the class immediately. Describe this in the creation form.
- Maintain all existing ownership, duplicate-answer, eligibility, privacy, grading, and reporting rules. A student's eligibility must not be inferred from meeting-tab activity.

The automatic reason prompt appears while the student panel is open and recovers from server timestamps after refresh. A closed side panel is not automatically opened. Existing background question polling remains unchanged; exact OS notification timing for recovery is not provided.
