# Verified LLM Email Classification — Interview/Engineering Notes

## Goal
Automate clear recruiting updates without trusting the LLM's self-reported confidence.
Use human review only when evidence, status interpretation, application identity, or
status chronology is insufficient.

## Decision pipeline
1. Read and unwrap email (original sender, subject, content).
2. Run cheap deterministic extraction first.
3. For low-confidence rule results, ask Groq-hosted Llama to return a **structured proposal**
   with source quotations for company, job title, status, and action.
4. Verify JSON types and quotations; reject invented or unsupported fields.
5. Run an **independent** status-evidence check on the quoted text. Reject broad words
   such as "offer", "calendar", or "unfortunately" as sufficient evidence by themselves.
6. Check entire email for contradictions (receipt plus assessment is a normal
   combination; rejection plus assessment is not).
7. Compute a **verification policy score** (NOT a probability):
   - Grounded company, job title and status quotes: 50 points (all required)
   - Independently recognized status evidence: 30
   - No contradictory status indicators: 15
   - Agreement with deterministic parser: 5
   Eligible for auto processing at 95 points with all required gates satisfied.
   Rejection and offer require deterministic status agreement.
8. Match the existing application by company and role. For an LLM-driven update,
   allow auto processing only on **exact** identity. High fuzzy similarity alone is
   not sufficient to update a possibly different application.
   For a *new* application, allow automatic creation only on a verified
   application-received email, not on an unmatched assessment or rejection.
9. Before writing, reject older messages or backward stage transitions to review.
   On success, save an event, update the application, and retain the email.
   Message-ID/fingerprint checks protect against duplicate ingestion.
10. Human review handles unclear evidence, multiple possible applications,
    questionable status transitions, and unsuccessful extraction.

## Important distinction
The number 95/100 is a count of checks that passed. It does NOT mean
"95% correct" or "95% model confidence." Calibrated confidence requires
a human-labeled representative dataset and held-out testing.
Do not present it as a probability in the UI or interview.

## Evaluation and release
Use `cd backend && python scripts/evaluate_llm_policy.py /private/path/labeled.jsonl`
on an anonymized, human-labeled set of real email examples. Include
different ATS templates, recruiting language variants, forwarded messages,
negations, ambiguous emails, the same company/multiple roles, assessments,
interviews, and rejections. The evaluator reports:
- auto coverage = automatic decisions / all emails
- auto precision = correct automatic decisions / automatic decisions
- review rate and failed-auto examples by status

The provided tests use **synthetic fixtures**. They validate flow and edge cases
but do not prove production accuracy. Do not commit personal recruiter emails
or authentication tokens to GitHub.
Define an error target and tune the gates on a calibration set; test the
selected policy on a *separate held-out* set, monitor a sample of automatic
decisions after launch, and re-evaluate when prompt/model or rules change.

## Key tradeoff
Strict source evidence plus exact identity prevents many wrong updates while
automating clear messages; it deliberately routes previously unseen wording
and uncertain identity for review until evaluated. A future trained/classically
calibrated classifier or embedding-based retrieval can expand coverage, provided
its measured accuracy and latency justify the extra complexity.

## Interview answer
"I used rules for predictable recruiting emails and an LLM to interpret
unfamiliar language. I don't take the model's reported confidence literally.
I require verbatim evidence, independently check the status cue, confirm the
correct application, and verify that the update doesn't regress the timeline.
Only sufficiently verified cases are applied automatically; ambiguity goes to
a review queue. I also built an offline evaluation workflow for measuring
auto-update precision and review rate on labeled messages."
