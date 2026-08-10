#!/usr/bin/env python3
import argparse, json, os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from pipeline import ROOT, build, metrics
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        if self.path=="/api/metrics":
            body=json.dumps(metrics(),ensure_ascii=False).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
        super().do_GET()
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=int(os.getenv("PORT","8000")));args=parser.parse_args();build();
    with ThreadingHTTPServer(("0.0.0.0",args.port),Handler) as server: print(f"Metric Lab on {args.port}");server.serve_forever()
if __name__=="__main__":main()
