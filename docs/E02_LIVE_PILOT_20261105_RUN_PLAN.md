# First limited E02 live pilot

Status: prepared for independent code and exact execution review; not a result.

Run ID: `e02-exploratory-live-20261105-01`.

The pilot tests whether a fixed model's partisan feeling-thermometer answers
change differently when the same authored civic notice is presented in a news
wrapper or a social-post wrapper. It uses four fictional profiles and two
authored DEMO notices, yielding eight matched blocks, sixteen arm units and at
most thirty-two pre/post model requests. Each post uses its own recorded pre;
contexts are isolated. Invalid baselines skip their posts, and uncertainty or
unverified billing stops the run. These are exploratory AI responses, not
measured effects on people or a representative population.

The unchanged frozen protocol is
`configs/e02_exploratory_live_pilot_v1_1.json` (SHA-256
`a76e3f8924c568e58960a99822f6e5665df4c95e38bb6e00e8d3075f71a5847b`).
Scoring, matched comparisons, exclusions and seeded crossed-bootstrap analysis
remain fixed before execution. One model family is used in this limited run;
cross-model replication and a human study anchor remain open research gates.

The request is `openai/gpt-4.1-nano` through Azure with no fallback. Only its
exact reviewed dated identity is additionally accepted. The response and
billing objects are retained in full canonical parsed form, with generation
IDs, native token usage, actual costs and provenance. Canonical parsed objects
are not original HTTP wire bytes. Reported unknown auxiliary counters remain
unknown; `streamed:true` remains a visible discrepancy with the nonstreaming
client request. The interpretation applies equally to both arms.

The existing owner authorization is one combined $5 ceiling. This study has a
$1 subceiling, at most32 model POSTs and32 billing GETs, one fresh public catalog
read, no retries and no credit purchases. Current reviewed prices give a
conservative reservation bound of $0.001397 per phase and $0.044704 for32 phases.
The two prior uncertain charges retain $0.000680 in holds and two historical
dispatches; they are never refunded or reset by this pilot. A ten-second initial
wait precedes each sole billing GET within the existing120-second phase limit.

Acceptance requires independently reviewed source and caller hashes, passing
mock primary/replay and failure checks, and an exact packet bound to the saved
original-owner history. Runtime must verify the same history and fresh prices.
Only recorded successful phases may enter analysis; all32 planned dispositions
and any failure must be reported. The former failed connectivity checkpoint is
not relabeled successful. Its separately reviewed recovery evidence admits the
pilot without rewriting the historical ledger.
