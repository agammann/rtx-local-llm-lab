"""Package the exact committed source with a checksum and commit identity."""
import hashlib, os, re, subprocess, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
if Path.cwd().resolve() != ROOT:
    raise ValueError('Run packaging from the repository root.')
if git('status', '--porcelain', '--untracked-files=normal').strip():
    raise ValueError('Packaging requires a clean committed source tree.')
version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
    raise ValueError('Expected a stable release version.')
if re.search(r'^VERSION = "' + re.escape(version) + '"$', (ROOT / 'bench.py').read_text(encoding='utf-8'), re.M) is None:
    raise ValueError('CLI and source versions differ.')
if 'MIT License' not in (ROOT / 'LICENSE').read_text(encoding='utf-8'):
    raise ValueError('Expected the source MIT license.')
commit = git('rev-parse', 'HEAD').decode().strip()
if os.environ.get('GITHUB_SHA', commit) != commit:
    raise ValueError('Checkout differs from the exact workflow commit.')
tracked = git('ls-files', '-z').decode().split('\0')[:-1]
for name in tracked:
    file = ROOT / name
    if file.is_symlink() or not file.is_file():
        raise ValueError('Linked or missing source file.')
    if any(part in {'.git', '.venv', 'node_modules', 'outputs', 'release-artifacts', 'verification-artifacts'} or part.startswith('.env') for part in Path(name).parts) or file.suffix.lower() in {'.gguf', '.safetensors', '.pyc'}:
        raise ValueError('Private, model or generated data is tracked.')
    data = file.read_bytes()
    if re.search(rb'sk-(?:proj-)?[A-Za-z0-9_-]{20,}', data) or (b'-----BEGIN' + b' PRIVATE KEY-----') in data:
        raise ValueError('A secret pattern is tracked.')
out = ROOT / 'release-artifacts'
out.mkdir(exist_ok=True)
name = 'rtx-local-llm-lab_' + version + '_source.zip'
subprocess.run(['git', 'archive', '--format=zip', '--prefix=rtx-local-llm-lab_' + version + '/', '--output=' + str(out / name), 'HEAD'], cwd=ROOT, check=True)
with zipfile.ZipFile(out / name) as archive:
    if archive.testzip() is not None or archive.comment.decode() != commit:
        raise ValueError('Archive integrity or commit differs.')
line = hashlib.sha256((out / name).read_bytes()).hexdigest() + '  ' + name + '\n'
(out / (name + '.sha256')).write_bytes(line.encode())
(out / 'SHA256SUMS').write_bytes(line.encode())
print('Packaged ' + name + ' from ' + commit + '; ' + str(len(tracked)) + ' exact tracked files.')
