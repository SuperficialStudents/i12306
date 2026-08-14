import sys
import unittest
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))

from ticket_flow import in_sale_window, plan_run


class TicketFlowTest(unittest.TestCase):
    def test_aug31_not_on_sale_on_aug14(self):
        self.assertFalse(in_sale_window("2026-08-31", today=date(2026, 8, 14)))

    def test_aug28_on_sale_on_aug14(self):
        self.assertTrue(in_sale_window("2026-08-28", today=date(2026, 8, 14)))

    def test_dry_run_before_sale_only_queries_test_date(self):
        plan = plan_run(
            buy=False,
            train_date="2026-08-31",
            today=date(2026, 8, 14),
            now_time=time(19, 3, 50),
            release_time=time(9, 30, 0),
        )
        self.assertTrue(plan["query_test_date"])
        self.assertFalse(plan["query_train_date"])
        self.assertFalse(plan["wait_for_release"])
        self.assertFalse(plan["purchase"])

    def test_dry_run_after_sale_queries_train_date_but_does_not_buy(self):
        plan = plan_run(
            buy=False,
            train_date="2026-08-31",
            today=date(2026, 8, 17),
            now_time=time(19, 0, 0),
            release_time=time(9, 30, 0),
        )
        self.assertTrue(plan["query_test_date"])
        self.assertTrue(plan["query_train_date"])
        self.assertFalse(plan["purchase"])

    def test_buy_before_release_waits_then_queries_train_date(self):
        plan = plan_run(
            buy=True,
            train_date="2026-08-31",
            today=date(2026, 8, 17),
            now_time=time(8, 0, 0),
            release_time=time(9, 30, 0),
        )
        self.assertFalse(plan["query_test_date"])
        self.assertTrue(plan["wait_for_release"])
        self.assertTrue(plan["query_train_date"])
        self.assertTrue(plan["purchase"])

    def test_buy_after_release_queries_train_date_without_wait(self):
        plan = plan_run(
            buy=True,
            train_date="2026-08-31",
            today=date(2026, 8, 17),
            now_time=time(9, 35, 0),
            release_time=time(9, 30, 0),
        )
        self.assertFalse(plan["wait_for_release"])
        self.assertTrue(plan["query_train_date"])
        self.assertTrue(plan["purchase"])
        self.assertFalse(plan["query_test_date"])


if __name__ == "__main__":
    unittest.main()
