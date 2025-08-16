import argparse, json, re
from pathlib import Path

def split_into_snippets(text, max_len=300):
    parts = re.split(r'(?:\n\n|\n|- )', text)
    snippets, cur = [], ""
    for p in map(str.strip, parts):
        if not p: 
            continue
        if len(cur) + len(p) + 1 <= max_len:
            cur = f"{cur} {p}".strip()
        else:
            if cur: snippets.append(cur)
            cur = p
    if cur: snippets.append(cur)
    return [s for s in snippets if len(s) > 20]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    entries = []
    for fp in Path(args.corpus).glob("*.txt"):
        text = Path(fp).read_text(encoding="utf-8", errors="ignore")
        for i, snip in enumerate(split_into_snippets(text)):
            entries.append({"doc_id": f"{fp.stem}:{i}", "text": snip})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(entries), encoding="utf-8")
    print(f"Wrote {len(entries)} snippets to {args.out}")

if __name__ == "__main__":
    main()
