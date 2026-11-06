"""Execute the production file-confirmation function with a selected real VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--auto', required=True)
parser.add_argument('--scratch', required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
function = 'fs_write' if repo.name == 'auto-notes' else 'write_confirmed'
source = repo / 'src/back/repository.at'
text = source.read_text(encoding='utf-8')
start = text.index('fn ' + function + '(')
brace = text.index('{', start)
depth = 1
end = brace + 1
while depth:
    depth += (text[end] == '{') - (text[end] == '}')
    end += 1
body = text[start:end]
scratch = Path(args.scratch).resolve()
scratch.mkdir(parents=True, exist_ok=True)
run = Path(tempfile.mkdtemp(prefix='confirmed-file-', dir=scratch)).resolve()
assert run.is_relative_to(scratch)
create, overwrite, empty = [run / name for name in ('create.txt', 'overwrite.txt', 'empty.txt')]
missing = run / 'missing-parent' / 'output.txt'
directory = run / 'directory'
directory.mkdir()
readonly, already = run / 'readonly.txt', run / 'already.txt'
overwrite.write_text('old', encoding='utf-8')
empty.write_text('old', encoding='utf-8')
readonly.write_text('preserve-original', encoding='utf-8')
already.write_text('same-content', encoding='utf-8')
invalid_readonly, invalid_writable, empty_readonly = [run / name for name in
    ('invalid-readonly.bin', 'invalid-writable.bin', 'empty-readonly.txt')]
invalid_bytes = bytes.fromhex('fffe80')
invalid_readonly.write_bytes(invalid_bytes)
invalid_writable.write_bytes(invalid_bytes)
empty_readonly.write_bytes(b'')
payload = '第一段中文 54.25。\n第二段 8.125。'
cases = [(create, payload, True), (overwrite, payload, True), (empty, '', True),
         (missing, payload, False), (directory, '', False),
         (readonly, 'different-content', False), (already, 'same-content', True),
         (invalid_readonly, '', False), (invalid_writable, '', True),
         (empty_readonly, '', True)]
probe = run / 'probe.at'
program = 'use auto.fs\n' + body + '\n'
for path, content, _ in cases:
    program += f'print(Json.encode({function}({json.dumps(path.as_posix(), ensure_ascii=False)}, {json.dumps(content, ensure_ascii=False)})))\n'
probe.write_text(program, encoding='utf-8')
try:
    os.chmod(readonly, stat.S_IREAD)
    os.chmod(already, stat.S_IREAD)
    os.chmod(invalid_readonly, stat.S_IREAD)
    os.chmod(empty_readonly, stat.S_IREAD)
    result = subprocess.run([str(Path(args.auto).resolve()), str(probe)], cwd=repo,
                            capture_output=True, text=True, encoding='utf-8', timeout=45)
finally:
    for path in (readonly, already, invalid_readonly, empty_readonly):
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
(run / 'probe.log').write_text(result.stdout + result.stderr, encoding='utf-8')
assert result.returncode == 0, result.stderr
lines = [line for line in result.stdout.splitlines() if line.strip()
         and not line.startswith(('----', 'Running Auto '))]
actual = [json.loads(line) for line in lines]
expected = [expected for _, _, expected in cases]
assert actual == expected and all(type(value) is bool for value in actual), (actual, expected)
assert create.read_text(encoding='utf-8') == overwrite.read_text(encoding='utf-8') == payload
assert empty.is_file() and empty.read_bytes() == b''
assert not missing.exists() and directory.is_dir()
assert readonly.read_text(encoding='utf-8') == 'preserve-original'
assert already.read_text(encoding='utf-8') == 'same-content'
assert invalid_readonly.read_bytes() == invalid_bytes
assert invalid_writable.read_bytes() == empty_readonly.read_bytes() == b''
receipt = {'production_source': str(source), 'function': function,
           'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'helper_sha256': hashlib.sha256(body.encode()).hexdigest(),
           'cli_sha256': hashlib.sha256(Path(args.auto).read_bytes()).hexdigest(),
           'cases': len(cases), 'expected': expected, 'actual': actual,
           'readonly_original_preserved': True, 'scratch': str(run)}
(run / 'result.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
