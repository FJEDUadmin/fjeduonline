from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from app.entitlements import compute_entitlement


class EntitlementTests(unittest.TestCase):
    def test_company_student_always_active(self) -> None:
        ent = compute_entitlement(
            in_company_class=True,
            trial_started_at=None,
            trial_days=30,
        )
        self.assertTrue(ent.is_active)
        self.assertEqual(ent.plan, "company_student_free")
        self.assertIsNone(ent.expires_at)

    def test_trial_active_before_expiry(self) -> None:
        started = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        ent = compute_entitlement(
            in_company_class=False,
            trial_started_at=started,
            trial_days=30,
        )
        self.assertTrue(ent.is_active)
        self.assertEqual(ent.plan, "trial")
        self.assertGreaterEqual(ent.days_left, 24)

    def test_trial_inactive_after_expiry(self) -> None:
        started = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        ent = compute_entitlement(
            in_company_class=False,
            trial_started_at=started,
            trial_days=30,
        )
        self.assertFalse(ent.is_active)
        self.assertEqual(ent.reason, "試用已到期")
        self.assertEqual(ent.days_left, 0)


if __name__ == "__main__":
    unittest.main()
