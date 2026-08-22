import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import build, metrics
from server import market_context


class PipelineTest(unittest.TestCase):
    def test_builds_mart(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "warehouse.db"
            result = build(database)
            report = metrics(database)

        self.assertEqual(result["orders"], 6)
        self.assertEqual(report["summary"]["revenue"], 965.0)
        self.assertEqual(len(report["daily"]), 3)

    def test_market_context_returns_public_rates(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'[{"date":"2026-08-21","base":"EUR","quote":"USD","rate":1.1699}]'

        with patch("server.urlopen", return_value=Response()) as mocked:
            context = market_context()

        self.assertTrue(context["live"])
        self.assertEqual(context["rates"][0]["quote"], "USD")
        self.assertEqual(mocked.call_args.args[0].get_header("User-agent"), "Ikel-Metric-Lab/1.0 (+https://github.com/Ikel0/metric-lab)")


if __name__ == "__main__":
    unittest.main()
