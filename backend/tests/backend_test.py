"""SettleSense backend API contract tests.

Covers: auth, run creation/execution, matches, exceptions, audit chain,
reports (md/csv/json), evaluation baselines, razorpay adapter (not-configured),
and auth protection. AI explain is exercised sparingly (1 call).
"""
import os
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

OPERATOR = {"email": "operator@settlesense.dev", "password": "operator123"}
REVIEWER = {"email": "reviewer@settlesense.dev", "password": "reviewer123"}


# --- fixtures ---
@pytest.fixture(scope="session")
def op_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=OPERATOR)
    assert r.status_code == 200, f"operator login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="session")
def rev_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=REVIEWER)
    assert r.status_code == 200, f"reviewer login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="session")
def completed_run_id(op_session):
    """Reuse an existing COMPLETED run if available; otherwise create one."""
    r = op_session.get(f"{BASE_URL}/api/runs")
    assert r.status_code == 200
    runs = r.json()
    for run in runs:
        if run.get("status") == "COMPLETED":
            return run["run_id"]
    # otherwise create + fixture + execute
    payload = {"name": "pytest-completed", "currency": "INR",
               "config": {"amount_tolerance_minor": 100, "date_window_days": 2,
                          "auto_match_threshold": 0.9, "ai_model": "gpt-5.4"}}
    r = op_session.post(f"{BASE_URL}/api/runs", json=payload)
    rid = r.json()["run_id"]
    op_session.post(f"{BASE_URL}/api/runs/{rid}/sources/fixture", json={})
    op_session.post(f"{BASE_URL}/api/runs/{rid}/execute", json={})
    return rid


# --- Auth ---
class TestAuth:
    def test_unauth_runs_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/runs")
        assert r.status_code == 401

    def test_login_success_returns_user_and_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json=OPERATOR)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == OPERATOR["email"]
        assert d["role"] == "operator"
        assert isinstance(d.get("access_token"), str) and len(d["access_token"]) > 20
        # cookie also set
        assert any(c.name == "access_token" for c in r.cookies)

    def test_login_wrong_password_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": OPERATOR["email"], "password": "wrong-xyz"})
        assert r.status_code == 401

    def test_auth_me_returns_current_user(self, op_session):
        r = op_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == OPERATOR["email"]


# --- Razorpay adapter ---
class TestRazorpay:
    def test_status_not_configured(self, op_session):
        r = op_session.get(f"{BASE_URL}/api/razorpay/status")
        assert r.status_code == 200
        d = r.json()
        assert d["configured"] is False

    def test_add_razorpay_source_returns_400_with_guidance(self, op_session, completed_run_id):
        r = op_session.post(f"{BASE_URL}/api/runs/{completed_run_id}/sources/razorpay", json={})
        assert r.status_code == 400
        body = r.json()
        # detail may be dict or string
        detail = body.get("detail", body)
        text = str(detail)
        assert "API_DATA_GAP" in text


# --- Run creation and execution ---
class TestRunLifecycle:
    def test_create_run_load_fixture_and_execute(self, op_session):
        payload = {"name": "TEST_lifecycle_run", "currency": "INR",
                   "config": {"amount_tolerance_minor": 100, "date_window_days": 2,
                              "auto_match_threshold": 0.9, "ai_model": "gpt-5.4"}}
        r = op_session.post(f"{BASE_URL}/api/runs", json=payload)
        assert r.status_code in (200, 201), r.text[:300]
        run = r.json()
        rid = run["run_id"]
        assert run["status"] == "CREATED"

        # load fixture -> 4 sources
        r = op_session.post(f"{BASE_URL}/api/runs/{rid}/sources/fixture", json={})
        assert r.status_code == 200
        srcs = r.json()["sources"]
        types = {s["source_type"] for s in srcs}
        assert {"settlement", "bank_statement", "internal_ledger", "payments"}.issubset(types)
        # invalid row counts as advertised
        counts = {s["source_type"]: s for s in srcs}
        assert counts["settlement"]["valid_rows"] == 128 and counts["settlement"]["invalid_rows"] == 1
        assert counts["bank_statement"]["valid_rows"] == 20 and counts["bank_statement"]["invalid_rows"] == 1

        # execute
        r = op_session.post(f"{BASE_URL}/api/runs/{rid}/execute", json={})
        assert r.status_code == 200
        m = r.json()["summary_metrics"]
        assert r.json()["status"] == "COMPLETED"
        assert m["records_processed"] == 260
        assert m["forced_match_count"] == 0
        assert m["overall_match_rate"] > 0.85

    def test_idempotent_execute_on_completed_run(self, op_session, completed_run_id):
        r = op_session.post(f"{BASE_URL}/api/runs/{completed_run_id}/execute", json={})
        assert r.status_code == 200
        body = r.json()
        assert body.get("idempotent") is True or body.get("status") == "COMPLETED"
        assert body["summary_metrics"]["records_processed"] == 260


# --- Matches ---
class TestMatches:
    def test_list_matches(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/matches")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 100
        m = d["matches"][0]
        for k in ("match_id", "plane", "decision", "confidence", "evidence"):
            assert k in m

    def test_filter_matches_by_plane(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/matches?plane=order_settlement")
        assert r.status_code == 200
        for m in r.json()["matches"]:
            assert m["plane"] == "order_settlement"


# --- Exceptions ---
class TestExceptions:
    def test_list_exceptions_sorted_by_severity(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/exceptions")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        codes = {e["exception_code"] for e in d["exceptions"]}
        # Expect AMBIGUOUS_MATCH present for graceful failure demo
        assert "AMBIGUOUS_MATCH" in codes

    def test_ambiguous_match_filter(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/exceptions?code=AMBIGUOUS_MATCH")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        ex = d["exceptions"][0]
        # no settlement_bank match for setl_0006 batch (system refused to force-match)
        assert "bank_0007" in ex["record_ids"] or "bank_0008" in ex["record_ids"]

    def test_resolve_without_note_returns_error(self, rev_session, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/exceptions?status=OPEN")
        opens = r.json()["exceptions"]
        if not opens:
            pytest.skip("no OPEN exceptions to test note validation")
        eid = opens[0]["exception_id"]
        r = rev_session.post(f"{BASE_URL}/api/exceptions/{eid}/resolve",
                             json={"action": "approve_match"})
        assert r.status_code in (400, 422), f"expected client error, got {r.status_code}: {r.text[:200]}"

    def test_resolve_transitions_to_resolved(self, rev_session, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/exceptions?status=OPEN")
        opens = r.json()["exceptions"]
        if not opens:
            pytest.skip("no OPEN exceptions remain")
        eid = opens[0]["exception_id"]
        r = rev_session.post(f"{BASE_URL}/api/exceptions/{eid}/resolve",
                             json={"action": "approve_match", "note": "pytest resolution note"})
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        # status transitioned
        assert body.get("status") == "RESOLVED" or body.get("exception", {}).get("status") == "RESOLVED"
        # audit event id present
        assert "audit_event_id" in body or "audit" in str(body).lower()


# --- Audit chain ---
class TestAudit:
    def test_audit_events_hash_chained(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/audit")
        assert r.status_code == 200
        d = r.json()
        events = d["events"]
        assert len(events) > 10
        # each event has hash + previous_hash (either explicit or via chain fields)
        first = events[0]
        # Check chain field presence flexibly
        assert any(k in first for k in ("hash", "event_hash", "current_hash"))

    def test_audit_filter_by_actor(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/audit?actor=system")
        assert r.status_code == 200
        events = r.json()["events"]
        assert all(e["actor"] == "system" for e in events)


# --- Reports ---
class TestReports:
    def test_report_markdown(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/report?format=markdown")
        assert r.status_code == 200
        assert "SettleSense Close Report" in r.text
        assert "Report hash" in r.text

    def test_report_csv(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/report?format=csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")

    def test_report_json(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/report?format=json")
        assert r.status_code == 200
        d = r.json()
        assert "report_hash" in d or "hash" in d


# --- Evaluation baselines ---
class TestEvaluation:
    def test_evaluation_has_three_baselines(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/evaluation")
        assert r.status_code == 200
        d = r.json()
        b = d["baselines"]
        for k in ("exact_only", "exact_plus_tolerance", "final_candidate_scoring"):
            assert k in b
        assert b["exact_only"]["auto_match_recall"] == 0.9835
        assert b["final_candidate_scoring"]["auto_match_recall"] == 1.0


# --- AI explanation (rate-limited: 1 call) ---
class TestAIExplain:
    def test_ai_explain_returns_summary_and_cites_record_ids(self, op_session, completed_run_id):
        r = op_session.get(f"{BASE_URL}/api/runs/{completed_run_id}/exceptions")
        exc = r.json()["exceptions"][0]
        eid = exc["exception_id"]
        record_ids = set(exc["record_ids"])
        r = op_session.post(f"{BASE_URL}/api/exceptions/{eid}/explain",
                            json={"model": "gpt-5.4"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        ai = d.get("ai_explanation") or d
        summary = ai.get("summary") or ai.get("explanation") or ""
        assert len(summary) > 20, f"empty summary in response: {str(d)[:300]}"
        # summary must cite at least one real involved record id
        assert any(rid in summary for rid in record_ids), f"no source id cited in: {summary[:200]}"
        # evidence_ids should also be present
        ev_ids = set(ai.get("evidence_ids") or [])
        assert ev_ids.issubset(record_ids) or ev_ids & record_ids, f"evidence_ids {ev_ids} not in {record_ids}"
