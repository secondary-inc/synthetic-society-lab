# JSON compatibility probe: price-interpretation proposal

Non-authorizing draft for independent review. No model selection, complete price
release, human approval, owner bootstrap, credential access or inference follows.
All approved experimental spending remains zero. An inner contract's type name
is not evidence of review: the accompanying machine-readable packet explicitly
labels its interpretation and arithmetic as PROPOSAL_ONLY.

## Concrete request and observed source

Propose the already implemented one-request nonpolitical JSON compatibility
probe, output ceiling32, seed20261103, model `openai/gpt-4.1-nano`, provider family
`azure`, reported provider `Azure`. No alternate model, tools/plugins, files,
images/audio, BYOK, region guarantee, fallback, repair or inference retry. This
is not selection of a model for E01/E02 scientific work or a study of people.
Required v4.1 code/remedy acceptance and actual external releases remain absent.

The new public native metadata snapshot observed November3 at18:10:08UTC has
2359bytes, SHA256 `59c4fcc5ec213b8aae3019949267bd0f27f6bdfc95bee436c06a85ffc8ef9ee9`.
One fixed unauthenticated GET used the accepted collector; no owner/key/model
was accessed. It advertises Azure and azure/swedencentral. Per-million input,
output and cache-read prices are respectively0.10/0.40/0.03 and0.11/0.44/0.033.
The two entries agree on required parameter support, empty native-tools map and
null service tier. The architecture reports text output. The selected policy
explicitly bounds both family members, including a member the public model page
currently marks outside Standard routing. It promises no physical serving region.

## Explicit interpretations requiring independent acceptance

The catalog omits request, two cache-write and internal-reasoning rates. Their
proposed zeros are deliberate interpretations of the sources below, never
automatic defaults inferred solely from absence:

- Request fee: the [pricing FAQ](https://openrouter.ai/pricing) describes token
  billing and separates credit-purchase fees from individual inference requests.
  The [support FAQ](https://openrouter.ai/support/) similarly describes
  provider-price passthrough. Together with the explicit token table on the
  [model page](https://openrouter.ai/openai/gpt-4.1-nano), these support a proposed
  zero flat request fee for this text-only Standard shared-provider request.
  This is an interpretation, not an independently verified Azure contract.
- Cache writes: the [OpenRouter caching guide](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
  distinguishes models before GPT-5.6 from newer charged writes. Proposed zero
  write rates apply only to this older model with no explicit caching controls.
  Cache reads use the exact Azure catalog rates, even though another provider's
  published ratio may differ. Azure-specific applicability needs review.
- Reasoning: the proposed request uses no reasoning controls, and the catalog
  advertises no reasoning parameter. Zero separately charged reasoning is an
  explicit applicability assumption for this model, not proved by an absent
  field. Independent review must accept its basis or leave this interpretation
  BLOCKED. Actual nonzero/unknown native reasoning cannot become success.
- The advertised web-search price is inapplicable only because the exact request
  disables tools/plugins and has no online/search variant. The v4.1 checks must
  reject observed auxiliary activity; absence of a returned counter is retained
  as NOT_REPORTED, not an invented zero. Media inputs/outputs and conditional
  tier/override pricing remain outside the contract.

These web observations are dated advisory readings, not a frozen native document
corpus. The earlier native403 documentation failure remains unchanged; it was
not retried or bypassed. Review can reject any unsupported interpretation.

## Conditional arithmetic and authorization boundary

Use the existing conservative bound: sum prompt/cache-read/two cache-write
components for every possible input token, take the largest member; similarly
bound completion plus reasoning and flat request components. With the proposed
zeros, input is0.143USD per million tokens and output0.44USD per million tokens.
This deliberately overcounts mutually exclusive cache categories. Actual
native usage and total billing still require reconciliation; the quote is
conditional on the reviewed request/framing/provider contract, not a guarantee
against an external service violating it.

The machine-readable packet records the exact compiled prompt, parameters,
input-envelope ceiling, upward-rounded reservation and proposal hashes. A possible
owner ceiling of0.001USD of model-balance usage and one absolute lifetime dispatch
is only a proposed ceiling. It is not approved spending or an activation switch.
Credit purchases, account fees, taxes and development/local costs are separate,
unpriced and not automatically bought or altered. No account balance or auto-topup
setting has been inspected. Any eventual execution requires an owner-provided
pre-funded setup and concrete approval, with a rotated dedicated key injected
securely rather than pasted into chat. No question for paid authority is issued
by this proposal.

The proposed interpretation interval is finite. Before a new dispatch the fixed
collector must refresh metadata within15minutes and match the reviewed semantic
contract, membership, parameters and prices. Changed meaning or an expired
release refuses; the agent cannot silently choose a replacement or retry.
Provider/model revision, real parameter support, actual serving/billing identity,
availability and compatibility remain unobserved. The first real POST is NOT_RUN.
