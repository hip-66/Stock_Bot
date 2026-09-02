# מדריך הפייפליין האוטונומי — Stock Bot

> גרסה זו כתובה פעמיים: קודם בעברית, ואחר כך (למטה) באותו תוכן באנגלית.
> This document is written twice: first in Hebrew, then (below) the same content in English.

---

# חלק 1: עברית

## איך זה בנוי (חשוב להבין לפני שמשתמשים)

יש **שתי תיקיות** נפרדות על הדיסק, ושתי "גרסאות" (branches) בגיט:

```
Desktop\Projects\
├── Stock Bot\                          <- התיקייה החיה. run_bot.bat / check_bot.bat
│                                          פועלים כאן. תמיד על הענף main.
│                                          הסוכנים האוטונומיים אף פעם לא כותבים לכאן.
│
└── Stock_Bot_pipeline_workspace\       <- "ארגז החול" של הפייפליין. תמיד על הענף
                                           pipeline-dev. כל העבודה של הסוכנים קורית
                                           רק כאן.
```

שני התיקיות הן אותו repo של גיט (`git worktree`), אז יש להן היסטוריה משותפת, אבל הן שתי תיקיות פיזיות נפרדות לגמרי על הדיסק — קובץ שנכתב באחת לא מופיע אוטומטית בשנייה.

הרעיון: הסוכנים (רעיונות → בנייה → בדיקה → תיקון) עובדים כל הזמן ב-`Stock_Bot_pipeline_workspace`, ודוחפים כל שינוי לגיטהאב לענף `pipeline-dev`. שום דבר לא זז אוטומטית לענף `main` או לתיקייה `Stock Bot` (=הבוט שרואים בטלגרם). המעבר קורה רק כשאתה מריץ בעצמך את `approve_and_deploy.bat` (או דוחה עם `reject_and_reset.bat`).

`portfolio.json` (הנתונים הפיננסיים האמיתיים) הוצא לגמרי מהמעקב של גיט — שום פעולת merge/pull/reset לא יכולה לגעת בו או לדרוס אותו.

**בתוך `claude\` יש עוד חלוקה:** קבצים שאתה בפועל נוגע בהם (הסקריפטים, ה-config) יושבים ישירות בתיקייה. כל מה שהפייפליין **יוצר** בזמן ריצה (יומן, סטטוס, קובץ נעילה, המשימות של הסוכנים) יושב בתת-תיקייה `claude\state\` — כדי שהתיקייה הראשית תישאר נקייה ותציג רק דברים שרלוונטי לך לגעת בהם.

## "למה יש שני קבצים — run_pipeline.py ו-start_pipeline.bat, אם אני לא נוגע ב-run_pipeline.py?"

זה לא כפילות — זו הפרדה מכוונת בין **המנוע** ל**כפתור ההפעלה**:

- **`run_pipeline.py`** הוא כל הלוגיקה בפועל (הרצת 4 הסוכנים, קומיטים, push, בדיקת לו"ז, וכו'). הוא כתוב בפייתון כי צריך שם קוד אמיתי עם טיפול בשגיאות, JSON, תזמון — דברים שקובץ `.bat` לא יודע לעשות בצורה סבירה.
- **`start_pipeline.bat`** הוא רק "כפתור" — שתי שורות שפותחות חלון ומריצות את ה-Python. אתה נוגע בזה כי זה מה שמפעיל בפועל; אתה לא נוגע ב-`run_pipeline.py` כי זו הלוגיקה הפנימית — בדיוק כמו שאתה לוחץ על קיצור דרך של תוכנה ולא פותח את קובץ ה-exe שלה ידנית.

מיזוג שני הקבצים לאחד (להכניס את כל קוד הפייתון בתוך ה-bat) היה דווקא **פוגע** בסדר — batch לא תומך היטב בלוגיקה מורכבת, ואז כל שינוי עתידי (למשל הפיצ'ר של עצירה מתוזמנת שהוספתי עכשיו) היה הרבה יותר מסובך לכתוב ולתחזק. בדקתי את כל הקבצים בתיקייה — אין כרגע אף קובץ מיותר/לא בשימוש; כל קובץ שרשום בטבלה למטה נחוץ בפועל.

## כל הקבצים בתיקיית `claude` — מה כל אחד עושה ומתי להריץ אותו

| קובץ | סוג | מתי להריץ / מה זה |
|---|---|---|
| `CLAUDE.md` | הגדרות | חוקי התפקידים של 4 הסוכנים וכללי הבטיחות. הפייפליין קורא את זה בכל מחזור. עורכים את זה רק אם רוצים לשנות את ההתנהגות/הכללים של הסוכנים עצמם. |
| `run_pipeline.py` | מנוע | כל הלוגיקה. לא מריצים ישירות — ראו הסבר למעלה. |
| `start_pipeline.bat` | פעולה | **מפעיל את הפייפליין.** פותח חלון נפרד שרץ לנצח, כולל המתנה אוטומטית וחזרה כשנגמרים הטוקנים. |
| `stop_pipeline.bat` | פעולה | **עוצר את הפייפליין** (מיידית, גם באמצע עבודה של סוכן אם צריך). מומלץ להריץ לפני `approve_and_deploy.bat`/`reject_and_reset.bat`. |
| `continue_pipeline.bat` | פעולה | **ממשיך פייפליין שנעצר לבדיקה מתוזמנת** (ראו הסעיף הבא). לא עושה כלום אם הפייפליין לא במצב המתנה. |
| `review_changes.bat` | פעולה | פותח בדפדפן את עמוד ההשוואה בגיטהאב בין `main` ל-`pipeline-dev` — לקרוא שינויים לפני שמחליטים. |
| `approve_and_deploy.bat` | פעולה | ✅ **מאשרים ופורסים לפרודקשיין.** ממזג `pipeline-dev` ל-`main`, דוחף לגיטהאב, מעדכן את התיקייה החיה, ושואל בנפרד אם להפעיל מחדש את הבוט. |
| `reject_and_reset.bat` | פעולה | ❌ **דוחים ומאפסים.** מוחק לצמיתות את מה שב-`pipeline-dev` ומחזיר אותו למה שיש ב-`main`. לא נוגע בתיקייה החיה. |
| `.gitignore` | הגדרות | מתעלם מכל `claude/state/` — לא צריך לגעת. |
| `state\pipeline.log` | פלט (אוטומטי) | יומן מלא — לפתוח עם עורך טקסט לחקירה מעמיקה. |
| `state\pipeline_status.json` | פלט (אוטומטי) | תמונת מצב מהירה: מחזור נוכחי, שלב אחרון, עלות מצטברת. |
| `state\pipeline.pid` | פלט (אוטומטי) | קיים רק בזמן ריצה — מונע הפעלה כפולה. אם נשאר בטעות אחרי קריסה, פשוט מוחקים. |
| `state\next_task.md` | פלט (אוטומטי) | המשימה הבאה שסוכן 1 כתב לסוכן 2. נוצר מחדש כל מחזור. |
| `state\bugs_found.md` | פלט (אוטומטי) | הבאגים שסוכן 3 מצא לסוכן 4. נוצר מחדש כל מחזור. |
| `..\.env` (בתיקייה הראשית) | הגדרות סודיות | טוקן טלגרם ומפתח Gemini. לא בגיט. |

## עצירה מתוזמנת לבדיקה (Scheduled Review Pause)

**השאלה שהובילה לפיצ'ר הזה:** אם עוצרים את הפייפליין באמצע עבודה של סוכן, זה יכול לפגוע בקוד שהוא באמצע לכתוב? התשובה המלאה:

- **הבוט החי (`Stock Bot`) לעולם לא בסיכון**, לא משנה מתי עוצרים — הסוכנים כותבים אך ורק בתוך `Stock_Bot_pipeline_workspace`, לא בתיקייה החיה. זה נכון תמיד, גם אם עוצרים באמצע.
- אם עוצרים עם `stop_pipeline.bat` **באמצע** עבודה של סוכן, ה"ארגז חול" (`pipeline-dev`) עלול להישאר עם שינויים לא-commit-ים חצי גמורים. אין קומיט חדש עד שסוכן מסיים בהצלחה — כך שהכי גרוע שיכול לקרות זה בלגן זמני בענף הפיתוח, שאפשר תמיד לנקות עם `reject_and_reset.bat`.
- **הפיצ'ר החדש שהוספתי פותר את זה מהשורש:** במקום לעצור באופן ידני ובלתי-צפוי, אפשר להגדיר ימים ושעה קבועים שבהם הפייפליין עוצר **בעצמו**, אבל **רק בין מחזורים שלמים** — הוא אף פעם לא עוצר סוכן באמצע עבודה. כברירת מחדל: **כל יום ראשון וחמישי, מהשעה 09:00 הוא מפסיק להתחיל מחזורים חדשים, וברגע שהמחזור הנוכחי מסתיים ונשלח לגיטהאב — הוא נעצר ומחכה לך**, גם אם זה קורה קצת לפני 10:00 או קצת אחריה (תלוי כמה זמן לקח המחזור האחרון).
- כשזה קורה: הפייפליין שולח לך **הודעה בבוט הטלגרם האמיתי** (בלי להפעיל/לגעת בבוט עצמו — רק שולח הודעה עם הטוקן הקיים, אותו דבר כמו ששולח any-בוט הודעה) שאומרת שהוא ממתין לבדיקה שלך.
- כדי להחליט: `review_changes.bat` (לראות מה נבנה) ואז או `continue_pipeline.bat` (להמשיך) או `stop_pipeline.bat`/`reject_and_reset.bat` (לעצור/לדחות).
- אם לא תגיב בכלל — הוא פשוט **ממשיך לחכות** (לא ממשיך אוטומטית בלי שתאשר). זו ברירת המחדל הבטוחה.

### הגדרות (env vars, לא חובה לגעת)

| משתנה | ברירת מחדל | מה הוא עושה |
|---|---|---|
| `PIPELINE_PAUSE_ENABLED` | `1` (מופעל) | `0` כדי לכבות את העצירה המתוזמנת לגמרי. |
| `PIPELINE_PAUSE_DAYS` | `Sunday,Thursday` | באילו ימים (באנגלית, מופרד בפסיקים) לעצור. |
| `PIPELINE_PAUSE_HOUR` | `10` | שעת היעד (24 שעות, לפי השעון המקומי). |
| `PIPELINE_PAUSE_LEAD_MINUTES` | `60` | כמה דקות לפני השעה להפסיק להתחיל מחזורים חדשים. |

## תרחישי שימוש

### תרחיש 1: הפעלה ראשונה (חד-פעמי)
1. ודא שביצעת את ההתחברות החד-פעמית לגיטהאב (`git push -u origin main` ו-`git push -u origin pipeline-dev`).
2. לחיצה כפולה על `start_pipeline.bat`.
3. משאירים את החלון פתוח ברקע.

### תרחיש 2: בדיקת התקדמות תוך כדי ריצה
1. `state\pipeline_status.json` — מחזור נוכחי, עלות.
2. לפרטים מלאים: `state\pipeline.log`.
3. לראות מה נבנה: `review_changes.bat`.

### תרחיש 3: אהבתי את מה שהסוכנים בנו — רוצה שזה יעלה לבוט האמיתי
1. (מומלץ) `stop_pipeline.bat`.
2. `review_changes.bat`.
3. `approve_and_deploy.bat` → "y" למיזוג → "y" להפעלה מחדש.
4. בודקים בטלגרם.
5. `start_pipeline.bat` שוב אם רוצים להמשיך.

### תרחיש 4: לא אהבתי — רוצה למחוק ולתת לו לנסות שוב
1. (מומלץ) `stop_pipeline.bat`.
2. `reject_and_reset.bat` → "y".
3. הבוט החי לא נגע בכלל.
4. `start_pipeline.bat` שוב.

### תרחיש 5: לבדוק את הקוד לוקאלית בלי להשפיע על הבוט האמיתי
1. פותחים את `Stock_Bot_pipeline_workspace` (לא `Stock Bot`!).
2. אם רוצים להריץ את `bot.py` בפועל משם — טוקן טלגרם **נפרד לבדיקות** בלבד.

### תרחיש 6: משהו נראה תקוע
1. `state\pipeline.pid` קיים אבל אין חלון פתוח — קרס. מוחקים את הקובץ, מריצים `start_pipeline.bat`.
2. `state\pipeline_status.json`/`state\pipeline.log` תמיד יגידו איפה זה נעצר.

### תרחיש 7: קיבלת הודעה בטלגרם "⏸️ הפייפליין עצר לבדיקה"
1. `review_changes.bat` — לראות מה נבנה מאז הבדיקה הקודמת.
2. אם טוב: `approve_and_deploy.bat`, ואז `continue_pipeline.bat` כדי שימשיך לעבוד על הבא בתור.
3. אם לא: `reject_and_reset.bat`, ואז `continue_pipeline.bat`.
4. אם פשוט צריך עוד זמן לבדוק: לא עושים כלום — הוא ימתין בסבלנות.

## תקלות נפוצות

- **"git is not recognized"** — טרמינל ישן. `$env:PATH = "C:\Program Files\Git\cmd;$env:PATH"` פעם אחת ב-PowerShell (לא רלוונטי ב-cmd אם git כבר עובד שם).
- **push protection על סודות** — אם GitHub חוסם push בגלל "secrets found", זה סימן שמשהו רגיש נכנס להיסטוריה. אל תלחצו על "allow secret" בקישור של גיטהאב — זה חושף את הסוד לצמיתות. תגידו לי ואני אנקה את ההיסטוריה.
- **הבוט לא מגיב אחרי deploy** — בדקו ב-Task Manager אם `python.exe` רץ, או `check_bot.bat`.

---

# Part 2: English

## How this is built (important to understand before using it)

There are **two separate folders** on disk, and two git branches:

```
Desktop\Projects\
├── Stock Bot\                          <- The LIVE folder. run_bot.bat / check_bot.bat
│                                          run from here. Always on the `main` branch.
│                                          The autonomous agents never write here.
│
└── Stock_Bot_pipeline_workspace\       <- The pipeline's sandbox. Always on the
                                           `pipeline-dev` branch. All agent work
                                           happens only here.
```

Both folders are the same git repo (`git worktree`), so they share history, but they are two completely separate physical folders on disk — a file written in one does not automatically appear in the other.

The idea: the agents (ideas → build → test → fix) work continuously inside `Stock_Bot_pipeline_workspace`, pushing every change to GitHub on the `pipeline-dev` branch. Nothing ever moves automatically to the `main` branch or to the `Stock Bot` folder (= the bot you see on Telegram). Promotion only happens when you personally run `approve_and_deploy.bat` (or reject with `reject_and_reset.bat`).

`portfolio.json` (your real financial data) has been fully removed from git tracking — no merge/pull/reset operation can touch or overwrite it.

**Inside `claude\` there's a further split:** files you actually interact with (scripts, config) sit directly in the folder. Everything the pipeline **generates** at runtime (log, status, lock file, the agents' hand-off tasks) lives in a `claude\state\` subfolder — so the main folder stays clean and only shows things relevant for you to touch.

## "Why are there two files — run_pipeline.py and start_pipeline.bat — if I don't touch run_pipeline.py?"

This isn't duplication — it's an intentional split between the **engine** and the **start button**:

- **`run_pipeline.py`** is all the actual logic (running the 4 agents, commits, push, schedule checking, etc.). It's written in Python because that logic needs real error handling, JSON, scheduling — things a `.bat` file can't reasonably do.
- **`start_pipeline.bat`** is just a "button" — two lines that open a window and run the Python. You touch this one because it's what actually launches things; you don't touch `run_pipeline.py` because it's the internal logic — the same way you click a program's shortcut rather than opening its .exe by hand.

Merging the two into one file (putting all the Python logic inside the .bat) would actually **hurt** the organization — batch doesn't handle complex logic well, and every future change (like the scheduled-pause feature just added) would have been much harder to write and maintain. I reviewed every file in the folder — there is currently no unused/leftover file; everything in the table below is actually used.

## Every file in the `claude` folder — what it does and when to run it

| File | Type | When to run it / what it is |
|---|---|---|
| `CLAUDE.md` | Config | The 4 agents' role rules and safety rules. The pipeline reads this every cycle. Only edit this if you want to change the agents' own behavior/rules. |
| `run_pipeline.py` | Engine | All the logic. Don't run directly — see explanation above. |
| `start_pipeline.bat` | Action | **Starts the pipeline.** Opens a dedicated window that runs forever, including automatically waiting and retrying when usage limits are hit. |
| `stop_pipeline.bat` | Action | **Stops the pipeline** (immediately, even mid-agent if needed). Recommended before `approve_and_deploy.bat`/`reject_and_reset.bat`. |
| `continue_pipeline.bat` | Action | **Resumes a pipeline paused for scheduled review** (see next section). Does nothing if the pipeline isn't waiting. |
| `review_changes.bat` | Action | Opens the GitHub comparison page between `main` and `pipeline-dev` in your browser — read the changes before deciding. |
| `approve_and_deploy.bat` | Action | ✅ **Approve and deploy to production.** Merges `pipeline-dev` into `main`, pushes to GitHub, updates the live folder, and separately asks whether to restart the bot. |
| `reject_and_reset.bat` | Action | ❌ **Reject and reset.** Permanently discards what's on `pipeline-dev` and resets it to match `main`. Never touches the live folder. |
| `.gitignore` | Config | Ignores all of `claude/state/` — no need to touch this. |
| `state\pipeline.log` | Output (auto) | Full log — open with a text editor to dig deep. |
| `state\pipeline_status.json` | Output (auto) | Quick snapshot: current cycle, last stage, cumulative cost. |
| `state\pipeline.pid` | Output (auto) | Exists only while running — prevents double-starting. If left over after a crash, just delete it. |
| `state\next_task.md` | Output (auto) | The next task Agent 1 wrote for Agent 2. Regenerated every cycle. |
| `state\bugs_found.md` | Output (auto) | The bugs Agent 3 found for Agent 4. Regenerated every cycle. |
| `..\.env` (in the root folder) | Secret config | Telegram token and Gemini key. Not in git. |

## Scheduled Review Pause

**The question that led to this feature:** if you stop the pipeline mid-agent, can that damage the code it's in the middle of writing? Full answer:

- **The live bot (`Stock Bot`) is never at risk**, no matter when you stop — the agents only ever write inside `Stock_Bot_pipeline_workspace`, never the live folder. That's true always, even mid-stop.
- If you stop with `stop_pipeline.bat` **mid-agent**, the sandbox (`pipeline-dev`) can be left with half-finished, uncommitted changes. No new commit happens until an agent finishes successfully — so worst case is temporary mess on the dev branch, always cleanable with `reject_and_reset.bat`.
- **The new feature I added solves this at the root:** instead of stopping manually and unpredictably, you can set fixed days and a time at which the pipeline pauses **itself** — but **only between complete cycles**, never mid-agent. By default: **every Sunday and Thursday, starting at 09:00 it stops starting new cycles, and as soon as the current cycle finishes and is pushed to GitHub — it pauses and waits for you**, whether that lands slightly before or after 10:00 (depending how long the last cycle took).
- When that happens: the pipeline sends you a **message on the real Telegram bot** (without starting or touching the bot itself — it just sends a message using the existing token, same as any bot sending a message) saying it's waiting for your review.
- To decide: `review_changes.bat` (see what was built), then either `continue_pipeline.bat` (keep going) or `stop_pipeline.bat`/`reject_and_reset.bat` (stop/reject).
- If you don't respond at all — it simply **keeps waiting** (it does not auto-continue without your approval). That's the safe default.

### Settings (env vars, optional)

| Variable | Default | What it does |
|---|---|---|
| `PIPELINE_PAUSE_ENABLED` | `1` (on) | `0` to disable scheduled pausing entirely. |
| `PIPELINE_PAUSE_DAYS` | `Sunday,Thursday` | Which days (English, comma-separated) to pause on. |
| `PIPELINE_PAUSE_HOUR` | `10` | Target hour (24h, local time). |
| `PIPELINE_PAUSE_LEAD_MINUTES` | `60` | How many minutes before that hour to stop starting new cycles. |

## Usage scenarios

### Scenario 1: First-time setup (one-time)
1. Make sure you've done the one-time GitHub sign-in (`git push -u origin main` and `git push -u origin pipeline-dev`).
2. Double-click `start_pipeline.bat`.
3. Leave the window running in the background.

### Scenario 2: Checking progress while it's running
1. `state\pipeline_status.json` — current cycle, cost.
2. Full detail: `state\pipeline.log`.
3. See what was built: `review_changes.bat`.

### Scenario 3: I like what the agents built — I want it live on the real bot
1. (Recommended) `stop_pipeline.bat`.
2. `review_changes.bat`.
3. `approve_and_deploy.bat` → "y" to merge → "y" to restart.
4. Check on Telegram.
5. Run `start_pipeline.bat` again if you want it to keep going.

### Scenario 4: I don't like it — discard it and let it try again
1. (Recommended) `stop_pipeline.bat`.
2. `reject_and_reset.bat` → "y".
3. The live bot was never touched.
4. Run `start_pipeline.bat` again.

### Scenario 5: Testing the code locally without affecting the real bot
1. Open `Stock_Bot_pipeline_workspace` (not `Stock Bot`!).
2. To actually run `bot.py` from there — use a **separate test-only** Telegram token.

### Scenario 6: Something looks stuck
1. `state\pipeline.pid` exists but no window is open — it crashed. Delete the file, run `start_pipeline.bat`.
2. `state\pipeline_status.json`/`state\pipeline.log` always show where it last stopped.

### Scenario 7: You got a Telegram message "⏸️ Pipeline paused for review"
1. `review_changes.bat` — see what was built since the last check.
2. If good: `approve_and_deploy.bat`, then `continue_pipeline.bat` so it keeps going on the next thing.
3. If not: `reject_and_reset.bat`, then `continue_pipeline.bat`.
4. If you just need more time to review: do nothing — it will wait patiently.

## Common issues

- **"git is not recognized"** — an old terminal. Run `$env:PATH = "C:\Program Files\Git\cmd;$env:PATH"` once in PowerShell (not needed in cmd if git already works there).
- **Push protection on secrets** — if GitHub blocks a push saying "secrets found", something sensitive made it into history. Don't click "allow secret" on GitHub's link — that permanently exposes it. Tell me and I'll clean the history.
- **The bot doesn't respond after a deploy** — check Task Manager for `python.exe`, or `check_bot.bat`.
