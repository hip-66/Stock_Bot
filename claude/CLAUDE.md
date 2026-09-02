# 🤖 PROJECT OVERVIEW: STOCK & FINANCIAL TELEGRAM BOT

## 1. General Objective & Vision
A state-of-the-art, autonomous financial assistant and portfolio management bot on Telegram. Powered by Google Gemini AI (`gemini-2.5-flash`), `yfinance`, and live market data searches. The bot provides real-time portfolio tracking, logs buy/sell transactions automatically via natural language or inline menus, delivers rich analytical insights with 100% data reliability, and maintains a clean, human-readable UI/UX optimized for Telegram.

## 2. Technical Stack
- **Language & Core:** Python 3.x
- **Telegram Interface:** `pyTelegramBotAPI` (Telebot) with `InlineKeyboardMarkup`
- **AI & Analytics:** Google GenAI SDK (`google-genai`), Structured Outputs (`Pydantic`), Google Search grounding
- **Financial Market Data:** `yfinance` (real-time stock pricing & currency exchange rates)
- **Task Scheduling:** `apscheduler` (automated reports twice daily at 12:00 and 20:00)
- **Database:** Local JSON-based persistent storage (`portfolio.json`) supporting cash deposits, stock holdings, transactions history, and realized/unrealized P&L calculations.

## 3. Core Features & Menu Architecture (Current State)
1. 📊 **General P&L Summary (`menu_1`):** Total invested capital, total portfolio value, free cash, active stocks value, and net profit/loss percentage.
2. 🔍 **Individual Stock Performance (`menu_2`):** Detailed breakdown per stock (quantity, average buy price, current market price, market value, and open P&L).
3. ➕ **Buy Transaction Logging (`menu_3`):** Natural language parsing to update portfolio holdings and cash balance upon purchasing stocks.
4. ➖ **Sell Transaction Logging (`menu_4`):** Realizing profits/losses and updating holdings when shares are sold.
5. 💡 **AI Portfolio Recommendations - Sell/Trim (`menu_5`):** Individual stock analysis with actionable sell/hold advice.
6. 💡 **AI Market Opportunities - Buy (`menu_6`):** High-potential stock recommendations outside the current portfolio.
7. 🔥 **Hardware & Storage Portfolio Assets (`menu_7`):** Analysis of existing hardware/storage/semiconductor holdings.
8. 🔥 **Hardware & Storage External Opportunities (`menu_8`):** Leading external hardware/storage stocks to consider.
9. 📈 **Weekly Momentum Stocks (In Portfolio) (`menu_9`):** Identifying strong upward momentum in current holdings.
10. 📈 **Weekly Momentum Stocks (External) (`menu_10`):** Hot external stocks showing sharp short-term breakout potential.
11. 📉 **Short/Risk Alerts (In Portfolio) (`menu_11`):** Weakness or short/downward pressure alerts on owned stocks.
12. 📉 **Short/Risk Alerts (External) (`menu_12`):** Market-wide short risks and declining stocks to avoid.
13. 💸 **Live Exchange Rates (`menu_13`):** Real-time USD/ILS and EUR/ILS currency conversions.
14. ⏰ **Automated Scheduled Reports:** Daily pushes sent automatically at 12:00 and 20:00.

---

# 🔄 MULTI-AGENT CONTINUOUS PIPELINE RULES

You are an autonomous 4-agent software development and optimization pipeline. On every execution, inspect the current state of the project files (`bot.py`, `portfolio.json`, etc.) and assume your designated role sequentially:

## ⚠️ Non-negotiable safety rules (apply to every agent)
- **Never start, run, or restart `bot.py` as a live process** (no `python bot.py`, no calling `run_bot.bat`/`restart_bot.bat`). A production instance is already polling Telegram with a real bot token — a second instance will collide with it (Telegram rejects concurrent pollers) and can knock the real bot offline. Validate logic via static reading, isolated unit tests of individual functions, and mocked calls only.
- **Never edit or delete `portfolio.json`.** It is live financial data, not application code.
- All pipeline hand-off files (`next_task.md`, `bugs_found.md`) live in the `claude/` folder, not the project root.
- Keep changes scoped to what the current `next_task.md`/`bugs_found.md` entry actually asks for — no unrelated rewrites.

### [Agent 1: Product Strategy & Feature Expansion]
- **Role:** Product Manager & Innovator.
- **Action:** Read the app structure, code, and user context. Analyze potential new features, UI/UX enhancements, efficiency improvements, and advanced financial tracking ideas.
- **Output:** Write the precise next development objective into `claude/next_task.md`.

### [Agent 2: Developer & Core Maintainer]
- **Role:** Software Engineer.
- **Action:** Read `claude/next_task.md`. Implement the requested features, optimize `bot.py`, improve API integrations (`yfinance`, `Gemini`), refine JSON database handling, and ensure clean, modular code writing.
- **Output:** Update code files and log completed tasks.

### [Agent 3: QA & Comprehensive Tester]
- **Role:** Quality Assurance Engineer.
- **Action:** Test the application logic from end to end (0 to 100) via static analysis and isolated unit tests. Verify JSON integrity, Telegram message parsing, Markdown formatting safety, rate limits, and error handling mechanisms.
- **Output:** If bugs or edge-case failures are found, log them in detail inside `claude/bugs_found.md`. If everything passes seamlessly, write "No issues found." to that file instead.

### [Agent 4: Root Cause Bug Fixer]
- **Role:** Senior Debugging Specialist.
- **Action:** Read `claude/bugs_found.md`. Fix all identified issues from the root cause in the Python source code, refactor unstable logic, ensure robust exception handling, and prepare a clean baseline for the next Agent 1 cycle. If the file says "No issues found.", do nothing.
- **Output:** Clean up logs and finalize fixes.

<!-- 



# 🤖 סקירת פרויקט: בוט טלגרם פיננסי לניהול תיק מניות

## 1. מטרה ראשית וחזון
אפליקציית בוט טלגרם אוטונומית, מתקדמת ומקצועית לניהול תיק השקעות ומעקב פיננסי. הבוט מופעל באמצעות בינה מלאכותית (`Google Gemini API` בגרסת `gemini-2.5-flash`), נתוני שוק בזמן אמת דרך `yfinance`, וחיפושי רשת חיים (Google Search grounding). הבוט מעקב רציף אחר תיק המניות האישי של המשתמש, מתעד קניות ומכירות באופן חכם, מפיק דוחות הון מפורטים, מחשב רווחים והפסדים (ממומשים ולא ממומשים) ומציג שערי חליפין מעודכנים. כמו כן, הבוט שולח דוחות אוטומטיים מתוזמנים פעמיים ביום (בשעה 12:00 ובשעה 20:00), מספק ניתוחי שוק אנליסטיים באמינות גבוהה, ומציג ממשק משתמש (UI/UX) אינטואיטיבי, נקי ונעים לקריאה המבוסס על כפתורי אינטראקציה מתקדמים (Inline Keyboards).

## 2. טכנולוגיות פרויקט (Tech Stack)
- **שפת פיתוח ותשתית:** Python 3.x
- **ממשק טלגרם:** `pyTelegramBotAPI` (Telebot) עם תמיכה ב-`InlineKeyboardMarkup`
- **בינה מלאכותית וניתוחים:** Google GenAI SDK (`google-genai`), פלט מובנה באמצעות `Pydantic` (Structured Outputs), וגישת חיפוש מידע ברשת
- **מידע פיננסי:** ספריית `yfinance` לשליפת מחירי מניות ושערי חליפין בזמן אמת
- **תזמון משימות:** `apscheduler` להפצת דוחות מתוזמנים אוטומטיים ב-12:00 וב-20:00
- **בסיס נתונים:** אחסון מקומי מבוסס קובץ JSON (`portfolio.json`) המנהל הפקדות מזומן, אחזקות מניות, היסטוריית פעולות וחישובי P&L.

## 3. פיצרים מרכזיים וארכיטקטורת התפריטים (Core Features)
1. 📊 **סיכום רווחים/הפסדים כלליים בתיק (`menu_1`):** שווי תיק כולל, הון שהופקד, מזומן פנוי, שווי מניות פעילות ומאזן כולל באחוזים ובדולרים.
2. 🔍 **פירוט ביצועים לכל מניה בנפרד (`menu_2`):** כמות אחזקה, ממוצע מחיר קנייה, מחיר שוק נוכחי, שווי שוק ורווח/הפסד פתוח לכל נכס.
3. ➕ **דיווח על קניית מניות (`menu_3`):** פענוח טקסט חופשי ועדכון אוטומטי של פוזיציות קנייה ומזומן בתיק.
4. ➖ **דיווח על מכירת מניות (`menu_4`):** מימוש רווחים/הפסדים ועדכון היתרות בתיק בעת סגירת פוזיציה.
5. 💡 **מניות מומלצות למכירה/צמצום מהתיק (`menu_5`):** ניתוח AI פרטני לכל מניה בתיק עם המלצה אופרטיבית (החזק או מכור).
6. 💡 **מניות מומלצות לקנייה/השקעה שלא בתיק (`menu_6`):** זיהוי הזדמנויות חזקות בשוק עם פוטנציאל תשואה גבוה שאינן בתיק כרגע.
7. 🔥 **חומרה ואחסון רווחיות שקיימות בתיק (`menu_7`):** מעקב וניתוח של מניות שבבים, חומרה ואחסון שנמצאות בפורטפוליו.
8. 🔥 **חומרה ואחסון רווחיות שלא בתיק (`menu_8`):** סקירת מניות חומרה ושבבים מובילות בשוק ששווה לבחון להשקעה.
9. 📈 **פוטנציאל זינוק השבוע שקיימות בתיק (`menu_9`):** איתור מומנטום חזק בנכסים הקיימים.
10. 📈 **פוטנציאל זינוק השבוע שלא בתיק (`menu_10`):** חשיפת מניות חמות מחוץ לתיק המציגות פוטנציאל פריצה חד השבוע.
11. 📉 **התראות שורט/ירידה שקיימות בתיק (`menu_11`):** זיהוי סימני חולשה או לחץ שורט על המניות שבבעלותך.
12. 📉 **התראות שורט/ירידה שלא בתיק (`menu_12`):** זיהוי מניות בסיכון ירידה בשוק הכללי שכדאי להיזהר מהן.
13. 💸 **שערי חליפין עדכניים (`menu_13`):** המרות רציפות ומדויקות של USD/ILS ו-EUR/ILS.
14. ⏰ **דוחות מתוזמנים אוטומטיים:** שליחת סיכום תיק פעמיים ביום באופן אוטומטי (12:00 ו-20:00).

---

# 🔄 חוקי תהליך העבודה האוטונומי (Multi-Agent Pipeline)

אתה חלק ממחזורית פיתוח ואופטימיזציה אוטונומית המורכבת מ-4 סוכנים. בכל הפעלה עליך לבדוק את מצב קבצי הפרויקט (`bot.py`, `portfolio.json` וכדומה) ולשחק בסבב את התפקיד התורן:

### [סוכן 1: אסטרטגיית מוצר ופיתוח פיצרים]
- **תפקיד:** מנהל מוצר וחדשנות.
- **פעולה:** קורא את מבנה האפליקציה, קוד המקור והקונטקסט. מנתח רעיונות לפיצרים חדשים, שיפורי חוויית משתמש (UI/UX), התייעלות ורעיונות מתקדמים לניהול התיק.
- **תוצר:** כתיבת משימת הפיתוח הבאה באופן מפורט בקובץ `next_task.md`.

### [סוכן 2: מפתח ותחזוקת מערכת]
- **תפקיד:** מהנדס תוכנה ראשי.
- **פעולה:** קורא את קובץ `next_task.md`. מממש את הפיצ'רים הנדרשים, משפר את `bot.py`, מייעל את שליפת הנתונים מ-`yfinance` ומ-Gemini, מטפל בבסיס הנתונים (JSON) ושומר על כתיבת קוד נקייה ומודולרית.
- **תוצר:** עדכון קבצי הקוד בפרויקט ורישום ביצוע המשימה.

### [סוכן 3: בקר איכות ובדיקות (QA)]
- **תפקיד:** מהנדס אבטחת איכות ובדיקות.
- **פעולה:** בודק את לוגיקת האפליקציה מקצה לקצה (מ-0 עד 100). מוודא שלמות מבני הנתונים ב-JSON, תקינות הודעות טלגרם, תאימות לתקני Markdown, ניהול שגיאות ומגבלות קצב (Rate Limits).
- **תוצר:** אם נמצאו באגים או תקלות קצה, מתעד אותם בפירוט בקובץ `bugs_found.md`. אם הכל תקין לחלוטין, מציין זאת במפורש.

### [סוכן 4: מתקן תקלות מהשורש (Bug Fixer)]
- **תפקיד:** מומחה דיבאגינג בכיר.
- **פעולה:** קורא את `bugs_found.md`. מתקן את כל השגיאות והבאגים מהשורש ישירות בקוד הפייתון, מתקן לוגיקה לא יציבה, מוסיף הגנות חסינות לשגיאות (Exception Handling), ומכין תשתית נקייה ומדויקת לסבב הבא של סוכן 1.
- **תוצר:** ניקוי לוגים ויישום התיקונים בקוד המקור. -->