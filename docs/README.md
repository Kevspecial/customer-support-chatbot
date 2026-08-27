# Screenshots

Evidence images for the project submission, grouped by the rubric area each
supports. Items marked ⚠️ need re-capturing before submission — the reason is
given in each case.

| # | Image | Supports | Status |
|---|-------|----------|--------|
| 1 | [aws console.png](aws%20console.png) | Resources & tool setup | OK |
| 2 | [harness.png](harness.png) | Resources & tool setup | Duplicate of 1 |
| 3 | [aws1.png](aws1.png) | Testing infrastructure | OK |
| 4 | [EvalDatasetBucketName and BedrockEvalRoleArn.png](EvalDatasetBucketName%20and%20BedrockEvalRoleArn.png) | Testing infrastructure | OK |
| 5 | [chat show tool call and ticketid.png](chat%20show%20tool%20call%20and%20ticketid.png) | Bug report path | ⚠️ Shows the failure |
| 6 | [dynamoDB bug report -1.png](dynamoDB%20bug%20report%20-1.png) | Bug report path | ⚠️ No items visible |
| 7 | [faq and bug prompt.png](faq%20and%20bug%20prompt.png) | Flow diagram + conditions | Strong |
| 8 | [other prompt.png](other%20prompt.png) | Flow routing | ⚠️ Documents a bug |
| 9 | [Bug prompts.png](Bug%20prompts.png) | Flow testing | ⚠️ Malformed run |
| 10 | [Faq prompts.png](Faq%20prompts.png) | Flow testing | ⚠️ Malformed run |
| 11 | [Covered and uncoverd prompts.png](Covered%20and%20uncoverd%20prompts.png) | Flow testing | ⚠️ Malformed run |
| 12 | [evaluation job in terminal.png](evaluation%20job%20in%20terminal.png) | Evaluation job created | OK |
| 13 | [evaluation job.png](evaluation%20job.png) | Evaluation jobs completed | OK |
| 14 | [evaluation.png](evaluation.png) | Flow evaluation results | ⚠️ Pre-fix, stale |
| 15 | [evaluation result - 2.png](evaluation%20result%20-%202.png) | Harness evaluation results | OK |
| 16 | [eval-prompt details.png](eval-prompt%20details.png) | Per-prompt scores | Partial (page 1 of 4) |

---

## Resources and tool setup

### 1. aws console.png · 2. harness.png

One terminal session covering Steps 1 and 2 end to end:

- `aws cloudformation deploy` creating `bug-report-tool-stack`
- `setup_gateway.py` creating gateway
  `bug-report-tool-stack-gateway-v1wzguqnty` (status `READY`) and registering
  Lambda target `bugreports` with the tool `create_bug_report`
- `create_harness.py` loading the system prompt (14,087 characters once the
  FAQ replaces `{{FAQ}}`) and reporting harness
  `support_chatbot-Nq0RyI4o4a` as `READY`

The two images are the same run; `harness.png` is the wider VS Code capture.
Keep one.

### 3. aws1.png

`aws cloudformation deploy` creating `bug-report-testing-stack`.

### 4. EvalDatasetBucketName and BedrockEvalRoleArn.png

The testing stack's outputs: bucket
`udacity-agentic-engineer-c1-eval-631659229800` and role
`arn:aws:iam::631659229800:role/bedrock-eval-role`. Together with image 3
this evidences the evaluation infrastructure.

---

## Bug report path

### 5. chat show tool call and ticketid.png ⚠️

A `chat.py` session captured with `script`, showing the
`[tool call] bugreports___create_bug_report` line and returned ticket IDs.

> **Re-capture required.** The rubric asks for collection of the description,
> steps to reproduce, and environment *before* the tool call. Here the tool
> fires on turn 1 in response to "Hi, something on your site isn't working" —
> a message containing none of the three — and the questions follow
> afterwards. A second fabricated ticket is then re-quoted across three
> turns, alongside an unprompted refund explanation the customer never asked
> for.
>
> `aws console.png` confirms the 14,087-character prompt (the version with
> the `THE GATE` section) is deployed, so re-running should now produce the
> question-first behavior. Open with a vague report and answer one question
> per turn.

### 6. dynamoDB bug report -1.png ⚠️

The DynamoDB **Tables list**, showing `bug-report-tool-stack-bug-reports` as
`Active` with partition key `ticketId (S)`.

> **Re-capture required.** The rubric asks for the table *showing at least one
> item created by the chatbot*. This is the table list, not the contents, and
> it reports **0 bytes** total size. Open the table and use **Explore table
> items**, then screenshot the rows. Cross-check that a `ticketId` there
> matches one in your chat transcript.
>
> (DynamoDB's size metric updates only every few hours, so 0 bytes is not
> proof the table is empty — but the screenshot still shows no items.)

---

## Flow: classification and routing

### 7. faq and bug prompt.png

The strongest image in the set. The flow `customers-requestss` in the
builder, covering two rubric requirements at once:

- **Full flow diagram** — `Flow Input` fanning out to `classifier`,
  `Prompt_2`, `Prompt_3`, and `Prompt_4`; the condition node routing to three
  responders; each responder terminating at its own output node
  (`FlowOutputNode_1`, `_2`, `_3`).
- **Condition node expressions** — the `category` node showing
  `category == "bug"` → `Prompt_2`, `category == "faq"` → `Prompt_3`, and the
  "if all conditions are false" default → `Prompt_4`.

The test panel shows two correct runs: a complete bug report answered without
inventing a ticket ID, and a refund-timing complaint answered with the FAQ's
3–10 business day figure.

**Still missing:** a capture of the `classifier` node's own configuration
panel showing its prompt text and temperature 0. The rubric asks for the
classifier prompt configuration specifically.

### 8. other prompt.png ⚠️

The same flow with the test panel showing *"If I order from Germany, will I
have to pay import duty?"* routed to `FlowOutputNode_2`.

> **Documents a bug.** The reply invents a customs policy — duties levied by
> German customs, charges payable on delivery, "we have no control over these
> charges" — none of which is in `online_shop_faq.md`. `Prompt_3` contained
> the raw FAQ with no grounding rules, so the model answered from general
> knowledge.
>
> The grounded replacement in
> [../flow-prompts/faq-responder.txt](../flow-prompts/faq-responder.txt) is
> now deployed. Re-running this message should return the 1-800-555-0199
> hand-off, which makes a good demonstration of the uncovered-question path.

### 9–11. Bug prompts.png · Faq prompts.png · Covered and uncoverd prompts.png ⚠️

All three are the same flow execution, `20260825-040406`, scrolled to
different parts of the output.

> **Not valid test evidence.** The entire `flow-tests.json` file was pasted
> into the test panel as a single message. The trace confirms it —
> `FlowInputNode` → `classifier` → `category` → `Prompt_4` →
> `FlowOutputNode_3` — so all 12 cases were treated as one customer message,
> classified `other`, and answered by the hand-off branch alone. The `bug` and
> `faq` branches never ran.
>
> These show the *contents of the test file*, not per-case flow behavior. Run
> cases individually instead, or use `generate-eval-dataset-flow.py`, which
> sends each prompt in its own invocation.

---

## Testing and evaluation

### 12. evaluation job in terminal.png

The `jobArn` returned when the evaluation job was created:
`arn:aws:bedrock:us-east-1:631659229800:evaluation-job/83bc0wacepx2`.

### 13. evaluation job.png

The Evaluations list with both jobs `Completed`:

| Job | Created | Inference source |
|-----|---------|------------------|
| `support-chatbot-eval-run-1` | 26 Aug 2026 16:04 GMT | `my-support-chatbot` (harness) |
| `evaluation-job-quick-start-20260825141038` | 25 Aug 2026 14:20 GMT | `support-flow` (flow) |

### 14. evaluation.png ⚠️

Flow evaluation results — Helpfulness 0.76, **Correctness 0.83**,
Faithfulness 0.98, Completeness 0.83, Harmfulness 0.00.

> **Stale.** This job ran on 25 August, before `Prompt_3` was replaced with
> the grounded version. It scores the hallucinating FAQ branch. Re-run and
> re-capture for a result that reflects the current flow.
>
> Worth keeping regardless: the Faithfulness 0.98 against Correctness 0.83 is
> the most interesting finding in the whole evaluation, and it is discussed
> in [evaluation-observations.md](evaluation-observations.md).

### 15. evaluation result - 2.png

Harness evaluation results — **Correctness 0.84** (avg 0.842) across 19
prompts, with the distribution histogram. The histogram is what shows the
score is bimodal rather than uniform: a small bar at 0 and a large one near
1.

### 16. eval-prompt details.png

The per-prompt scoring table, page 1 of 4. All five visible FAQ cases —
return policy, refund timing, damaged item, discount code, password reset —
scored **1**.

Pages 2–4 were not captured. Since 0.842 is exactly 16/19, three prompts
scored 0, and those pages are where they are. Capturing them would let the
observations name all three failures precisely rather than two.

---

## Housekeeping

Several filenames contain spaces, which need URL-encoding in Markdown links.
Renaming to hyphenated lowercase (`aws-console.png`, `flow-diagram.png`,
`eval-results-harness.png`) would be tidier, though nothing depends on it.
`Covered and uncoverd prompts.png` also has a typo in "uncovered".
