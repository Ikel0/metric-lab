#!/usr/bin/env python3
import argparse, json, os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from pipeline import ROOT, build, metrics

def market_context():
    url = "https://api.frankfurter.dev/v2/rates?base=EUR&quotes=USD,GBP,CHF&providers=ECB"
    try:
        with urlopen(url, timeout=5) as response:
            rows = json.load(response)
        return {"source": "Frankfurter / ECB", "rates": rows, "live": True}
    except Exception:
        return {"source": "Frankfurter / ECB", "rates": [], "live": False, "message": "Contexte externe momentanément indisponible."}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_json(self, payload, status=HTTPStatus.OK):
        body=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=="/health": return self.send_json({"status":"ok","service":"metric-lab","warehouse_ready":(ROOT / "warehouse.db").exists()})
        if self.path=="/api/metrics": return self.send_json(metrics())
        if self.path=="/api/market-context": return self.send_json(market_context())
        super().do_GET()
    def do_POST(self):
        if self.path == "/api/rebuild": return self.send_json({"status":"rebuilt", **build()}, HTTPStatus.CREATED)
        return self.send_json({"error":"unknown endpoint"}, HTTPStatus.NOT_FOUND)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=int(os.getenv("PORT","8000")));args=parser.parse_args();build();
    with ThreadingHTTPServer(("0.0.0.0",args.port),Handler) as server: print(f"Metric Lab on {args.port}");server.serve_forever()
if __name__=="__main__":main()
