import json, glob, os, sys

sys.stdout.reconfigure(encoding="utf-8")

keys = [
    "about.button","about.button_title","about.credits_note","about.credits_title",
    "about.summary","about.version",
    "pane.controls","pane.fix_indent","pane.indent","pane.line_numbers",
    "indent.fault_at","indent.fix","indent.fix_all_prompt","indent.fixed_all",
    "indent.fixed_one","indent.move_next","indent.no_faults",
]
out = []
for f in sorted(glob.glob("src/jojo_code/i18n/*.json")):
    code = os.path.splitext(os.path.basename(f))[0]
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    out.append("== " + code)
    for k in keys:
        out.append("   " + k + " = " + str(d.get(k)))
sys.stdout.write("\n".join(out))
