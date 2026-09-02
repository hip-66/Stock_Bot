"""
Continuous 4-agent pipeline for the Stock Bot project.

Cycle: Agent 1 (ideas) -> Agent 2 (build) -> Agent 3 (QA) -> Agent 4 (bug fix) -> repeat.
Each agent is one headless `claude -p` call; role instructions live in claude/CLAUDE.md
so this script and the prompts stay in sync automatically when CLAUDE.md changes.

SAFETY MODEL - read before changing:
The agents never touch this checked-out folder (the live one run_bot.bat/check_bot.bat
use). All their work happens in an isolated git worktree (WORKSPACE_DIR, a sibling
folder on its own `pipeline-dev` branch). After Agent 2 and Agent 4, changes are
committed *there* with the agent's own explanation as the commit body and pushed to
GitHub on `pipeline-dev`. Nothing ever auto-merges into `main` and nothing ever touches
the live folder or portfolio.json - promoting reviewed changes to production is a
separate, human-run step (see claude/approve_and_deploy.bat). Do not change cwd for
run_claude_agent() to PROJECT_DIR/live folder; that would defeat this isolation.

INTERRUPTION SAFETY: an agent call (run_claude_agent) is never interrupted by the
scheduled-pause check below - that check only ever runs *between* cycles, after the
previous cycle's work is already committed and pushed. Killing the window yourself
(Ctrl+C / stop_pipeline.bat) can still land mid-agent; that's fine too because nothing
is committed until an agent finishes, so at worst the workspace has some uncommitted
scratch changes - claude/reject_and_reset.bat wipes those back to a clean state. The
live folder is never at risk either way.

Runs forever. On a usage/rate limit it sleeps and retries instead of stopping.
Stop with Ctrl+C, or via claude/stop_pipeline.bat from another window.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # live folder - never written to by agents

# Isolated git worktree the agents actually work in. Override via env var if you move it.
WORKSPACE_DIR = os.environ.get(
    "PIPELINE_WORKSPACE_DIR",
    os.path.join(os.path.dirname(PROJECT_DIR), "Stock_Bot_pipeline_workspace"),
)
WORKSPACE_BRANCH = os.environ.get("PIPELINE_BRANCH", "pipeline-dev")

# Everything the pipeline generates at runtime lives in one subfolder, so claude/ itself
# only ever shows files you actually interact with (scripts + docs), not runtime noise.
STATE_DIR = os.path.join(SCRIPT_DIR, "state")
os.makedirs(STATE_DIR, exist_ok=True)
LOG_FILE = os.path.join(STATE_DIR, "pipeline.log")
STATUS_FILE = os.path.join(STATE_DIR, "pipeline_status.json")
PID_FILE = os.path.join(STATE_DIR, "pipeline.pid")
CONTINUE_SIGNAL_FILE = os.path.join(STATE_DIR, "continue_signal")

CLAUDE_EXE = shutil.which("claude")
_GIT_FALLBACK = r"C:\Program Files\Git\cmd\git.exe"
GIT_EXE = shutil.which("git") or (_GIT_FALLBACK if os.path.exists(_GIT_FALLBACK) else None)

# Tunables - override via environment variables, no code changes needed.
PERMISSION_MODE = os.environ.get("PIPELINE_PERMISSION_MODE", "bypassPermissions")
MAX_BUDGET_USD_PER_CALL = os.environ.get("PIPELINE_MAX_BUDGET_USD", "5")
AGENT_TIMEOUT_SECONDS = int(os.environ.get("PIPELINE_AGENT_TIMEOUT", str(45 * 60)))
CYCLE_SLEEP_SECONDS = int(os.environ.get("PIPELINE_CYCLE_SLEEP", "15"))
# Unset by default -> inherits whatever effort level is set in ~/.claude/settings.json.
# A single call at "xhigh" can take several minutes and cost noticeably more; set
# PIPELINE_EFFORT=medium (for example) to trade depth for speed/cost on this pipeline.
EFFORT = os.environ.get("PIPELINE_EFFORT", "")

ERROR_BACKOFF_MIN = 60
ERROR_BACKOFF_MAX = 1800
RATE_LIMIT_BACKOFF_MIN = int(os.environ.get("PIPELINE_RATE_LIMIT_BACKOFF", str(15 * 60)))
RATE_LIMIT_BACKOFF_MAX = 3600

RATE_LIMIT_MARKERS = (
    "rate limit", "too many requests", "limit reached", "usage limit",
    "quota exceeded", "overloaded", "resets at",
)

# --- Scheduled review pause -------------------------------------------------
# On these weekdays, the pipeline stops starting *new* cycles once the lead-in window
# opens (PAUSE_HOUR minus PAUSE_LEAD_MINUTES) and pauses at the next cycle boundary -
# never mid-agent. It pings you on Telegram and waits for claude/continue_pipeline.bat.
PAUSE_ENABLED = os.environ.get("PIPELINE_PAUSE_ENABLED", "1").strip().lower() not in ("0", "false", "no")
PAUSE_DAYS = {
    d.strip().lower() for d in os.environ.get("PIPELINE_PAUSE_DAYS", "Sunday,Thursday").split(",") if d.strip()
}
PAUSE_HOUR = int(os.environ.get("PIPELINE_PAUSE_HOUR", "10"))  # 24h, local time
PAUSE_LEAD_MINUTES = int(os.environ.get("PIPELINE_PAUSE_LEAD_MINUTES", "60"))
PAUSE_POLL_SECONDS = int(os.environ.get("PIPELINE_PAUSE_POLL_SECONDS", "30"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pipeline")


def write_status(**fields):
    status = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status = json.load(f)
        except (json.JSONDecodeError, OSError):
            status = {}
    status.update(fields)
    status["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def ensure_workspace_ready():
    if not GIT_EXE:
        raise RuntimeError("git was not found - install it before running the pipeline.")
    if not os.path.isdir(WORKSPACE_DIR):
        raise RuntimeError(
            f"Pipeline workspace {WORKSPACE_DIR} does not exist. Create it once with:\n"
            f'  git -C "{PROJECT_DIR}" worktree add -b {WORKSPACE_BRANCH} "{WORKSPACE_DIR}" main'
        )
    branch = subprocess.run(
        [GIT_EXE, "branch", "--show-current"],
        cwd=WORKSPACE_DIR, capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    if branch != WORKSPACE_BRANCH:
        raise RuntimeError(
            f"{WORKSPACE_DIR} is on branch '{branch}', expected '{WORKSPACE_BRANCH}'. "
            "Refusing to run agents there until that's fixed - this is the isolation "
            "that keeps unapproved changes out of the live/main branch."
        )


def agent_summary(payload):
    text = (payload or {}).get("result")
    if not text:
        return "(no summary text returned)"
    text = str(text).strip()
    return text[:3000] + ("\n...[truncated]" if len(text) > 3000 else "")


def git_checkpoint_and_push(short_message, payload):
    """Commit in the isolated workspace (never the live folder) and push to GitHub
    on WORKSPACE_BRANCH. Never touches `main` - promotion to production is a separate,
    human-run step (see approve_and_deploy.bat)."""
    try:
        subprocess.run([GIT_EXE, "add", "-A"], cwd=WORKSPACE_DIR, capture_output=True,
                        text=True, timeout=60)
        commit_message = short_message + "\n\n" + agent_summary(payload)
        result = subprocess.run(
            [GIT_EXE, "commit", "-m", commit_message],
            cwd=WORKSPACE_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
        if result.returncode != 0:
            log.info("Git checkpoint skipped (nothing to commit): %s", short_message)
            return None
        commit_hash = subprocess.run(
            [GIT_EXE, "rev-parse", "--short", "HEAD"],
            cwd=WORKSPACE_DIR, capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        log.info("Git checkpoint created (%s): %s", commit_hash, short_message)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Git checkpoint failed: %s", exc)
        return None

    try:
        push = subprocess.run(
            [GIT_EXE, "push", "origin", WORKSPACE_BRANCH],
            cwd=WORKSPACE_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
        if push.returncode == 0:
            log.info("Pushed %s to origin/%s", commit_hash, WORKSPACE_BRANCH)
        else:
            log.warning("Push to GitHub failed (will retry next checkpoint): %s",
                        (push.stdout + push.stderr)[:500])
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Push to GitHub failed (will retry next checkpoint): %s", exc)

    return commit_hash


def run_claude_agent(agent_name, prompt_instruction):
    if not CLAUDE_EXE:
        raise RuntimeError(
            "The 'claude' CLI was not found on PATH. Install it with: "
            "npm install -g @anthropic-ai/claude-code"
        )

    error_backoff = ERROR_BACKOFF_MIN
    rate_limit_backoff = RATE_LIMIT_BACKOFF_MIN
    attempt = 0
    while True:
        attempt += 1
        log.info("--- %s (attempt %d) ---", agent_name, attempt)
        cmd = [
            CLAUDE_EXE, "-p", prompt_instruction,
            "--output-format", "json",
            "--permission-mode", PERMISSION_MODE,
            "--max-budget-usd", str(MAX_BUDGET_USD_PER_CALL),
        ]
        if EFFORT:
            cmd += ["--effort", EFFORT]
        try:
            result = subprocess.run(
                cmd,
                cwd=WORKSPACE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            log.error("%s timed out after %ds - retrying in %ds",
                       agent_name, AGENT_TIMEOUT_SECONDS, error_backoff)
            time.sleep(error_backoff)
            error_backoff = min(error_backoff * 2, ERROR_BACKOFF_MAX)
            continue
        except OSError as exc:
            log.error("Failed to launch claude CLI: %s - retrying in %ds", exc, error_backoff)
            time.sleep(error_backoff)
            error_backoff = min(error_backoff * 2, ERROR_BACKOFF_MAX)
            continue

        raw_output = (result.stdout or "") + (result.stderr or "")

        payload = None
        if result.stdout:
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                payload = None

        if payload is not None and result.returncode == 0 and not payload.get("is_error"):
            denials = payload.get("permission_denials") or []
            if denials:
                log.warning("%s: %d tool call(s) were denied: %s",
                             agent_name, len(denials), denials)
            log.info("%s completed OK (cost: $%.4f)",
                       agent_name, payload.get("total_cost_usd") or 0)
            return payload

        lowered = raw_output.lower()
        if any(marker in lowered for marker in RATE_LIMIT_MARKERS):
            log.warning("%s hit a usage/rate limit. Sleeping %ds before retrying...",
                         agent_name, rate_limit_backoff)
            write_status(state="waiting_for_rate_limit", last_agent=agent_name)
            time.sleep(rate_limit_backoff)
            rate_limit_backoff = min(rate_limit_backoff * 2, RATE_LIMIT_BACKOFF_MAX)
            continue

        rate_limit_backoff = RATE_LIMIT_BACKOFF_MIN
        log.error("%s failed (rc=%s): %s - retrying in %ds",
                   agent_name, result.returncode, raw_output[:500], error_backoff)
        time.sleep(error_backoff)
        error_backoff = min(error_backoff * 2, ERROR_BACKOFF_MAX)


# --- Scheduled review pause -------------------------------------------------

def load_live_telegram_credentials():
    """Reads TELEGRAM_TOKEN/MY_CHAT_ID from the LIVE folder's .env - read-only, this
    never starts or touches bot.py itself, just reuses its token to send one message."""
    env_path = os.path.join(PROJECT_DIR, ".env")
    values = {}
    if not os.path.exists(env_path):
        return None, None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values.get("TELEGRAM_TOKEN"), values.get("MY_CHAT_ID")


def send_telegram_notification(text):
    token, chat_id = load_live_telegram_credentials()
    if not token or not chat_id:
        log.warning("No Telegram credentials in .env - skipping notification: %s", text)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15)
        log.info("Sent Telegram notification.")
    except (urllib.error.URLError, OSError) as exc:
        log.warning("Failed to send Telegram notification: %s", exc)


def pause_window_open(now):
    """True from (PAUSE_HOUR - PAUSE_LEAD_MINUTES) onward on a configured weekday,
    through the rest of that day - so once we're due for a pause, we stay due for it
    (we just won't start a NEW cycle) until it actually happens."""
    if not PAUSE_ENABLED:
        return False
    if now.strftime("%A").lower() not in PAUSE_DAYS:
        return False
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        hours=PAUSE_HOUR, minutes=-PAUSE_LEAD_MINUTES
    )
    return now >= window_start


def wait_for_resume_decision(cycle):
    if os.path.exists(CONTINUE_SIGNAL_FILE):
        os.remove(CONTINUE_SIGNAL_FILE)  # stale leftover from before - don't skip the pause

    log.info("Scheduled review pause reached after cycle %d. Waiting for continue_pipeline.bat ...", cycle)
    write_status(state="paused_for_review", cycle=cycle)
    send_telegram_notification(
        "\u23f8\ufe0f \u05d4\u05e4\u05d9\u05d9\u05e4\u05dc\u05d9\u05d9\u05df \u05e1\u05d9\u05d9\u05dd \u05de\u05d7\u05d6\u05d5\u05e8 \u05d5\u05e2\u05e6\u05e8 \u05dc\u05d1\u05d3\u05d9\u05e7\u05d4 \u05de\u05ea\u05d5\u05d6\u05de\u05e0\u05ea.\n"
        "\u05d1\u05d3\u05d5\u05e7 \u05d0\u05ea claude/review_changes.bat \u05e2\u05dc \u05d4\u05de\u05d7\u05e9\u05d1.\n"
        "\u05dc\u05d4\u05de\u05e9\u05d9\u05da: claude/continue_pipeline.bat\n"
        "\u05dc\u05e2\u05e6\u05d5\u05e8: claude/stop_pipeline.bat"
    )
    while not os.path.exists(CONTINUE_SIGNAL_FILE):
        time.sleep(PAUSE_POLL_SECONDS)
    os.remove(CONTINUE_SIGNAL_FILE)
    log.info("Resume signal received - continuing.")
    write_status(state="resumed")


def acquire_lock():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r", encoding="utf-8") as f:
            old_pid = f.read().strip()
        log.error(
            "%s already exists (pid=%s) - another instance may be running. "
            "Delete that file first if it isn't.", PID_FILE, old_pid,
        )
        sys.exit(1)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def release_lock():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def main():
    acquire_lock()
    try:
        ensure_workspace_ready()
    except RuntimeError as exc:
        log.error(str(exc))
        release_lock()
        sys.exit(1)
    log.info(
        "Pipeline starting. claude=%s git=%s live_folder=%s workspace=%s (branch %s) permission_mode=%s",
        CLAUDE_EXE, GIT_EXE, PROJECT_DIR, WORKSPACE_DIR, WORKSPACE_BRANCH, PERMISSION_MODE,
    )
    if PAUSE_ENABLED:
        log.info("Scheduled pause: %s at %02d:00 (opens %d min early)",
                  ", ".join(sorted(PAUSE_DAYS)), PAUSE_HOUR, PAUSE_LEAD_MINUTES)

    cycle = 0
    total_cost = 0.0
    last_pause_date = None
    try:
        while True:
            now = datetime.now()
            if pause_window_open(now) and last_pause_date != now.date().isoformat():
                last_pause_date = now.date().isoformat()
                wait_for_resume_decision(cycle)

            cycle += 1
            write_status(cycle=cycle, state="running", total_cost_usd=round(total_cost, 4))
            log.info("========== CYCLE %d ==========", cycle)

            r1 = run_claude_agent(
                "Agent 1 (Product & Ideas)",
                "Take on the role of Agent 1 (Product Strategy & Feature Expansion) as defined "
                "in claude/CLAUDE.md and execute it now for this cycle.",
            )
            total_cost += (r1 or {}).get("total_cost_usd") or 0
            write_status(cycle=cycle, state="agent1_done", total_cost_usd=round(total_cost, 4))

            r2 = run_claude_agent(
                "Agent 2 (Developer)",
                "Take on the role of Agent 2 (Developer & Core Maintainer) as defined in "
                "claude/CLAUDE.md and execute it now for this cycle.",
            )
            total_cost += (r2 or {}).get("total_cost_usd") or 0
            commit = git_checkpoint_and_push(
                f"Cycle {cycle}: Agent 2 build ({datetime.now():%Y-%m-%d %H:%M})", r2)
            write_status(cycle=cycle, state="agent2_done", total_cost_usd=round(total_cost, 4),
                         last_commit=commit)

            r3 = run_claude_agent(
                "Agent 3 (QA Tester)",
                "Take on the role of Agent 3 (QA & Comprehensive Tester) as defined in "
                "claude/CLAUDE.md and execute it now for this cycle.",
            )
            total_cost += (r3 or {}).get("total_cost_usd") or 0
            write_status(cycle=cycle, state="agent3_done", total_cost_usd=round(total_cost, 4))

            r4 = run_claude_agent(
                "Agent 4 (Bug Fixer)",
                "Take on the role of Agent 4 (Root Cause Bug Fixer) as defined in "
                "claude/CLAUDE.md and execute it now for this cycle.",
            )
            total_cost += (r4 or {}).get("total_cost_usd") or 0
            commit = git_checkpoint_and_push(
                f"Cycle {cycle}: Agent 4 fixes ({datetime.now():%Y-%m-%d %H:%M})", r4)
            write_status(cycle=cycle, state="cycle_complete", total_cost_usd=round(total_cost, 4),
                         last_commit=commit)

            log.info("Cycle %d complete. Total spend so far: $%.2f. Sleeping %ds.",
                       cycle, total_cost, CYCLE_SLEEP_SECONDS)
            time.sleep(CYCLE_SLEEP_SECONDS)
    except KeyboardInterrupt:
        log.info("Pipeline stopped by user (Ctrl+C).")
        write_status(state="stopped_by_user")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
