"""Fill in group.semester_program_id in config.json when it is 0.

RTU gives every (semester, programme, course, group) its own semesterProgramId.
Looking it up needs the RTU site, so this runs inside the GitHub Action before
the build. Once the id is written, this script does nothing.
"""
import json
import re
import sys

sys.path.insert(0, ".")
from rtusync.api import RtuApi  # noqa: E402

PATH = "config.json"

text = open(PATH, encoding="utf-8").read()
stripped = "\n".join(re.sub(r"\s(//|#).*$", "", line) for line in text.splitlines())
cfg = json.loads(re.sub(r"^\s*(//|#).*$", "", stripped, flags=re.M))

group = cfg["group"]
if int(group.get("semester_program_id") or 0):
    print("semester_program_id already set: %s" % group["semester_program_id"])
    sys.exit(0)

api = RtuApi()
semester_id = int(cfg["semester"]["id"])
code = group["program_code"].strip().upper()
course = int(group["course"])
wanted = str(group["group"]).strip()

program = None
for dept in api.programs(semester_id):
    for p in dept.get("program") or []:
        if str(p.get("code", "")).strip().upper() == code:
            program = p
if program is None:
    sys.exit("programme %s not found in semester %d" % (code, semester_id))

groups = api.groups(semester_id, program["programId"], course)
match = [g for g in groups if str(g.get("group")).strip() == wanted]
if not match:
    sys.exit("group %s not found; available: %s" % (wanted, [g.get("group") for g in groups]))

spid = int(match[0]["semesterProgramId"])
new = re.sub(r'("semester_program_id"\s*:\s*)\d+', r"\g<1>%d" % spid, text, count=1)
open(PATH, "w", encoding="utf-8").write(new)
# The fork came with the original author's timetable history; start clean.
import os
for leftover in ("state.json", "changes.md"):
    if os.path.exists(leftover):
        os.remove(leftover)
print("resolved %s course %d group %s -> semesterProgramId %d" % (code, course, wanted, spid))
