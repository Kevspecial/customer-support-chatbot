# Customer Support Chatbot — Amazon Bedrock AgentCore

A customer support chatbot for a fictional online shop, built on the
**Amazon Bedrock AgentCore managed harness**. It handles three kinds of
customer message:

| Route | Behavior |
|-------|----------|
| **Bug report** | Collects a description, steps to reproduce, and the customer's environment, then files a ticket via the `create_bug_report` tool and returns the ticket ID. |
| **Platform question** | Answers from `online_shop_faq.md`, embedded in the system prompt. |
| **Anything else** | Refers the customer to the human support line, 1-800-555-0199. |

All routing lives in a single system prompt — there are no classifier nodes
or condition branches. The harness supplies the agent loop, session state,
and tool execution; [system_prompt.txt](system_prompt.txt) supplies the
behavior.

## Architecture

```
  chat.py / generate-eval-dataset.py
              │  invoke_harness (runtimeSessionId = one conversation)
              ▼
   AgentCore managed harness  ──── system_prompt.txt + online_shop_faq.md
     (us.amazon.nova-pro-v1:0, temperature 0, topK 1)
              │  tools: [agentcore_gateway]
              ▼
   AgentCore Gateway  (MCP, AWS_IAM auth)
              │  target "bugreports"
              ▼
   Lambda  create_bug_report(description, stepsToReproduce, environment)
              │
              ▼
   DynamoDB  bug-report-tool-stack-bug-reports
```

The model sees the tool as `bugreports___create_bug_report` (three
underscores). The gateway passes tool arguments **directly as the Lambda
event** — no `messageVersion` envelope, unlike Bedrock Agents Classic.

## Repository layout

| File | Role |
|------|------|
| `system_prompt.txt` | **Main deliverable.** Routing, bug-collection procedure, FAQ grounding rules. `{{FAQ}}` is substituted at harness-creation time. |
| `harness-tests.json` | 19-case test suite: 6 FAQ, 5 bug, 4 handoff, 4 edge. |
| `online_shop_faq.md` | The shop FAQ (32 entries) injected into the prompt. |
| `cloudformation-tool.yaml` | DynamoDB table, Lambda, and three IAM roles. |
| `cloudformation-testing.yaml` | S3 bucket + `bedrock-eval-role` for Bedrock Evaluations. |
| `create_bug_report.py` | Lambda source (mirrors the copy embedded in the template). |
| `setup_gateway.py` | Creates the gateway, registers the Lambda as a tool, writes `agentcore_config.json`. |
| `create_harness.py` | Creates or updates the harness from `system_prompt.txt`. |
| `chat.py` | Interactive multi-turn terminal client. |
| `generate-eval-dataset.py` | Runs the test suite, emits `output_eval_dataset.jsonl`. |
| `cleanup_agentcore.py` | Deletes harness, gateway target, and gateway. |
| `docs/tools-setup.md` | Detailed Step 1 walkthrough + troubleshooting. |
| `docs/testing.md` | Detailed Step 3 walkthrough + Bedrock Evaluations config. |

## Steps taken

### 1. Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # boto3 1.43.76
aws configure                            # us-east-1
aws sts get-caller-identity              # confirm credentials
```

boto3 **1.43+** is mandatory — the `bedrock-agentcore` and
`bedrock-agentcore-control` clients do not exist in earlier releases.

### 2. Deploy the tool stack

```bash
aws cloudformation deploy \
  --template-file cloudformation-tool.yaml \
  --stack-name bug-report-tool-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### 3. Create the gateway

```bash
python setup_gateway.py
```

Reads the stack outputs, creates gateway
`bug-report-tool-stack-gateway`, registers target `bugreports` with the
`create_bug_report` tool schema, and writes `agentcore_config.json`.

### 4. Write the system prompt and create the harness

`system_prompt.txt` is structured as an explicit procedure rather than a
description:

- **Step 1 — classify** into bug report / platform question / anything
  else, with rules distinguishing a *policy complaint* from a *bug* and a
  stickiness rule so mid-collection fragments ("Chrome on Windows") aren't
  reclassified.
- **Step 2A — bug reports:** review what's already collected, never re-ask,
  ask exactly one question per turn, and file only when all three fields
  are genuinely present. Explicit prohibition on placeholders (`unknown`,
  `N/A`, empty strings).
- **Step 2B — platform questions:** answer *only* from the FAQ, don't round
  or paraphrase stated numbers, fall through to the handoff when coverage
  is partial.
- **Step 2C — handoff:** two or three sentences, phone number, no
  speculation.

```bash
python create_harness.py     # ~2-3 min on first creation
```

The script substitutes `{{FAQ}}` with `online_shop_faq.md`, producing a
12,189-character system prompt, and pins Nova Pro with temperature 0 and
topK 1 for reliable tool calling.

### 5. Manual smoke test

```bash
python chat.py
```

One conversation per run; the same `runtimeSessionId` is reused for every
turn, which is what makes multi-turn bug collection possible.

### 6. Automated test run

```bash
python generate-eval-dataset.py --tests-json harness-tests.json
```

19/19 harness calls succeeded, producing `output_eval_dataset.jsonl` in the
Bedrock Evaluations bring-your-own-inference format.

### 7. Testing stack

```bash
aws cloudformation deploy \
  --template-file cloudformation-testing.yaml \
  --stack-name bug-report-testing-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### 8. Teardown

```bash
python cleanup_agentcore.py
aws cloudformation delete-stack --stack-name bug-report-tool-stack --region us-east-1
BUCKET=udacity-agentic-engineer-c1-eval-<ACCOUNT_ID>
aws s3 rm "s3://$BUCKET" --recursive
aws cloudformation delete-stack --stack-name bug-report-testing-stack --region us-east-1
```

## Results

From the run of all 19 cases against the live harness:

**Working correctly (16/19)**

- All 6 FAQ cases answered accurately from the document, with figures quoted
  exactly ("30 days", "3–10 business days", "within 7 days with photos").
- All 4 handoff cases correctly declined rather than inventing policy —
  including warranty terms, customs duties, and wholesale pricing, none of
  which the FAQ covers.
- `edge-01` handled a mixed message: filed the bug ticket *and* answered the
  FAQ question in one reply.
- `edge-02` refused to fabricate ticket details on request.
- `edge-03` correctly treated a slow-refund complaint as a platform
  question, not a bug.
- `edge-04` declined to disclose the system prompt.
- `bug-01` and `bug-02` filed tickets from complete single-message reports,
  asking no unnecessary questions.

**Failures (3/19)** — see Known issues below.

## Known issues

### 1. Premature tool calls on incomplete bug reports

`bug-03` ("your website is broken") and `bug-05` (description + environment,
**no** steps to reproduce) both filed tickets instead of asking a question.

The mechanism is visible in `bug-04`, which passed only by accident: the
model called the tool first, the Lambda rejected it for a missing field, and
*then* it asked the customer. The prompt's "do not call the tool until you
have all three" rule is not being honored — Nova Pro calls first and leans
on the Lambda to bounce it.

That guard only catches **empty** fields. For `bug-03` and `bug-05` the
model supplied plausible-sounding but fabricated non-empty strings, which
sail straight through. Fixing this properly needs both halves:

- prompt: make the pre-call check a hard, restated gate rather than a rule
  stated once;
- Lambda: reject fabricated-looking values, not just empty ones (e.g. a
  minimum length, or rejecting steps that don't describe an action).

### 2. `<thinking>` spans leak into customer-facing output

14 of 19 responses begin with a visible `<thinking>…</thinking>` block. Nova
streams its reasoning, and neither `chat.py` nor `generate-eval-dataset.py`
filters it — the course's lesson-6 client did. This pollutes both the chat
UX and the eval dataset, since the judge model scores the reasoning along
with the answer. Fix by stripping the span in both clients before printing
or recording.

### 3. Bedrock Evaluations job not run

The dataset was generated and the testing stack deployed, but the JSONL was
never uploaded to S3 and no evaluation job was created, so there are no
LLM-as-a-judge scores. See [docs/testing.md](docs/testing.md) for the
console configuration.

### 4. Multi-turn collection is untested by the suite

`generate-eval-dataset.py` sends exactly one message per case in a fresh
session, so a genuine four-turn collection sequence can only be verified by
hand with `chat.py`. This is a property of the harness runner, not a gap in
the test suite.

## Reproducing

```bash
source .venv/bin/activate
aws cloudformation deploy --template-file cloudformation-tool.yaml \
  --stack-name bug-report-tool-stack --capabilities CAPABILITY_NAMED_IAM --region us-east-1
python setup_gateway.py
python create_harness.py
python chat.py
```

`setup_gateway.py` is **not** idempotent — running it a second time fails
with `ConflictException: A gateway with name '...' already exists`. Run
`python cleanup_agentcore.py` first, or reuse the existing
`agentcore_config.json`.

Iterating on the prompt needs no redeploy and no "prepare" step:

```bash
# edit system_prompt.txt
python create_harness.py    # updates the existing harness in place
```
