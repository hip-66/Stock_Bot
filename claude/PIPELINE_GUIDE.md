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

## כל הקבצים בתיקיית `claude` — מה כל אחד עושה ומתי להריץ אותו

| קובץ | סוג | מתי להריץ / מה זה |
|---|---|---|
| `CLAUDE.md` | הגדרות | חוקי התפקידים של 4 הסוכנים וכללי הבטיחות. הפייפליין קורא את זה בכל מחזור. עורכים את זה רק אם רוצים לשנות את ההתנהגות/הכללים של הסוכנים עצמם. |
| `run_pipeline.py` | מנוע | הסקריפט שמריץ את הלולאה האינסופית של 4 הסוכנים. לא מריצים אותו ישירות — משתמשים ב-`start_pipeline.bat`. |
| `start_pipeline.bat` | פעולה | **מפעיל את הפייפליין.** פותח חלון נפרד שרץ לנצח, כולל המתנה אוטומטית וחזרה כשנגמרים הטוקנים. |
| `stop_pipeline.bat` | פעולה | **עוצר את הפייפליין.** מומלץ להריץ לפני `approve_and_deploy.bat`/`reject_and_reset.bat` כדי שלא יהיה מירוץ בין קומיט חדש לבין הפעולה שלך. |
| `review_changes.bat` | פעולה | פותח בדפדפן את עמוד ההשוואה בגיטהאב בין `main` (מה שיש היום) ל-`pipeline-dev` (מה שהסוכנים בנו) — כדי לקרוא את השינויים לפני שמחליטים. |
| `approve_and_deploy.bat` | פעולה | ✅ **מאשרים ופורסים לפרודקשיין.** ממזג `pipeline-dev` ל-`main`, דוחף לגיטהאב, מעדכן את התיקייה החיה, ושואל בנפרד אם להפעיל מחדש את הבוט. רק אחרי "כן" שני זה מגיע בפועל לטלגרם. |
| `reject_and_reset.bat` | פעולה | ❌ **דוחים ומאפסים.** מוחק לצמיתות את כל מה שהסוכנים בנו ב-`pipeline-dev` ומחזיר אותו בדיוק למה שיש ב-`main`. לא נוגע בתיקייה החיה בכלל. הפייפליין יתחיל מחדש מהמצב הנוכחי בפעם הבאה שיופעל. |
| `.gitignore` | הגדרות | קבצים שלא נשמרים בגיט (יומנים, next_task.md וכו') — לא צריך לגעת בזה. |
| `pipeline.log` | פלט (נוצר אוטומטית) | יומן מלא של כל מה שהפייפליין עשה — לפתוח עם עורך טקסט כשרוצים לחקור לעומק. |
| `pipeline_status.json` | פלט (נוצר אוטומטית) | תמונת מצב מהירה: מחזור נוכחי, שלב אחרון, עלות מצטברת בדולרים. |
| `pipeline.pid` | פלט (נוצר אוטומטית) | קיים רק בזמן שהפייפליין רץ — מונע הפעלה כפולה בטעות. אם הפייפליין קרס בלי להיסגר נכון והקובץ נשאר, פשוט מוחקים אותו ידנית. |
| `next_task.md` | פלט (נוצר אוטומטית) | המשימה הבאה שסוכן 1 כתב עבור סוכן 2. נוצר מחדש כל מחזור. |
| `bugs_found.md` | פלט (נוצר אוטומטית) | הבאגים שסוכן 3 מצא עבור סוכן 4. נוצר מחדש כל מחזור. |
| `..\.env` (בתיקייה הראשית, לא בתוך claude) | הגדרות סודיות | טוקן טלגרם ומפתח Gemini. לא בגיט. אין צורך לגעת אלא אם מחליפים טוקן/מפתח. |

## תרחישי שימוש

### תרחיש 1: הפעלה ראשונה (חד-פעמי)
1. ודא שביצעת את ההתחברות החד-פעמית לגיטהאב (`git push -u origin main` ו-`git push -u origin pipeline-dev` מהטרמינל שלך).
2. לחיצה כפולה על `start_pipeline.bat`.
3. משאירים את החלון פתוח ברקע. אפשר לסגור את השיחה עם קלוד — הפייפליין ממשיך לרוץ בעצמו.

### תרחיש 2: בדיקת התקדמות תוך כדי ריצה
1. מסתכלים ב-`pipeline_status.json` (מחזור נוכחי, עלות) — פתיחה מהירה, לא צריך לקרוא הכל.
2. לפרטים מלאים: פותחים את `pipeline.log`.
3. לראות בפועל מה נבנה: `review_changes.bat`.

### תרחיש 3: אהבתי את מה שהסוכנים בנו — רוצה שזה יעלה לבוט האמיתי
1. (מומלץ) `stop_pipeline.bat` כדי שלא ירוץ במקביל.
2. `review_changes.bat` — קריאה אחרונה של הדיף בגיטהאב.
3. `approve_and_deploy.bat` → עונים "y" למיזוג → עונים "y" להפעלה מחדש של הבוט.
4. בודקים בטלגרם שהבוט מגיב ושהפיצ'ר החדש עובד.
5. `start_pipeline.bat` שוב אם רוצים להמשיך לפיתוח הבא.

### תרחיש 4: לא אהבתי / לא רלוונטי — רוצה למחוק ולתת לו לנסות שוב
1. (מומלץ) `stop_pipeline.bat`.
2. `reject_and_reset.bat` → עונים "y". כל מה שנבנה נמחק, `pipeline-dev` חוזר להיות זהה ל-`main`.
3. הבוט החי לא נגע בכלל, אין צורך לגעת בו.
4. `start_pipeline.bat` שוב — הפייפליין מתחיל מחזור חדש מנקודת ההתחלה הנוכחית.

### תרחיש 5: לבדוק את הקוד לוקאלית בלי להשפיע על הבוט האמיתי
1. פותחים את התיקייה `Stock_Bot_pipeline_workspace` (לא `Stock Bot`!) בעורך קוד.
2. **חשוב:** אם רוצים להריץ בפועל את `bot.py` משם, צריך טוקן טלגרם **נפרד לבדיקות** (בוט חדש שיוצרים דרך @BotFather) בקובץ `.env` שם — לעולם לא את הטוקן החי, אחרת שני התהליכים יתנגשו על אותו בוט בטלגרם.

### תרחיש 6: משהו נראה תקוע / לא בטוח אם הפייפליין רץ
1. אם `pipeline.pid` קיים אבל אין חלון פתוח בפועל — הפייפליין קרס. מוחקים את הקובץ ומריצים שוב `start_pipeline.bat`.
2. `pipeline_status.json` ו-`pipeline.log` תמיד יגידו איפה זה נעצר לאחרונה.

## הגדרות מתקדמות (לא חובה לגעת)

אפשר לכוון את התנהגות הפייפליין בלי לערוך קוד, על ידי הגדרת משתני סביבה לפני `start_pipeline.bat`:

| משתנה | ברירת מחדל | מה הוא עושה |
|---|---|---|
| `PIPELINE_EFFORT` | (יורש מההגדרה הגלובלית, בד"כ `xhigh`) | רמת עומק חשיבה. `medium` = מהיר וזול יותר, פחות מעמיק. |
| `PIPELINE_MAX_BUDGET_USD` | `5` | תקרת עלות דולרים לכל קריאה בודדת של סוכן. |
| `PIPELINE_AGENT_TIMEOUT` | 2700 (45 דקות) | כמה זמן לחכות לסוכן בודד לפני שמנסים שוב. |
| `PIPELINE_CYCLE_SLEEP` | 15 שניות | הפסקה בין מחזור למחזור. |
| `PIPELINE_RATE_LIMIT_BACKOFF` | 900 שניות (15 דקות) | כמה זמן להמתין כשנתקלים במגבלת שימוש, לפני הניסיון הבא. |

## תקלות נפוצות

- **"git is not recognized"** בטרמינל — פתחת טרמינל ישן שלא ראה את התקנת Git. תריץ `$env:PATH = "C:\Program Files\Git\cmd;$env:PATH"` פעם אחת בטרמינל הנוכחי, או סגור ופתח מחדש את כל האפליקציה (לא רק טאב טרמינל).
- **`approve_and_deploy.bat` אומר "push to GitHub failed"** — כנראה בעיית אינטרנט או שההתחברות לגיטהאב פגה. תריץ ידנית `git push origin main` מהתיקייה הראשית ותראה את השגיאה המדויקת.
- **הבוט לא מגיב אחרי deploy** — בדוק ב-Task Manager אם `python.exe` רץ בכלל, או פתח את `check_bot.bat` לראות סטטוס.

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

## Every file in the `claude` folder — what it does and when to run it

| File | Type | When to run it / what it is |
|---|---|---|
| `CLAUDE.md` | Config | The 4 agents' role rules and safety rules. The pipeline reads this every cycle. Only edit this if you want to change the agents' own behavior/rules. |
| `run_pipeline.py` | Engine | The script that runs the infinite 4-agent loop. Don't run it directly — use `start_pipeline.bat`. |
| `start_pipeline.bat` | Action | **Starts the pipeline.** Opens a dedicated window that runs forever, including automatically waiting and retrying when usage limits are hit. |
| `stop_pipeline.bat` | Action | **Stops the pipeline.** Recommended before `approve_and_deploy.bat`/`reject_and_reset.bat` so there's no race between a new commit and your action. |
| `review_changes.bat` | Action | Opens the GitHub comparison page between `main` (what's live today) and `pipeline-dev` (what the agents built) in your browser — to read the changes before deciding. |
| `approve_and_deploy.bat` | Action | ✅ **Approve and deploy to production.** Merges `pipeline-dev` into `main`, pushes to GitHub, updates the live folder, and separately asks whether to restart the bot. Only after that second "yes" does it actually reach Telegram. |
| `reject_and_reset.bat` | Action | ❌ **Reject and reset.** Permanently discards everything the agents built on `pipeline-dev` and resets it to exactly match `main`. Never touches the live folder at all. The pipeline will start fresh from the current state next time it's launched. |
| `.gitignore` | Config | Files that aren't saved to git (logs, next_task.md, etc.) — no need to touch this. |
| `pipeline.log` | Output (auto-generated) | Full log of everything the pipeline did — open with a text editor when you want to dig deep. |
| `pipeline_status.json` | Output (auto-generated) | Quick snapshot: current cycle, last stage, cumulative cost in dollars. |
| `pipeline.pid` | Output (auto-generated) | Exists only while the pipeline is running — prevents accidentally starting it twice. If the pipeline crashed without closing cleanly and this file is left behind, just delete it manually. |
| `next_task.md` | Output (auto-generated) | The next task Agent 1 wrote for Agent 2. Regenerated every cycle. |
| `bugs_found.md` | Output (auto-generated) | The bugs Agent 3 found for Agent 4. Regenerated every cycle. |
| `..\.env` (in the root folder, not inside claude) | Secret config | Telegram token and Gemini key. Not in git. No need to touch it unless you're rotating the token/key. |

## Usage scenarios

### Scenario 1: First-time setup (one-time)
1. Make sure you've done the one-time GitHub sign-in (`git push -u origin main` and `git push -u origin pipeline-dev` from your own terminal).
2. Double-click `start_pipeline.bat`.
3. Leave the window running in the background. You can close the chat with Claude — the pipeline keeps running on its own.

### Scenario 2: Checking progress while it's running
1. Glance at `pipeline_status.json` (current cycle, cost) — quick to open, no need to read everything.
2. For full detail: open `pipeline.log`.
3. To see what was actually built: `review_changes.bat`.

### Scenario 3: I like what the agents built — I want it live on the real bot
1. (Recommended) `stop_pipeline.bat` so it isn't running concurrently.
2. `review_changes.bat` — one last read of the diff on GitHub.
3. `approve_and_deploy.bat` → answer "y" to merge → answer "y" to restart the bot.
4. Check on Telegram that the bot responds and the new feature works.
5. Run `start_pipeline.bat` again if you want it to keep developing the next thing.

### Scenario 4: I don't like it / not relevant — discard it and let it try again
1. (Recommended) `stop_pipeline.bat`.
2. `reject_and_reset.bat` → answer "y". Everything built is discarded, `pipeline-dev` goes back to matching `main`.
3. The live bot was never touched — nothing to undo there.
4. Run `start_pipeline.bat` again — the pipeline starts a fresh cycle from the current baseline.

### Scenario 5: Testing the code locally without affecting the real bot
1. Open the `Stock_Bot_pipeline_workspace` folder (not `Stock Bot`!) in your code editor.
2. **Important:** if you want to actually run `bot.py` from there, you need a **separate test-only Telegram token** (a new bot created via @BotFather) in a `.env` file there — never the live token, or the two processes will collide over the same Telegram bot.

### Scenario 6: Something looks stuck / not sure if the pipeline is running
1. If `pipeline.pid` exists but there's no window actually open — the pipeline crashed. Delete the file and run `start_pipeline.bat` again.
2. `pipeline_status.json` and `pipeline.log` will always show where it last stopped.

## Advanced settings (optional)

You can tune the pipeline's behavior without editing code, by setting environment variables before running `start_pipeline.bat`:

| Variable | Default | What it does |
|---|---|---|
| `PIPELINE_EFFORT` | (inherits the global setting, usually `xhigh`) | Thinking depth. `medium` = faster and cheaper, less thorough. |
| `PIPELINE_MAX_BUDGET_USD` | `5` | Dollar cost cap per single agent call. |
| `PIPELINE_AGENT_TIMEOUT` | 2700 (45 minutes) | How long to wait for a single agent before retrying. |
| `PIPELINE_CYCLE_SLEEP` | 15 seconds | Pause between one full cycle and the next. |
| `PIPELINE_RATE_LIMIT_BACKOFF` | 900 seconds (15 minutes) | How long to wait after hitting a usage limit before trying again. |

## Common issues

- **"git is not recognized"** in the terminal — you opened an old terminal that didn't see the Git install. Run `$env:PATH = "C:\Program Files\Git\cmd;$env:PATH"` once in the current terminal, or fully close and reopen the whole app (not just a terminal tab).
- **`approve_and_deploy.bat` says "push to GitHub failed"** — likely an internet issue or your GitHub sign-in expired. Run `git push origin main` manually from the root folder to see the exact error.
- **The bot doesn't respond after a deploy** — check Task Manager to see if `python.exe` is even running, or open `check_bot.bat` to see its status.
