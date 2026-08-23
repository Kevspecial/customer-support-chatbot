# Testing and Evaluation

This guide covers Step 3: turning your chatbot into something you can test
repeatedly, and scoring the results with Amazon Bedrock Evaluations using
LLM-as-a-judge.

## The testing model

There are two levels, and they test different things:

| | `chat.py` | `generate-eval-dataset.py` |
|---|---|---|
| Session | one conversation, many turns | a **fresh session per test case** |
| Input | you type, interactively | one user message per case |
| Captures | everything, including `[tool call]` lines | only the **final assistant reply** |
| Good for | multi-turn collection, tool calls, debugging | regression scoring across many cases |

### The single-turn constraint — read this before writing tests

`generate-eval-dataset.py` sends **exactly one user message** per test case
and records the final reply. Your prompt correctly asks for missing bug
details one question at a time, which means:

> A vague bug report can only ever produce a **clarifying question** in an
> eval run. It can never produce a ticket.

So write your bug-report cases in two flavours:

- **complete in one message** — description, steps, and environment all
  present. This is the only way an eval run exercises the tool path, so it
  is the case that proves `create_bug_report` actually fires.
- **incomplete** — expect a single clarifying question naming the missing
  field, and explicitly expect *no* ticket.

Genuine multi-turn collection — asking one question at a time across four
turns and filing at the end — can only be verified by hand with `chat.py`.
Say so in your writeup; it is a property of the harness, not a gap in your
work.

## 1. Write the test suite

Copy the template and fill it in:

```bash
cp harness-tests-template.json harness-tests.json
```

Each case is `{"id", "prompt", "expected"}`. `expected` is written into the
JSONL as `referenceResponse` — the ideal answer the judge model compares
against — so write it as a description of the correct response, grounded in
the FAQ, not as a keyword list.

Cover all three routes. The README's stated minimum is one FAQ question, one
bug report, and one out-of-scope request; a suite that actually catches
regressions wants more:

- **FAQ route** — several questions whose answers are unambiguous in
  `online_shop_faq.md` (return window, refund timing, damaged goods, promo
  codes, password reset, tracking).
- **Bug route** — one complete report, plus one case per missing field, plus
  a report buried in an angry complaint.
- **Handoff route** — questions that sound answerable but that the FAQ does
  **not** cover. Warranty terms, customs and import duties, and wholesale
  pricing are all real gaps in this FAQ, which makes them good tests of
  whether the model invents policy.
- **Edge cases** — a message mixing a bug report and an FAQ question, a
  policy complaint that must *not* be classified as a bug, a request to
  fabricate ticket details, and an attempt to extract the system prompt.

`harness-tests.json` in this repo is a worked example with 19 such cases.

## 2. Generate the dataset

```bash
python generate-eval-dataset.py --tests-json harness-tests.json
```

Each case runs against the live harness, so this costs real inference and
takes roughly a few seconds per case. Output goes to
`output_eval_dataset.jsonl`, one record per line:

```json
{"prompt": "...", "referenceResponse": "...",
 "modelResponses": [{"response": "...", "modelIdentifier": "my-support-chatbot"}]}
```

Useful flags: `--model-identifier` labels the run (set it to something like
`prompt-v2` so you can tell iterations apart), and `--out-jsonl` renames the
output.

**Read the JSONL before uploading it.** If a case failed, its response is
`[HARNESS_ERROR] ...` — the script deliberately records failures rather than
skipping them. Fix those before spending money on an evaluation job:

```bash
grep -c HARNESS_ERROR output_eval_dataset.jsonl
python -c "import json;[print(json.loads(l)['modelResponses'][0]['response'][:120]) for l in open('output_eval_dataset.jsonl')]"
```

Also confirm tickets really landed for your complete-bug-report cases:

```bash
aws dynamodb scan --table-name bug-report-tool-stack-bug-reports --region us-east-1
```

A reply that quotes a ticket ID with no matching DynamoDB row means the
model fabricated it — a prompt bug, and exactly the kind of thing the
grounding rules in `system_prompt.txt` exist to prevent.

## 3. Deploy the testing stack

```bash
aws cloudformation deploy \
  --template-file cloudformation-testing.yaml \
  --stack-name bug-report-testing-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

This creates an S3 bucket named
`udacity-agentic-engineer-c1-eval-<YOUR_ACCOUNT_ID>` and an IAM role
`bedrock-eval-role` that Bedrock assumes to read the dataset, write results,
and invoke the judge model.

Upload the dataset:

```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name bug-report-testing-stack \
  --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='EvalDatasetBucketName'].OutputValue" \
  --output text)
aws s3 cp output_eval_dataset.jsonl s3://$BUCKET/input/
```

## 4. Create the evaluation job

In the Bedrock console (us-east-1), go to **Evaluations → Model
evaluation → Create**, and configure:

| Field | Value |
|-------|-------|
| Evaluation type | Automatic |
| Inference source | **Bring your own inference responses** |
| Evaluator model | Amazon Nova Pro |
| Dataset S3 URI | `s3://<bucket>/input/output_eval_dataset.jsonl` |
| Results S3 URI | `s3://<bucket>/output/` |
| IAM role | `bedrock-eval-role` |

Pick metrics that match what your prompt promises. **Correctness** and
**Completeness** catch FAQ answers that drift from the document;
**Faithfulness** catches invented policy; **Helpfulness** catches replies
that are accurate but unusable. **Harmfulness** is largely inert for this
dataset.

The job takes several minutes. Results land in the results S3 URI and are
viewable in the console.

## 5. Read the results and iterate

Scores matter less than *which* cases scored badly. Common patterns:

- **A handoff case scored low on correctness** — the model answered a
  question the FAQ does not cover. Tighten Step 2B's "if the FAQ does not
  cover it, switch to Step 2C" rule.
- **A complete bug report produced a question instead of a ticket** — the
  model did not recognise all three fields were present. Make the "if all
  three items are present, do not ask anything" rule more prominent.
- **A ticket was filed with a placeholder environment** — the Lambda's
  missing-field guard should have caught an empty string, but "unknown" is
  not empty. Strengthen the no-placeholder rule in the prompt.
- **A policy complaint was filed as a bug** — sharpen the
  complaint-versus-bug distinction in Step 1.

The iteration loop is fast, and there is no redeploy or "prepare" step:

```bash
# edit system_prompt.txt
python create_harness.py                                    # updates in place
python generate-eval-dataset.py --tests-json harness-tests.json \
  --model-identifier prompt-v3 --out-jsonl eval-v3.jsonl
```

Keeping each run's JSONL under a distinct `--model-identifier` lets you
compare prompt versions rather than just looking at one score in isolation.

## Cleanup

Empty the bucket **before** deleting the testing stack — CloudFormation
cannot delete a bucket that still has objects in it, and the stack will end
up in `DELETE_FAILED`:

```bash
python cleanup_agentcore.py
aws cloudformation delete-stack --stack-name bug-report-tool-stack --region us-east-1
aws s3 rm s3://$BUCKET --recursive
aws cloudformation delete-stack --stack-name bug-report-testing-stack --region us-east-1
```

If the testing stack is already `DELETE_FAILED`, empty the bucket and rerun
its `delete-stack` command.
