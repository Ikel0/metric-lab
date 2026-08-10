import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"));from pipeline import build,metrics
class PipelineTest(unittest.TestCase):
 def test_builds_mart(self):
  with tempfile.TemporaryDirectory() as folder:
   db=Path(folder)/"warehouse.db"; result=build(db); report=metrics(db)
  self.assertEqual(result["orders"],6);self.assertEqual(report["summary"]["revenue"],965.0);self.assertEqual(len(report["daily"]),3)
if __name__=="__main__":unittest.main()
