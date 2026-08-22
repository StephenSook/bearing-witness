"""Records the DEMO_RUNBOOK.md walkthrough (fleet -> green -> yellow -> red ->
approve -> refusal) against the live bw_product.ui on this box, as a backup
video insurance clip. Run with BW_FX=off already set on the server (flat mode,
no WebGL/animation flake) for a deterministic recording.

This is also the verification harness: every stage asserts the exact DOM text
a judge would need to see (status string, evidence locators, the recorded
decision + reason + timestamp, the refusal's "no approval path" line) BEFORE
moving on. If any assertion fails, the script raises and no video is treated
as good -- pixels are not trusted on their own, the live application state
backing each recorded beat is.
"""
import sys
import time

from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8091"
OUT_DIR = "/tmp/claude-1000/-home-dell-bearing-witness/9a507911-e20b-475b-8ae0-3c64dc1bd249/scratchpad/video"

checks_passed = []


def check(label: str, fn) -> None:
    fn()
    checks_passed.append(label)
    print(f"  [ok] {label}")


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        viewport={"width": 1600, "height": 900},
        record_video_dir=OUT_DIR,
        record_video_size={"width": 1600, "height": 900},
    )
    page = context.new_page()

    def hold(seconds: float) -> None:
        time.sleep(seconds)

    print("1. Fleet screen")
    page.goto(BASE + "/", wait_until="networkidle")
    check("fleet headline visible",
          lambda: expect(page.locator(".bw-headline")).to_contain_text("DETECT THE CHANGE."))
    check("fleet denominator states 15 of 15 evaluated",
          lambda: expect(page.get_by_text("15 OF 15 EVALUATED")).to_be_visible())
    hold(4.5)

    print("2. W011 BASELINE (green)")
    page.goto(BASE + "/case/green", wait_until="networkidle")
    check("green case shows NO_ANOMALY_DETECTED",
          lambda: expect(page.get_by_text("NO_ANOMALY_DETECTED", exact=True).first).to_be_visible())
    check("green case window is W011",
          lambda: expect(page.get_by_text("BEARING1_3-0011-")).to_be_visible())
    hold(4.5)

    print("3. W060 (yellow)")
    page.goto(BASE + "/case/yellow", wait_until="networkidle")
    check("yellow case shows WATCH_EARLY",
          lambda: expect(page.get_by_text("WATCH_EARLY", exact=True).first).to_be_visible())
    hold(3.5)

    print("4. W155 EXPLAIN THE SPECTRUM (red)")
    page.goto(BASE + "/case/red", wait_until="networkidle")
    check("red case shows ANALYST_REVIEW_REQUIRED",
          lambda: expect(page.get_by_text("ANALYST_REVIEW_REQUIRED", exact=True).first).to_be_visible())
    hold(3.0)
    page.mouse.wheel(0, 900)
    hold(2.0)
    check("evidence locator for h1/107.03Hz present",
          lambda: expect(page.get_by_text("107.03Hz|h1")).to_be_visible())
    check("inspection draft task drafted (outer race)",
          lambda: expect(page.get_by_text("INSPECT OUTER RACE")).to_be_visible())
    check("approve/reject/defer all present pre-decision",
          lambda: (expect(page.get_by_role("button", name="APPROVE INSPECTION")).to_be_visible(),
                   expect(page.get_by_role("button", name="REJECT")).to_be_visible(),
                   expect(page.get_by_role("button", name="DEFER")).to_be_visible()))
    hold(2.0)
    page.mouse.wheel(0, 700)
    hold(2.0)

    print("5. A human says yes: fill reason, APPROVE")
    reason_text = "harmonics confirmed at 107.03/214.06/321.09 Hz, dispatching inspection"
    reason = page.get_by_label("reason (stored with the decision)")
    reason.click()
    reason.fill(reason_text)
    hold(1.5)
    page.get_by_role("button", name="APPROVE INSPECTION").click()
    check("decision toast confirms APPROVE recorded",
          lambda: expect(page.get_by_text("APPROVE recorded")).to_be_visible())
    check("case status flips to INSPECTION_APPROVED",
          lambda: expect(page.get_by_text("INSPECTION_APPROVED", exact=True).first).to_be_visible())
    check("stored decision shows APPROVE + reason text",
          lambda: (expect(page.get_by_text("DECISION · APPROVE")).to_be_visible(),
                   expect(page.get_by_text(reason_text, exact=False)).to_be_visible()))
    hold(3.5)

    print("6. W155* REFUSE WITHOUT TRUST (refusal case)")
    page.goto(BASE + "/case/refusal", wait_until="networkidle")
    check("refusal case shows ABNORMAL_LOCATION_UNCONFIRMED",
          lambda: expect(page.get_by_text("ABNORMAL_LOCATION_UNCONFIRMED", exact=True).first).to_be_visible())
    hold(3.0)
    page.mouse.wheel(0, 1400)
    hold(1.0)
    check("refusal task is VERIFY_BEARING_GEOMETRY",
          lambda: expect(page.get_by_text("VERIFY_BEARING_GEOMETRY").first).to_be_visible())
    check("no approval path line present",
          lambda: expect(page.get_by_text("NO APPROVAL PATH HERE")).to_be_visible())
    check("no APPROVE button rendered anywhere on the refusal case",
          lambda: expect(page.get_by_role("button", name="APPROVE INSPECTION")).to_have_count(0))
    hold(3.0)

    context.close()
    browser.close()

print(f"\n{len(checks_passed)} checks passed, video finalized.")
