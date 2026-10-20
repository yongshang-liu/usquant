#!/usr/bin/env python3
"""Run real LEAN locally, with only offline backtesting exposed."""
import argparse
import datetime
import json
import platform
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read_json_comments(text):
    out=[];inside=False;escape=False;i=0
    while i<len(text):
        ch=text[i]
        if inside:
            out.append(ch)
            if escape:escape=False
            elif ch=='\\':escape=True
            elif ch=='"':inside=False
            i+=1;continue
        if ch=='"':inside=True;out.append(ch);i+=1;continue
        if text[i:i+2]=='//':
            while i<len(text) and text[i]!='\n':i+=1
            continue
        out.append(ch);i+=1
    return json.loads(''.join(out))


def prepare(lesson,output):
    upstream=ROOT/'vendor/lean'
    config=read_json_comments((upstream/'Launcher/config.json').read_text())
    env=config['environments']['backtesting']
    config['environments']={'backtesting':env}
    config.update({'environment':'backtesting','live-mode':False,'close-automatically':True,
        'data-folder':'/Lean/Data','results-destination-folder':'/Results',
        'object-store-root':'/Results/storage','algorithm-language':'Python',
        'algorithm-type-name':'BasicTemplateAlgorithm' if lesson=='official' else 'FirstBacktest',
        'algorithm-location':'/Upstream/Algorithm.Python/BasicTemplateAlgorithm.py' if lesson=='official' else '/Lessons/01-first-backtest/main.py',
        'python-additional-paths':['/Upstream/Algorithm.Python','/Lean/Launcher/bin/Debug'],
        'job-user-id':'0','api-access-token':'','job-organization-id':'',
        'algorithm-id':'USQuant-LEAN-'+lesson,'job-project-id':'0'})
    assert config['environments']['backtesting']['live-mode'] is False
    output.mkdir(parents=True,exist_ok=True)
    path=output/'config.json';path.write_text(json.dumps(config,indent=2))
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lesson',choices=['official','first'])
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    output=ROOT/'results'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+args.lesson)
    prepare(args.lesson,output)
    lock=json.loads((ROOT/'configs/engine-lock.json').read_text())
    arch='arm64' if platform.machine().lower() in ('arm64','aarch64') else 'amd64'
    image=lock['images'][arch]
    manifest={'source_commit':subprocess.check_output(['git','-C',str(ROOT/'vendor/lean'),'rev-parse','HEAD'],text=True).strip(),
              'runtime_image':image,'architecture':arch,'lesson':args.lesson,'mode':'offline-backtesting'}
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2))
    if args.prepare_only:print(output);return
    docker=shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    command=[docker,'run','--rm','--platform','linux/'+arch,'--network','none','--cpus','2','--memory','4g',
        '--mount',f'type=bind,src={ROOT / "vendor/lean/Data"},dst=/Lean/Data,readonly',
        '--mount',f'type=bind,src={ROOT / "vendor/lean"},dst=/Upstream,readonly',
        '--mount',f'type=bind,src={ROOT / "lessons"},dst=/Lessons,readonly',
        '--mount',f'type=bind,src={output},dst=/Results',
        image,'--config','/Results/config.json']
    # No env-file, host networking, brokerage credentials or docker socket mounts.
    with (output/'console.log').open('w') as log:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:print(line,end='',flush=True);log.write(line)
        code=process.wait()
    print('Results:',output)
    if code:raise SystemExit(code)
    # LEAN may exit zero after an algorithm initialization/runtime error.
    candidates=[p for p in output.glob('*.json') if p.name not in ('config.json','provenance.json') and not p.name.endswith('-order-events.json')]
    results=[]
    for path in candidates:
        data=json.loads(path.read_text())
        if isinstance(data,dict) and 'statistics' in data:results.append(data)
    if not results or not any(r.get('statistics',{}).get('Total Orders') not in (None,'0',0) for r in results):
        raise SystemExit('No completed result with orders; inspect console.log')
    if any(r.get('runtimeError') for r in results):raise SystemExit('LEAN runtime error')
    print('Verified: actual LEAN result with orders')

if __name__=='__main__':main()
