"""Import closure of modules inside ppt-master's scripts dir (static, via ast)."""
import ast, sys, os
from pathlib import Path
root = Path(sys.argv[1])
mods = {}
for p in root.rglob("*.py"):
    if "tests" in p.parts: continue
    rel = p.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__": parts = parts[:-1]
    mods[".".join(parts)] = p
def resolve(cur, node):
    out = []
    pkg = cur.split(".")
    is_pkg = mods[cur].name == "__init__.py"
    if isinstance(node, ast.ImportFrom):
        if node.level:
            base = pkg if is_pkg else pkg[:-1]
            base = base[: len(base) - (node.level - 1)] if node.level > 1 else base
            name = ".".join(base + ([node.module] if node.module else []))
        else:
            name = node.module or ""
        cands = [name] + [f"{name}.{a.name}" for a in node.names]
    else:
        cands = [a.name for a in node.names]
    for c in cands:
        while c:
            if c in mods: out.append(c); break
            c = c.rpartition(".")[0]
    return out
deps = {}
for m, p in mods.items():
    try: tree = ast.parse(p.read_text(encoding="utf-8"))
    except Exception: deps[m] = set(); continue
    s = set()
    for n in (tree.body if os.environ.get("TOP") else ast.walk(tree)):
        if isinstance(n, (ast.Import, ast.ImportFrom)): s.update(resolve(m, n))
    # sys.path hacks: bare imports of top-level script modules
    s.discard(m); deps[m] = s
def closure(m):
    seen, stack = set(), [m]
    while stack:
        x = stack.pop()
        if x in seen: continue
        seen.add(x); stack.extend(deps.get(x, ()))
    return seen
def lines(ms): return sum(len(mods[x].read_text(encoding="utf-8").splitlines()) for x in ms)
for target in sys.argv[2:]:
    c = closure(target)
    tops = sorted({x.split(".")[0] for x in c})
    print(f"{target}: {len(c)} modules, {lines(c)} lines; top-level: {tops}")
