# Worked example - Seed mode

This example is illustrative only. It shows the Phase 4 output and approval gate; it does not call gh issue create.

**Input:**

~~~text
SPEC: docs/report-export-spec.md
REPO: acme/reporting
LABELS: agent-work-ticket
Universe: zero open tickets with that label
~~~

**Spec excerpt:**

- §1 Export endpoint - add POST /reports/exports, validate the request, and return an export job identifier.
- §2 Export audit event - record an ExportRequested audit event after an export request is accepted. Consume the accepted-request hook exposed by [draft #A].

**Universe snapshot:** agent-work-ticket, acme/reporting, Seed mode, zero existing tickets.

**Coverage map:** docs/report-export-spec.md §1 -> [draft #A]; docs/report-export-spec.md §2 -> [draft #B]. [draft #B] depends on the accepted-request hook from [draft #A].

## [draft #A] Reports API - create export jobs

~~~markdown
## Agent Work Ticket

### Request / Outcome

* Add POST /reports/exports for validated report-export requests.
* Return an export job identifier after an accepted request.
* Expose an accepted-request hook stub for the audit consumer owned by [draft #B].

### Background / Context

* This is the first ticket in the dependency order for the Seed-mode example.
* [draft #B] consumes the accepted-request hook; this ticket owns only the hook boundary and endpoint behavior.

### Source Materials

* docs/report-export-spec.md §1

### Scope of Work

The owner may:

* Implement request validation and job-identifier creation for POST /reports/exports.
* Define the accepted-request hook stub consumed by [draft #B].
* Add endpoint tests for accepted and rejected requests.

The owner must not:

* Implement ExportRequested audit-event persistence or consumption ([draft #B]).
* Change unrelated report endpoints.
* Change the audit-event contract after [draft #B] begins consuming the hook.
* Invent semantics not in docs/report-export-spec.md §1.
* Take any action requiring human approval without asking first.

### Definition of Done

This ticket is complete when:

* Valid requests return a job identifier and invalid requests are rejected by tests.
* The accepted-request hook stub is named and callable by a test double.
* Endpoint tests pass without requiring the audit-event implementation.

### Stop Conditions

Stop and ask for input if:

* The spec does not define request validation or job-identifier behavior.
* The accepted-request hook cannot be exposed without changing a shared contract.
* The work would affect another repository or team.

### Blocking Questions

If blocked, ask only the exact question needed to continue.

* None known for this example.
~~~

## [draft #B] Audit Trail - record export requests

~~~markdown
## Agent Work Ticket

### Request / Outcome

* Consume the accepted-request hook from [draft #A].
* Record an ExportRequested audit event after an export request is accepted.
* Add tests proving the event is recorded once per accepted request.

### Background / Context

* Depends on [draft #A], consumed through its accepted-request hook stub.
* This ticket owns audit-event consumption and persistence, not endpoint behavior.

### Source Materials

* docs/report-export-spec.md §2
* [draft #A] Reports API - create export jobs

### Scope of Work

The owner may:

* Implement the ExportRequested audit-event consumer and persistence behavior.
* Add tests using the accepted-request hook stub from [draft #A].

The owner must not:

* Implement POST /reports/exports or request validation ([draft #A]).
* Change the accepted-request hook contract owned by [draft #A].
* Change unrelated audit-event types.
* Invent semantics not in docs/report-export-spec.md §2.
* Take any action requiring human approval without asking first.

### Definition of Done

This ticket is complete when:

* An accepted-request hook call records exactly one ExportRequested event.
* Tests pass with a stubbed hook producer; the endpoint implementation is not required.
* Rejected requests do not produce the event in the consumer tests.

### Stop Conditions

Stop and ask for input if:

* The spec does not define when an export request is accepted.
* The hook stub from [draft #A] is missing or incompatible.
* The work would change the endpoint contract or affect another repository.

### Blocking Questions

If blocked, ask only the exact question needed to continue.

* None known for this example.
~~~

**Batch approval:** Approve all, Approve subset (name the drafts), or Revise.
