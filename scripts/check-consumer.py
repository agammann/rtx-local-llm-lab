"""Verify a complete release asset set and test a fresh exact source consumer."""
import argparse, hashlib, re, stat, subprocess, sys, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
p.add_argument('--directory')
p.add_argument('--commit')
args = p.parse_args()
version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
commit = args.commit or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
if not re.fullmatch(r'[a-f0-9]{40}', commit):
    raise ValueError('Expected exact source commit.')
directory = Path(args.directory).resolve() if args.directory else ROOT / 'release-artifacts'
name = 'rtx-local-llm-lab_' + version + '_source.zip'
expected = {name, name + '.sha256', 'SHA256SUMS'}
if {file.name for file in directory.iterdir()} != expected:
    raise ValueError('Release asset set differs.')
line = hashlib.sha256((directory / name).read_bytes()).hexdigest() + '  ' + name + '\n'
if any((directory / checksum).read_bytes() != line.encode() for checksum in [name + '.sha256', 'SHA256SUMS']):
    raise ValueError('Checksums differ.')
out = Path(args.out).resolve()
if out.exists() or out.is_relative_to(ROOT):
    raise ValueError('Use a new consumer folder outside the checkout.')
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1]
files = {}
prefix = 'rtx-local-llm-lab_' + version + '/'
with zipfile.ZipFile(directory / name) as archive:
    if archive.comment.decode() != commit or archive.testzip() is not None:
        raise ValueError('Archive commit or integrity differs.')
    if len(archive.namelist()) != len(set(archive.namelist())):
        raise ValueError('Duplicate archive entry.')
    for item in archive.infolist():
        if not item.filename.startswith(prefix):
            raise ValueError('Archive prefix differs.')
        path = item.filename[len(prefix):]
        if PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or '\\' in path or ':' in path:
            raise ValueError('Unsafe archive path.')
        if stat.S_IFMT(item.external_attr >> 16) not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise ValueError('Linked or special archive entry.')
        if not item.is_dir():
            files[path] = archive.read(item)
if set(files) != set(tracked):
    raise ValueError('Archive source set differs.')
for path, data in files.items():
    if data != (ROOT / path).read_bytes():
        raise ValueError('Source bytes differ: ' + path)
out.mkdir(parents=True)
for path, data in files.items():
    target = out / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
result = subprocess.check_output([sys.executable, 'bench.py', '--version'], cwd=out, text=True).strip()
if result != 'RTX Local LLM Lab ' + version:
    raise ValueError('Consumer version differs.')
subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=out, check=True)
print('Verified ' + str(len(files)) + ' exact source files and fresh CLI consumer at ' + str(out))
