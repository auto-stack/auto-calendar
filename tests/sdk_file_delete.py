"""Execute the production deletion confirmation against owned file fixtures."""
import argparse,hashlib,json,os
from pathlib import Path
import subprocess,tempfile

parser=argparse.ArgumentParser()
parser.add_argument('--auto',required=True)
parser.add_argument('--scratch',required=True)
args=parser.parse_args()
if os.name != 'nt':
    raise RuntimeError('The share-deny deletion fixture requires Windows')
repo=Path(__file__).resolve().parents[1]
source=repo/'src/back/repository.at'
text=source.read_text(encoding='utf-8')
start=text.index('fn delete_confirmed(');end=text.index('{',start)+1;depth=1
while depth:
    depth+=(text[end]=='{')-(text[end]=='}');end+=1
helper=text[start:end]
base=Path(args.scratch).resolve();base.mkdir(parents=True,exist_ok=True)
run=Path(tempfile.mkdtemp(prefix='confirmed-delete-',dir=base)).resolve()
assert run.is_relative_to(base)
existing=run/'existing.txt';existing.write_text('remove',encoding='utf-8')
locked=run/'locked.txt';locked.write_text('preserve-original',encoding='utf-8')
missing=run/'missing.txt';directory=run/'directory';directory.mkdir()
populated=run/'populated';populated.mkdir();(populated/'child.txt').write_text('preserve-child',encoding='utf-8')
paths=[existing,missing,locked,directory,populated]
probe=run/'probe.at'
program='use auto.fs\n'+helper+'\n'
for path in paths:
    program+=f'print(Json.encode(delete_confirmed({json.dumps(path.as_posix(),ensure_ascii=False)})))\n'
probe.write_text(program,encoding='utf-8')
handle=locked.open('rb')  # Windows CRT handle does not grant FILE_SHARE_DELETE.
try:
    result=subprocess.run([str(Path(args.auto).resolve()),str(probe)],cwd=repo,capture_output=True,text=True,encoding='utf-8',timeout=45)
finally:handle.close()
(run/'probe.log').write_text(result.stdout+result.stderr,encoding='utf-8')
assert result.returncode==0,result.stderr
actual=[json.loads(line)for line in result.stdout.splitlines()if line.strip()and not line.startswith(('----','Running Auto '))]
assert actual==[True,True,False,False,False]and all(type(value)is bool for value in actual),actual
assert not existing.exists()and not missing.exists()
assert locked.read_text(encoding='utf-8')=='preserve-original'
assert directory.is_dir()and(populated/'child.txt').read_text(encoding='utf-8')=='preserve-child'
receipt={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(helper.encode()).hexdigest(),'cli_sha256':hashlib.sha256(Path(args.auto).read_bytes()).hexdigest(),'actual':actual,'cases':len(paths),'failed_files_preserved':True,'scratch':str(run)}
(run/'result.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
