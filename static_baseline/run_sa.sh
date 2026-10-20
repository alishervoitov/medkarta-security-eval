#!/bin/bash
S=/tmp/claude-0/-home-claude/e769ad94-37b0-5fe5-970c-4fda8e3cbadc/scratchpad
W=$S/fi2/work
for d in $(ls $W); do
  [ -d "$W/$d" ] || continue
  $S/sa/bin/bandit -r "$W/$d" -f json -q --exclude "*/tests/*,*/test_*,*/migrations/*,*/node_modules/*,*/docs/*" -o $S/sa_out/bandit_$d.json 2>/dev/null
  $S/sa/bin/semgrep scan --metrics=off --quiet --json --disable-version-check \
    --config $S/sgrules/python/django/security --config $S/sgrules/python/django/best-practice \
    --config $S/sgrules/python/lang/security --config $S/sgrules/python/jwt \
    --exclude tests --exclude migrations --exclude node_modules --exclude docs --exclude '*.sqlite3' \
    -o $S/sa_out/semgrep_$d.json "$W/$d" >/dev/null 2>$S/sa_out/semgrep_$d.err
  echo "done $d"
done
echo ALLDONE
