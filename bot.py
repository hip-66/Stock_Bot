import os
import sys
import subprocess
import json
import time
from datetime import datetime

# =====================================================================
# 1. מנגנון בדיקה והתקנה אוטומטית של ספריות
# =====================================================================
REQUIRED_PACKAGES = {
    "telebot": "pyTelegramBotAPI",
    "yfinance": "yfinance",
    "google.genai": "google-genai",
    "apscheduler": "apscheduler",
    "bidi": "python-bidi",
    "pydantic": "pydantic"
}

print("Checking required packages...")
for import_name, install_name in REQUIRED_PACKAGES.items():
    try:
        __import__(import_name)
    except ImportError:
        print(f"Missing package {install_name}. Installing automatically...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", install_name])

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yfinance as ticker_viewer
from apscheduler.schedulers.background import BackgroundScheduler
from google import genai
from google.genai import types
from bidi.algorithm import get_display
from pydantic import BaseModel, Field
from typing import Optional

def print_rtl(text):
    print(get_display(str(text)))

print_rtl("Starting UI-Refined Telegram Financial Bot...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# 2. הגדרות ונתונים אישיים (נטענים מ-.env או ממשתני סביבה - לא בקוד)
# =====================================================================
def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

load_env_file(os.path.join(BASE_DIR, ".env"))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
_MY_CHAT_ID_RAW = os.environ.get("MY_CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

if not TELEGRAM_TOKEN or not _MY_CHAT_ID_RAW or not GEMINI_KEY:
    raise RuntimeError(
        "Missing TELEGRAM_TOKEN / MY_CHAT_ID / GEMINI_KEY. "
        "Set them as environment variables, or create a .env file next to bot.py "
        "with lines like TELEGRAM_TOKEN=..., MY_CHAT_ID=..., GEMINI_KEY=..."
    )
MY_CHAT_ID = int(_MY_CHAT_ID_RAW)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

class AIClientUnavailableError(RuntimeError):
    """Raised when Gemini features are used but the client failed to initialize at startup."""

ai_client = None
MODEL_NAME = 'gemini-2.5-flash'
try:
    ai_client = genai.Client(api_key=GEMINI_KEY)
    print_rtl(f"\nהחיבור ל-Gemini ({MODEL_NAME}) בוצע בהצלחה!")
except Exception as e:
    print_rtl(f"\n❌ שגיאה באתחול Gemini: {e}\nכל תכונות ה-AI (תפריטים 5-12 והודעות חופשיות) יהיו מושבתות עד לתיקון.")

DB_FILE = os.path.join(BASE_DIR, "portfolio.json")

PRICE_CACHE = {}
CACHE_DURATION = 300  # 5 דקות מטמון

# =====================================================================
# 3. הגדרת סכמת הנתונים של ה-AI (Structured Output)
# =====================================================================
class PortfolioUpdateSchema(BaseModel):
    action: str = Field(description="The financial action detected: 'BUY', 'SELL', 'DEPOSIT', or 'NONE'")
    symbol: Optional[str] = Field(default=None, description="The stock ticker symbol upper-case")
    qty: Optional[float] = Field(default=0.0, description="Quantity of shares")
    price: Optional[float] = Field(default=0.0, description="Price per share")
    ai_reply: str = Field(description="The technical or analyst-style text response directed to the user in fluent Hebrew.")

# =====================================================================
# 4. ניהול בסיס הנתונים
# =====================================================================
def load_portfolio():
    default_structure = {
        "cash_deposits": {"total_deposited_usd": 0.0, "history": []},
        "stocks": {}, 
        "total_realized_pnl": 0.0
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "stocks" in data:
                    if "cash_deposits" not in data:
                        data["cash_deposits"] = {"total_deposited_usd": 0.0, "history": []}
                    return data
        except Exception as e:
            print_rtl(f"Error reading JSON file: {e}")
    return default_structure

def save_portfolio(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print_rtl(f"❌ שגיאה בשמירת קובץ הנתונים: {e}")

# =====================================================================
# 5. משיכת מחירי מניות ושערי חליפין
# =====================================================================
def get_cached_price(symbol):
    current_time = time.time()
    if symbol in PRICE_CACHE:
        cached_price, timestamp = PRICE_CACHE[symbol]
        if current_time - timestamp < CACHE_DURATION:
            return cached_price
            
    try:
        stock = ticker_viewer.Ticker(symbol)
        price = stock.info.get("currentPrice") or stock.info.get("regularMarketPrice")
        if price:
            PRICE_CACHE[symbol] = (float(price), current_time)
            return float(price)
    except Exception:
        pass
    
    if symbol in PRICE_CACHE:
        return PRICE_CACHE[symbol][0]
    return None

# =====================================================================
# 6. בניית תפריט ה-UI/UX החדש (Inline Keyboard)
# =====================================================================
def get_main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    
    markup.add(
        InlineKeyboardButton("📊 סיכום רווחים/הפסדים כלליים בתיק", callback_data="menu_1"),
        InlineKeyboardButton("🔍 פירוט ביצועים לכל מניה בנפרד", callback_data="menu_2"),
        InlineKeyboardButton("➕ דיווח על קניית מניות (עדכון התיק)", callback_data="menu_3"),
        InlineKeyboardButton("➖ דיווח על מכירת מניות (מימוש רווח)", callback_data="menu_4"),
        InlineKeyboardButton("💡 מניות מומלצות למכירה/צמצום מהתיק", callback_data="menu_5"),
        InlineKeyboardButton("💡 מניות מומלצות לקנייה/השקעה שלא בתיק", callback_data="menu_6"),
        InlineKeyboardButton("🔥 חומרה ואחסון רווחיות שקיימות בתיק", callback_data="menu_7"),
        InlineKeyboardButton("🔥 חומרה ואחסון רווחיות שלא בתיק", callback_data="menu_8"),
        InlineKeyboardButton("📈 פוטנציאל זינוק השבוע שקיימות בתיק", callback_data="menu_9"),
        InlineKeyboardButton("📈 פוטנציאל זינוק השבוע שלא בתיק", callback_data="menu_10"),
        InlineKeyboardButton("📉 התראות שורט/ירידה שקיימות בתיק", callback_data="menu_11"),
        InlineKeyboardButton("📉 התראות שורט/ירידה שלא בתיק", callback_data="menu_12"),
        InlineKeyboardButton("💸 שערי חליפין עדכניים (שקל/דולר/אירו)", callback_data="menu_13"),
        InlineKeyboardButton("📜 היסטוריית עסקאות", callback_data="menu_14")
    )
    return markup

# =====================================================================
# 7. עיצוב ממשק מוקפד וברור (שורה לכל נתון בצורה מושלמת)
# =====================================================================
def get_financial_status():
    usd_ils = get_cached_price("ILS=X") or "לא זמין"
    eur_ils = get_cached_price("EURILS=X") or "לא זמין"
        
    portfolio = load_portfolio()
    stocks_report = ""
    portfolio_summary = ""
    
    total_unrealized_buy = 0.0
    total_unrealized_current = 0.0
    total_portfolio_realized_pnl = portfolio.get("total_realized_pnl", 0.0)
    
    cash_data = portfolio.get("cash_deposits", {})
    total_deposited_usd = float(cash_data.get("total_deposited_usd", 0.0))
    
    if not portfolio.get("stocks"):
        stocks_report = "אין מניות רשומות בתיק כרגע."
    else:
        stocks_report += "📋 **פירוט אחזקות וביצועים לפי מניה:**\n"
        stocks_report += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for symbol, data in portfolio["stocks"].items():
            holdings = data.get("holdings", {"qty": 0.0, "avg_purchase_price": 0.0})
            qty = float(holdings.get("qty", 0.0))
            avg_buy = float(holdings.get("avg_purchase_price", 0.0))
            realized_pnl = float(data.get("realized_pnl", 0.0))
            
            if qty == 0 and realized_pnl == 0:
                continue
                
            current_price = None
            if qty > 0:
                current_price = get_cached_price(symbol)

            stocks_report += f"📌 **מניית {symbol}**\n"
            
            if qty > 0 and current_price:
                total_invested_in_stock = avg_buy * qty
                total_current_val = current_price * qty
                
                total_unrealized_buy += total_invested_in_stock
                total_unrealized_current += total_current_val
                
                unrealized_pnl = total_current_val - total_invested_in_stock
                unrealized_pct = (unrealized_pnl / total_invested_in_stock) * 100 if total_invested_in_stock > 0 else 0
                unrealized_status = "🟢 רווח פתוח" if unrealized_pnl >= 0 else "🔴 הפסד פתוח"
                
                stocks_report += (
                    f"▫️ כמות אחזקה: `{qty:g}` יחידות\n"
                    f"▫️ שער קנייה ממוצע: `{avg_buy:.2f}$`\n"
                    f"▫️ מחיר שוק נוכחי: `{current_price:.2f}$`\n"
                    f"▫️ שווי שוק כולל: `{total_current_val:.2f}$`\n"
                    f"▫️ {unrealized_status}: `{abs(unrealized_pnl):.2f}$` (`{unrealized_pct:+.2f}%`)\n"
                )
            elif qty > 0:
                stocks_report += f"▫️ כמות: `{qty:g}` | ממוצע: `{avg_buy:.2f}$` (שגיאת שוק)\n"
            else:
                stocks_report += "▫️ אין פוזיציה פתוחה כרגע.\n"
                
            if realized_pnl != 0:
                stocks_report += f"▫️ 💰 רווח נעול: `{realized_pnl:.2f}$`\n"
                
            stocks_report += "───────────────────\n\n"
            
        total_unrealized_pnl = total_unrealized_current - total_unrealized_buy
        grand_total_pnl = total_unrealized_pnl + total_portfolio_realized_pnl
        current_cash_balance = total_deposited_usd - total_unrealized_buy + total_portfolio_realized_pnl
        total_portfolio_value = total_unrealized_current + current_cash_balance
        net_pnl_pct = (grand_total_pnl / total_deposited_usd) * 100 if total_deposited_usd > 0 else 0

        current_time_str = datetime.now().strftime('%d/%m/%Y בשעה %H:%M:%S')
        
        portfolio_summary = (
            f"👑 **דו\"ח סיכום הון וביצועים**\n"
            f"📅 עדכון: `{current_time_str}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 סך הון שהופקד: `{total_deposited_usd:.2f}$`\n"
            f"🏦 שווי תיק כולל: `{total_portfolio_value:.2f}$`\n"
            f"💰 מזומן פנוי: `{current_cash_balance:.2f}$`\n"
            f"📈 שווי מניות פעילות: `{total_unrealized_current:.2f}$`\n"
            f"🔥 מאזן כולל: `{grand_total_pnl:+.2f}$` (`{net_pnl_pct:+.2f}%`)\n"
        )
                
    return usd_ils, eur_ils, stocks_report, portfolio_summary

# =====================================================================
# 8. מנוע ה-AI (Gemini)
# =====================================================================
def generate_ai_response(user_prompt, explicit_intent=None):
    if ai_client is None:
        raise AIClientUnavailableError(
            "לקוח ה-Gemini לא אותחל בהצלחה בעת הפעלת הבוט (בדוק GEMINI_KEY ואת החיבור לרשת)."
        )

    usd, eur, stocks_data, portfolio_summary = get_financial_status()
    
    portfolio = load_portfolio()
    active_tickers = list(portfolio.get("stocks", {}).keys())
    
    search_context = f"""
    אתה אנליסט שוק ומנהל השקעות טכני חד, ישיר ומתקדם ביותר. תענה בעברית מקצועית.
    המשתמש מבין היטב את שוק ההון - אל תוציא אזהרות או דיסקליימרים משפטיים!
    
    רשימת המניות שנמצאות כרגע בפועל בתיק של המשתמש: {active_tickers if active_tickers else "אין מניות בתיק כרגע"}
    
    נתוני שוק: דולר: {usd} ש"ח | אירו: {eur} ש"ח
    {portfolio_summary}
    """
    
    if explicit_intent:
        user_prompt = f"[בקשה מהתפריט: {explicit_intent}] - {user_prompt}"

    full_contents = f"{search_context}\n\nהודעה: {user_prompt}"

    search_response = ai_client.models.generate_content(
        model=MODEL_NAME,
        contents=full_contents,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.2
        )
    )
    
    ai_analyzed_text = search_response.text.strip()

    struct_context = f"""
    חלץ את הפעולה הפיננסית מהודעת המשתמש ל-JSON. הודעה: "{user_prompt}"
    בשדה 'ai_reply' העתק בדיוק את הטקסט הבא:
    {ai_analyzed_text}
    """

    struct_response = ai_client.models.generate_content(
        model=MODEL_NAME,
        contents=struct_context,
        config=types.GenerateContentConfig(
            tools=[],
            response_mime_type="application/json",
            response_schema=PortfolioUpdateSchema,
            temperature=0.1
        )
    )
    
    return json.loads(struct_response.text)

# =====================================================================
# 9. ניהול פוזיציות והודעות בטוחות
# =====================================================================
def apply_portfolio_action(action_data):
    action = action_data.get("action", "NONE").upper()
    portfolio = load_portfolio()
    
    if action == "DEPOSIT":
        amount_usd = float(action_data.get("price") or 0.0)
        if amount_usd > 0:
            portfolio["cash_deposits"]["total_deposited_usd"] += amount_usd
            save_portfolio(portfolio)
        return

    symbol = action_data.get("symbol")
    if not symbol or str(symbol).upper().strip() in ["INFO", "HELP", "MENU", "BUY", "SELL"]:
        return
        
    symbol = str(symbol).upper().strip()
    qty = float(action_data.get("qty") or 0.0)
    price = float(action_data.get("price") or 0.0)
    
    if action == "NONE" or qty <= 0:
        return
        
    if symbol not in portfolio["stocks"]:
        portfolio["stocks"][symbol] = {"holdings": {"qty": 0.0, "avg_purchase_price": 0.0}, "realized_pnl": 0.0, "transactions": []}
        
    stock_entry = portfolio["stocks"][symbol]
    current_qty = float(stock_entry["holdings"]["qty"])
    current_avg = float(stock_entry["holdings"]["avg_purchase_price"])
    
    if action == "BUY":
        new_qty = current_qty + qty
        new_avg = ((current_qty * current_avg) + (qty * price)) / new_qty if new_qty > 0 else 0.0
        stock_entry["holdings"]["qty"] = new_qty
        stock_entry["holdings"]["avg_purchase_price"] = new_avg
        stock_entry.setdefault("transactions", []).append({
            "action": "BUY",
            "qty": qty,
            "price": price,
            "date": datetime.now().isoformat(timespec="seconds")
        })
    elif action == "SELL":
        qty_to_sell = min(qty, current_qty)
        if qty_to_sell > 0:
            pnl = (price - current_avg) * qty_to_sell
            stock_entry["realized_pnl"] += pnl
            portfolio["total_realized_pnl"] += pnl
            stock_entry["holdings"]["qty"] = current_qty - qty_to_sell
            if stock_entry["holdings"]["qty"] == 0:
                stock_entry["holdings"]["avg_purchase_price"] = 0.0
            stock_entry.setdefault("transactions", []).append({
                "action": "SELL",
                "qty": qty_to_sell,
                "price": price,
                "date": datetime.now().isoformat(timespec="seconds"),
                "realized_pnl": pnl
            })

    save_portfolio(portfolio)

def send_long_message(chat_id, text, reply_markup=None):
    if not text:
        return
        
    max_len = 3800
    if len(text) <= max_len:
        try:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            bot.send_message(chat_id, text.replace("*", "").replace("[", "").replace("]", ""), reply_markup=reply_markup)
    else:
        parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
        for idx, part in enumerate(parts):
            markup = reply_markup if idx == len(parts) - 1 else None
            try:
                bot.send_message(chat_id, part, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                bot.send_message(chat_id, part.replace("*", "").replace("[", "").replace("]", ""), reply_markup=markup)

# =====================================================================
# 10. טיפול בלחיצות על כפתורי התפריט
# =====================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_click(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    menu_id = call.data.split("_")[1]
    
    usd, eur, stocks_data, portfolio_summary = get_financial_status()
    
    if menu_id == "1":
        send_long_message(chat_id, portfolio_summary, reply_markup=get_main_menu_keyboard())
    elif menu_id == "2":
        send_long_message(chat_id, stocks_data, reply_markup=get_main_menu_keyboard())
    else:
        loading_msg = bot.send_message(chat_id, "⏳ מבצע סריקת שוק וניתוח נתונים מסודר... אנא המתן.")
        bot.send_chat_action(chat_id, 'typing')
        
        response_text = ""
        try:
            if menu_id == "3":
                response_text = "➕ דיווח על קנייה:\n\nשלח לי בטקסט חופשי: 'קניתי 10 מניות WDC ב-72 דולר'."
            elif menu_id == "4":
                response_text = "➖ דיווח על מכירה:\n\nשלח לי בטקסט חופשי: 'מכרתי 5 מניות ב-135 דולר'."
            elif menu_id == "5":
                ai_res = generate_ai_response("נתח אחת-אחת את המניות שנמצאות אצלי בתיק. תן המלצה אופרטיבית חד משמעית לכל מניה: האם למכור או להחזיק ולכמה זמן.", "המלצות מכירה וצמצום מהתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "6":
                ai_res = generate_ai_response("תן לי המלצות ממוקדות על מניות חזקות לקנייה והשקעה שאינן קיימות כרגע בתיק שלי, עם דגש על פוטנציאל תשואה גבוה.", "מניות מומלצות לקנייה שלא בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "7":
                ai_res = generate_ai_response("בדוק אילו מניות חומרה, שבבים ואחסון רווחיות קיימות אצל בתיק כרגע, ונתח את מצבן בשוק הנוכחי.", "חומרה ואחסון שקיימות בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "8":
                ai_res = generate_ai_response("תן סקירה על מניות חומרה ואחסון מובילות בולטות ברווחיותן שאינן קיימות בתיק שלי כרגע ושווה לשקול.", "חומרה ואחסון שלא בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "9":
                ai_res = generate_ai_response("בדוק איזו מניה מתוך המניות שקיימות אצלי בתיק מציגה מומנטום חזק ופוטנציאל זינוק השבוע.", "פוטנציאל זינוק שקיימות בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "10":
                ai_res = generate_ai_response("הצג מניות חמות מחוץ לתיק שלי שמציגות כעת פוטנציאל זינוק חד השבוע.", "פוטנציאל זינוק שלא בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "11":
                ai_res = generate_ai_response("האם ישנן התראות שורט או סימני חולשה מסוכנים על מניות שקיימות אצלי בתיק כרגע?", "התראות שורט שקיימות בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "12":
                ai_res = generate_ai_response("אילו מניות בשוק שעתידות לרדת או חשופות לשורט כבד כדאי להיזהר מהן (מניות שלא בתיק)?", "התראות שורט שלא בתיק")
                response_text = ai_res.get("ai_reply", "אין מענה.")
            elif menu_id == "13":
                response_text = (
                    "💸 שערי חליפין רציפים עדכניים:\n\n"
                    f"💵 USD/ILS: `{usd if isinstance(usd, str) else f'{usd:.4f}'}` ש\"ח\n"
                    f"💶 EUR/ILS: `{eur if isinstance(eur, str) else f'{eur:.4f}'}` ש\"ח\n\n"
                    f"⏰ עודכן: {datetime.now().strftime('%H:%M:%S')}"
                )
            elif menu_id == "14":
                portfolio_data = load_portfolio()
                all_txns = []
                for sym, sdata in portfolio_data.get("stocks", {}).items():
                    for txn in sdata.get("transactions", []):
                        entry = dict(txn)
                        entry["symbol"] = sym
                        all_txns.append(entry)

                if not all_txns:
                    response_text = "📜 אין עסקאות רשומות עדיין."
                else:
                    all_txns.sort(key=lambda t: t.get("date", ""), reverse=True)
                    lines = ["📜 **היסטוריית עסקאות אחרונות**", "━━━━━━━━━━━━━━━━━━━\n"]
                    for txn in all_txns[:15]:
                        txn_action = txn.get("action", "")
                        emoji = "🟢" if txn_action == "BUY" else "🔴"
                        action_label = "קנייה" if txn_action == "BUY" else "מכירה"
                        txn_qty = float(txn.get("qty", 0.0))
                        txn_price = float(txn.get("price", 0.0))
                        total_value = txn_qty * txn_price
                        raw_date = txn.get("date", "")
                        try:
                            date_str = datetime.fromisoformat(raw_date).strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            date_str = raw_date

                        line = (
                            f"{emoji} **{txn.get('symbol', '?')}** | {action_label}\n"
                            f"▫️ כמות: `{txn_qty:g}` | מחיר: `{txn_price:.2f}$` | שווי: `{total_value:.2f}$`\n"
                            f"▫️ תאריך: `{date_str}`"
                        )
                        if txn_action == "SELL" and "realized_pnl" in txn:
                            realized = float(txn.get("realized_pnl", 0.0))
                            pnl_emoji = "💰" if realized >= 0 else "📉"
                            line += f"\n▫️ {pnl_emoji} רווח/הפסד ממומש: `{realized:+.2f}$`"
                        lines.append(line + "\n───────────────────")
                    response_text = "\n".join(lines)
        except AIClientUnavailableError as e:
            print_rtl(f"❌ AI לא זמין בכפתור {menu_id}: {e}")
            response_text = "🤖 שירות ה-AI אינו זמין כרגע (כשל באתחול). פנה למנהל המערכת לבדיקת GEMINI_KEY."
        except Exception as e:
            print_rtl(f"❌ שגיאה בכפתור {menu_id}: {e}")
            response_text = "⚠️ חלה שגיאה במשיכת הנתונים. אנא נסה שוב."
            
        try:
            bot.delete_message(chat_id, loading_msg.message_id)
        except Exception:
            pass
            
        send_long_message(chat_id, response_text, reply_markup=get_main_menu_keyboard())

# =====================================================================
# 11. פקודות ותקשורת חופשית
# =====================================================================
@bot.message_handler(commands=['start', 'menu'])
def send_welcome_menu(message):
    welcome_text = (
        "🤖 **ברוך הבא למערכת הניהול הפיננסי!**\n\n"
        "בחר אפשרות מהתפריט למטה או שלח הודעה חופשית לעדכון התיק."
    )
    send_long_message(message.chat.id, welcome_text, reply_markup=get_main_menu_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_free_text(message):
    print_rtl(f"📥 הודעה חדשה: {message.text}")
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        structured_response = generate_ai_response(message.text)
        apply_portfolio_action(structured_response)
        usd, eur, stocks_data, updated_portfolio_summary = get_financial_status()
        
        ai_text_reply = structured_response.get("ai_reply", "")
        
        send_long_message(message.chat.id, f"{ai_text_reply}\n\n{updated_portfolio_summary}")
        send_long_message(message.chat.id, stocks_data, reply_markup=get_main_menu_keyboard())

    except AIClientUnavailableError as e:
        print_rtl(f"❌ AI לא זמין: {e}")
        bot.send_message(message.chat.id, "🤖 שירות ה-AI אינו זמין כרגע (כשל באתחול). פנה למנהל המערכת לבדיקת GEMINI_KEY.", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        print_rtl(f"❌ שגיאה: {e}")
        bot.send_message(message.chat.id, "⚠️ אופס, חלה שגיאה זמנית בעיבוד הנתונים.", reply_markup=get_main_menu_keyboard())

def send_scheduled_report():
    usd, eur, stocks_data, portfolio_summary = get_financial_status()
    send_long_message(MY_CHAT_ID, f"📊 דו\"ח תיק אוטומטי מתוזמן:\n\n{portfolio_summary}")
    send_long_message(MY_CHAT_ID, stocks_data, reply_markup=get_main_menu_keyboard())

scheduler = BackgroundScheduler()
scheduler.add_job(send_scheduled_report, 'cron', hour=12, minute=0)
scheduler.add_job(send_scheduled_report, 'cron', hour=20, minute=0)
scheduler.start()

print_rtl("\n🚀 הבוט פועל כעת בהצלחה ומקשיב...")
bot.infinity_polling()