# ORDER: <project>-<slug>

Status: Approved
Approval: <key>
Upstream: the owner's order, issued with scripts/delegate.sh by <issuer> on <issued>
Task: <task>
Grants: <grants>
Expires: <expires>

<!-- scripts/delegate.sh writes this file into doc/orders/ and stages it; the
     owner commits it with an Owner-Approved trailer naming the order's key.
     Do not edit an issued order: the commit check refuses a changed order
     document, and the task line is hashed into the owner's registry entry.
     To change the task, revoke this order and issue a new one. -->

## Approval history

- **<issued> — issued (human).** Registry key `<key>`, written by scripts/delegate.sh and carried on the canonical `Approval:` line above.
