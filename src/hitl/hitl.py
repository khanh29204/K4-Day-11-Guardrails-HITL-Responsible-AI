"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 11: Confidence Router
  TODO 12: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 11: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response, confidence, action_type="general"):
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(action="escalate", confidence=confidence,
                reason=f"High-risk action: {action_type}", priority="high",
                requires_human=True)
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(action="auto_send", confidence=confidence,
                reason="High confidence", priority="low", requires_human=False)
        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(action="queue_review", confidence=confidence,
                reason="Medium confidence — needs review", priority="normal",
                requires_human=True)
        return RoutingDecision(action="escalate", confidence=confidence,
            reason="Low confidence — escalating", priority="high",
            requires_human=True)


# ============================================================
# TODO 12: Design 3 HITL decision points + a review lifecycle
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
# - approval_path: What approve/reject/timeout decision is recorded?
# - audit_fields: Which correlation ID, intent and proposed action/diff are logged?
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "High-Value Money Transfer Verification",
        "trigger": "User requests transfer_money action exceeding 10,000,000 VND or targeting new external beneficiary",
        "hitl_model": "human-in-the-loop",
        "context_needed": "User request text, source account ID, beneficiary account number, beneficiary name, transfer amount, risk score, user transaction history",
        "example": "Customer requests to transfer 50,000,000 VND to an external bank account for the first time via chat assistant.",
        "approval_path": "Approve: execute transfer with HITL-ID logged; Reject: notify user & cancel; Timeout (15m): auto-cancel transfer request.",
        "audit_fields": "correlation_id, request_id, reviewer_id, user_id, intent='transfer_money', payload_diff, approval_status, timestamp",
    },
    {
        "id": 2,
        "name": "Account Closure & Credential Changes",
        "trigger": "User requests close_account, change_password, or update_personal_info",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Customer verification status, request type, current contact details, requested changes, auth tokens, device footprint",
        "example": "Customer requests to change their registered phone number and close secondary savings account.",
        "approval_path": "Approve: apply sensitive account change with recorded approval ID; Reject: keep existing credentials; Timeout: request expires.",
        "audit_fields": "correlation_id, request_id, reviewer_id, user_id, intent='account_modification', old_vs_new_diff, approval_status, timestamp",
    },
    {
        "id": 3,
        "name": "Low Confidence / Ambiguous Banking Action",
        "trigger": "LLM confidence score < 0.7 on banking transaction request, or LLM-as-Judge returns borderline verdict",
        "hitl_model": "human-as-tiebreaker",
        "context_needed": "Original user query, full chat history, LLM proposed response, confidence score, safety judge verdict & reason",
        "example": "Customer sends a complex query about loan restructuring that agent is only 55% confident in answering correctly.",
        "approval_path": "Approve: send proposed response; Edit & Approve: agent response modified by human reviewer before sending; Reject: human agent takes over chat session.",
        "audit_fields": "correlation_id, request_id, reviewer_id, user_id, confidence_score, original_response, edited_response, approval_status, timestamp",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
