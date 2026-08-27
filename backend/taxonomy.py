EXCEPTION_TAXONOMY = {
    "MISSING_BANK_ENTRY": {"severity": "high", "default_action": "human_review"},
    "MISSING_ORDER": {"severity": "high", "default_action": "leave_unresolved"},
    "AMOUNT_MISMATCH": {"severity": "high", "default_action": "human_review"},
    "FEE_VARIANCE": {"severity": "medium", "default_action": "human_review"},
    "TAX_VARIANCE": {"severity": "high", "default_action": "human_review"},
    "DUPLICATE": {"severity": "high", "default_action": "human_review"},
    "TIMING_DIFFERENCE": {"severity": "low", "default_action": "probable_match"},
    "PARTIAL_REFUND": {"severity": "medium", "default_action": "verify_refund_linkage"},
    "DISPUTE_ADJUSTMENT": {"severity": "high", "default_action": "human_review"},
    "AMBIGUOUS_MATCH": {"severity": "medium", "default_action": "human_review"},
    "IDENTIFIER_CONFLICT": {"severity": "critical", "default_action": "reject_auto_match"},
    "INVALID_SOURCE": {"severity": "medium", "default_action": "reject_row"},
    "UNEXPECTED_ADJUSTMENT": {"severity": "high", "default_action": "human_review"},
    "API_DATA_GAP": {"severity": "medium", "default_action": "use_fixture"},
}

ALLOWED_RECOMMENDED_ACTIONS = [
    "human_review", "leave_unresolved", "probable_match", "verify_refund_linkage",
    "reject_auto_match", "reject_row", "use_fixture", "request_data", "no_action",
]

RESOLUTION_ACTIONS = [
    "approve_match", "reject_match", "split_match", "merge_match", "request_data", "leave_unresolved",
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
