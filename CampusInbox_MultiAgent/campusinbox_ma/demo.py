"""DEMO MODE runner for the multi-agent CampusInbox.

DEMO MODE: mails are local sample files, sign-in is simulated, and nothing is
ever sent anywhere. This mirrors the original MVP's honest demo framing.
"""
from __future__ import annotations

import argparse
import pathlib

from .agents.base import State
from .coordinator import Coordinator
from .chatbot import ChatbotAgent
from .tools.core import Mail

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "sample_mails"


def load_demo_mails() -> list[Mail]:
    mails = []
    for path in sorted(DATA.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        head, body = text.split("\n\n", 1)
        fields = dict(line.split(": ", 1) for line in head.splitlines())
        mails.append(Mail(subject=fields["Subject"], sender=fields["From"],
                          date_header=fields["Date"], body=body.strip(),
                          source="demo"))
    return mails


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="skip interactive approval (deadlines stay 'waiting')")
    ap.add_argument("--chat", action="store_true", help="open the chatbot after the pipeline")
    ap.add_argument("--no-live-web", action="store_true", help="force chatbot web search into demo fallback")
    args = ap.parse_args()

    print("=== CampusInbox MULTI-AGENT - DEMO MODE (simulated sign-in, sample mails, nothing is sent) ===\n")
    state = State(mails=load_demo_mails())
    coord = Coordinator()
    state = coord.run(state)

    print("--- agent trace ---")
    for line in state.log:
        print(line)

    print("\n--- proposed deadlines (by course) ---")
    for item in state.planned:
        dl = item["deadline"]
        print(f"[{dl.course}] {dl.what} -> {dl.due}")
        print(f"   proof: \"{dl.quote}\"")
        print(f"   reminder: {item['reminder']['text']} ({item['reminder']['status']})")
        if "note" in item:
            n = item["note"]
            print(f"   note: {n['priority']} priority, {n['days_left']} day(s) left - {n['first_step']}")

    if state.rejected:
        print("\n--- rejected by agents ---")
        for r in state.rejected:
            print(f"[{r['stage']}] {r['reason']}: {r['sentence'][:70]}")

    if not args.auto:
        state = coord.approval_gate(state)

    if args.chat:
        bot = ChatbotAgent(state, live_web=not args.no_live_web)
        print("\n--- chatbot (ReAct loop: Thought / Action / Observation; type 'quit' to exit) ---")
        while True:
            try:
                q = input("you: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in ("quit", "exit", ""):
                break
            print(bot.ask(q))


if __name__ == "__main__":
    main()
