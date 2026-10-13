"""Local-only recording development server; never deploy this as a public service."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server import Handler, ThreadingHTTPServer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8768)
    args=parser.parse_args()
    token=secrets.token_urlsafe(20)
    destination=ROOT / '.agent' / 'recording'
    destination.mkdir(parents=True,exist_ok=True)

    class RecordingHandler(Handler):
        def do_POST(self):
            if urlsplit(self.path).path != '/__recording/'+token:
                return super().do_POST()
            if self.client_address[0]!='127.0.0.1' or self.headers.get('Origin')!=f'http://127.0.0.1:{args.port}':
                self.json(403,{'error':'Only the local recording page may save this recording'})
                return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<160*1024*1024 or not self.headers.get('Content-Type','').startswith('video/webm'):
                self.json(400,{'error':'Expected bounded WebM recording'})
                return
            temporary=destination/'gomoku-demo.webm.part'
            remaining=length
            with temporary.open('wb') as handle:
                while remaining:
                    chunk=self.rfile.read(min(1024*1024,remaining))
                    if not chunk:
                        raise ConnectionError('Recording upload ended early')
                    handle.write(chunk)
                    remaining-=len(chunk)
            target=destination/'gomoku-demo.webm'
            temporary.replace(target)
            meta={'bytes':length,'frames_rendered':self.headers.get('X-Recording-Frames'),'source':'real application renderer captureStream + actual stage scenery','url_path':'game.html?record=<local-token>'}
            (destination/'capture.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            self.json(201,{'status':'saved','bytes':length})
            print(f'RECORDING_SAVED={target}',flush=True)

    http=ThreadingHTTPServer(('127.0.0.1',args.port),RecordingHandler)
    print(f'RECORDING_URL=http://127.0.0.1:{args.port}/game.html?record={token}',flush=True)
    print(f'RECORDING_OUTPUT={destination}',flush=True)
    http.serve_forever()


if __name__=='__main__':
    main()
