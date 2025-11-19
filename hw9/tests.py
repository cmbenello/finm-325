import os
import sys
import json
import unittest

BASE_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from fix_parser import FixParser
from order import Order, OrderState
from risk_engine import RiskEngine
from logger import Logger


class TestFixParser(unittest.TestCase):
    def test_parse_valid_new_order_single(self):
        p = FixParser()
        raw = "8=FIX.4.2|35=D|55=AAPL|54=1|38=100|40=2|44=150|10=128"
        msg = p.parse(raw)
        self.assertEqual(msg["35"], "D")
        self.assertEqual(msg["55"], "AAPL")
        self.assertEqual(msg["54"], "1")
        self.assertEqual(msg["38"], "100")
        self.assertEqual(msg["40"], "2")
        self.assertEqual(msg["44"], "150")

    def test_missing_required_field_raises(self):
        p = FixParser()
        raw = "8=FIX.4.2|35=D|54=1|38=100|40=2|44=150|10=128"  # missing 55
        with self.assertRaises(ValueError):
            p.parse(raw)

    def test_limit_order_without_price_raises(self):
        p = FixParser()
        raw = "8=FIX.4.2|35=D|55=AAPL|54=1|38=100|40=2|10=128"  # missing 44
        with self.assertRaises(ValueError):
            p.parse(raw)


class TestOrderLifecycle(unittest.TestCase):
    def test_valid_transitions(self):
        o = Order("AAPL", 100, "1")
        self.assertEqual(o.state, OrderState.NEW)
        o.transition(OrderState.ACKED)
        self.assertEqual(o.state, OrderState.ACKED)
        o.transition(OrderState.FILLED)
        self.assertEqual(o.state, OrderState.FILLED)

    def test_invalid_transition_does_not_change_state(self):
        o = Order("AAPL", 100, "1")
        o.transition(OrderState.FILLED)
        self.assertEqual(o.state, OrderState.NEW)


class TestRiskEngine(unittest.TestCase):
    def test_order_within_limits_passes(self):
        r = RiskEngine(max_order_size=1000, max_position=2000)
        o = Order("AAPL", 100, "1")
        self.assertTrue(r.check(o))
        r.update_position(o)
        self.assertEqual(r.positions.get("AAPL"), 100)

    def test_order_size_exceeds_limit(self):
        r = RiskEngine(max_order_size=500, max_position=2000)
        o = Order("AAPL", 600, "1")
        with self.assertRaises(ValueError):
            r.check(o)

    def test_position_limit_exceeded(self):
        r = RiskEngine(max_order_size=1000, max_position=100)
        o1 = Order("AAPL", 80, "1")
        r.check(o1)
        r.update_position(o1)
        self.assertEqual(r.positions.get("AAPL"), 80)

        o2 = Order("AAPL", 30, "1")
        with self.assertRaises(ValueError):
            r.check(o2)


class TestLogger(unittest.TestCase):
    def setUp(self):
        # reset singleton for tests
        Logger._instance = None

    def test_log_appends_event(self):
        log = Logger(path="test_events.json")
        log.log("TestEvent", {"x": 1})
        self.assertEqual(len(log.events), 1)
        self.assertEqual(log.events[0]["type"], "TestEvent")
        self.assertEqual(log.events[0]["data"], {"x": 1})

    def test_save_writes_json_file(self):
        path = os.path.join(BASE_DIR, "test_events.json")
        if os.path.exists(path):
            os.remove(path)

        log = Logger(path=path)
        log.log("TestEvent", {"x": 1})
        log.save()

        self.assertTrue(os.path.exists(path))
        with open(path, "r") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["type"], "TestEvent")

        os.remove(path)


if __name__ == "__main__":
    unittest.main()
