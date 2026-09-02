# Next Development Objective (Cycle 1 — Agent 1 → Agent 2)

## Feature: Transaction Confirmation & Undo Safety Layer

### Why this, why now
`handle_free_text` (bot.py) pipes any free-text message straight through
`generate_ai_response` → `apply_portfolio_action`, which mutates
`portfolio.json` immediately with no human checkpoint. A single AI misparse
(wrong qty, wrong price, wrong symbol, or an ambiguous sentence like "sold
some WDC") silently corrupts real financial data, and there is currently no
way for the user to review or reverse it. This directly conflicts with the
project's stated goal of "100% data reliability." This is the highest-value
fix available right now: it's scoped, self-contained, and protects the core
asset (the user's real portfolio ledger) without requiring new external
dependencies.

### Scope — implement in `bot.py` only (do NOT touch `portfolio.json`)

**1. Confirm-before-apply for BUY / SELL / DEPOSIT**
- In `handle_free_text`, after `generate_ai_response` returns a structured
  action with `action` in `{"BUY", "SELL", "DEPOSIT"}` (and a valid
  symbol/qty/price where relevant), do **not** call `apply_portfolio_action`
  right away. Instead:
  - Store the pending action in an in-memory dict keyed by `chat_id`, e.g.
    `PENDING_ACTIONS = {}`, with the parsed action payload and a timestamp.
  - Send a confirmation message (Hebrew, consistent with existing style)
    summarizing exactly what will happen — action type, symbol, qty, price,
    and (for BUY/SELL) the resulting new position size / avg price where
    easily computable — with an `InlineKeyboardMarkup` offering two buttons:
    `✅ אשר` (`callback_data="confirm_apply"`) and `❌ בטל`
    (`callback_data="confirm_cancel"`).
  - `action == "NONE"` (or missing symbol/qty as today) should skip
    confirmation entirely and just reply with the AI's text, same as now —
    only money-mutating actions need the checkpoint.
- Add a new `@bot.callback_query_handler` for `call.data in
  ("confirm_apply", "confirm_cancel")`:
  - On `confirm_apply`: look up the pending action for that `chat_id`, call
    `apply_portfolio_action` on it, then send the updated
    `portfolio_summary`/`stocks_data` (same as the current post-apply flow),
    and clear the pending entry.
  - On `confirm_cancel`: clear the pending entry and send a short
    "❌ הפעולה בוטלה" acknowledgement.
  - If no pending action exists for that chat (expired or already handled),
    reply that there's nothing to confirm — don't error.
- Expire pending actions after 5 minutes (check the stored timestamp before
  applying) so a stale confirmation tap from an old message can never apply
  outdated data. Also overwrite/clear any existing pending action for a
  chat when a new one is parsed, so only the most recent proposal is ever
  confirmable.
- The existing menu_3/menu_4 free-text instructions and prompt flow stay as
  they are — this only changes what happens *after* parsing, not how the
  user is asked to phrase a trade.

**2. Undo last transaction (per stock)**
- Add a new inline button, `↩️ בטל פעולה אחרונה` (`callback_data`
  `"undo_last"`), to the confirmation message sent immediately after a
  transaction is applied (step 1's post-`confirm_apply` message), so the
  user has one tap to revert a mistake they only noticed after confirming.
- Implement `undo_last_transaction(symbol)`:
  - Pop the last entry from `portfolio["stocks"][symbol]["transactions"]`.
  - Recompute that stock's `holdings` (qty, avg_purchase_price) and
    `realized_pnl` from scratch by replaying the *remaining* transaction
    list in order (reuse the same BUY/SELL math already in
    `apply_portfolio_action`) rather than trying to reverse the arithmetic —
    this avoids float-drift and stays correct even if transactions were
    edited out of order.
  - Recompute `portfolio["total_realized_pnl"]` as the sum of every stock's
    `realized_pnl` after the replay.
  - Save via the existing `save_portfolio`.
  - If the stock has no transactions left to undo, reply that there's
    nothing to undo instead of erroring.
- Wire `undo_last` in the callback handler to call this for the
  most-recently-affected symbol (track it alongside the pending/applied
  action so undo targets the right stock), then send the refreshed
  portfolio summary.

### Explicitly out of scope for this task
- No changes to `portfolio.json`'s on-disk structure/schema.
- No multi-step undo history (only the single most recent transaction per
  stock needs to be revertible).
- No new menu item for browsing full transaction history — that's a
  separate, later feature.
- Do not touch the scheduled report logic, exchange-rate menu, or any of
  the AI-analysis menus (5–12).

### Acceptance check (for Agent 3 / manual review)
- A free-text "קניתי 5 מניות NVMI ב-570 דולר" produces a confirmation
  prompt, not an immediate DB write.
- Tapping ❌ leaves `portfolio.json` unchanged.
- Tapping ✅ applies the trade and matches what today's code would have
  produced for the same input.
- Undo after a confirmed BUY restores the exact prior `holdings` and
  `realized_pnl` for that symbol.
- A confirmation tap arriving after the 5-minute window is rejected
  gracefully (no crash, no stale write).
