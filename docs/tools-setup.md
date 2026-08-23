# Tools Setup

This guide covers Step 1 of the project: deploying the bug report tool and
exposing it to your chatbot through an AgentCore Gateway.

By the end you will have a DynamoDB table, a Lambda function, three IAM
roles, a gateway with one registered tool, and an `agentcore_config.json`
file that every later script reads.

## Prerequisites

- AWS credentials configured for **us-east-1**. Verify with
  `aws sts get-caller-identity`.
- Amazon Bedrock **and** Amazon Bedrock AgentCore enabled on the account.
- Model access granted for **Amazon Nova Pro** (`amazon.nova-pro-v1:0`) in
  the Bedrock console under *Model access*. The project pins
  `us.amazon.nova-pro-v1:0` everywhere; do not rely on the harness default
  model, which needs an AWS Marketplace subscription lab accounts cannot
  complete.
- Python 3.9+ and the pinned dependencies:

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

  boto3 **1.43+** is required — the AgentCore control-plane and runtime
  clients do not exist in older versions. Check with
  `python -c "import boto3; print(boto3.__version__)"`.

## 1. Deploy the tool stack

```bash
aws cloudformation deploy \
  --template-file cloudformation-tool.yaml \
  --stack-name bug-report-tool-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

`CAPABILITY_NAMED_IAM` is required because the template creates roles with
explicit names. The stack creates:

| Resource | Name |
|----------|------|
| DynamoDB table | `bug-report-tool-stack-bug-reports` |
| Lambda function | `bug-report-tool-stack-create-bug-report` (Python 3.12, 30s timeout) |
| Lambda execution role | `bug-report-tool-stack-lambda-role` |
| Gateway role | `bug-report-tool-stack-gateway-role` |
| Harness execution role | `bug-report-tool-stack-harness-role` |

Read the outputs back:

```bash
aws cloudformation describe-stacks \
  --stack-name bug-report-tool-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs' --output table
```

You should see `BugReportsTableName`, `BugReportsTableArn`,
`LambdaFunctionArn`, `LambdaExecutionRoleArn`, `GatewayRoleArn`, and
`HarnessExecutionRoleArn`. You do not need to copy any of these by hand —
`setup_gateway.py` reads them directly from the stack.

## 2. Test the Lambda in isolation

Do this before involving the gateway or the model. Debugging a broken tool
through a gateway through an agent loop is far harder than testing it
directly.

The gateway passes tool arguments **as the event itself** — there is no
`messageVersion` / `parameters` envelope like Bedrock Agents Classic used.
So a direct invoke uses exactly the shape the model will produce:

```bash
aws lambda invoke \
  --function-name bug-report-tool-stack-create-bug-report \
  --cli-binary-format raw-in-base64-out \
  --payload '{"description":"Checkout button does nothing","stepsToReproduce":"Add item to cart, click Pay now","environment":"Chrome 120 on Windows 11"}' \
  --region us-east-1 \
  /dev/stdout
```

Expected response:

```json
{"ticketId": "0f0f...-...", "status": "OPEN"}
```

Now test the guard rail — omit a field:

```bash
aws lambda invoke \
  --function-name bug-report-tool-stack-create-bug-report \
  --cli-binary-format raw-in-base64-out \
  --payload '{"description":"Something broke","stepsToReproduce":"","environment":"Chrome"}' \
  --region us-east-1 \
  /dev/stdout
```

Expected: an `error` telling the caller which fields are missing and to ask
the customer for them. This exists because models sometimes satisfy a
"required" parameter with an empty string; the error steers the model back
to asking rather than filing a useless ticket.

Confirm the successful ticket landed:

```bash
aws dynamodb scan \
  --table-name bug-report-tool-stack-bug-reports \
  --region us-east-1
```

Each item has `ticketId`, `description`, `stepsToReproduce`, `environment`,
`status` (`OPEN`), and `createdAt`.

## 3. Create the gateway and register the tool

```bash
python setup_gateway.py
```

This creates an MCP gateway with `AWS_IAM` authorization, then registers the
Lambda as a target named `bugreports` carrying one tool:

```
create_bug_report(description, stepsToReproduce, environment)
```

All three parameters are marked required in the tool's JSON Schema. The
model sees the tool namespaced as **`bugreports___create_bug_report`**
(three underscores) — that is the name you will see in `chat.py` output.

The script writes `agentcore_config.json`:

```json
{
  "region": "us-east-1",
  "stack_name": "bug-report-tool-stack",
  "table_name": "...",
  "lambda_arn": "...",
  "gateway_name": "bug-report-tool-stack-gateway",
  "gateway_id": "...",
  "gateway_arn": "...",
  "gateway_target_id": "...",
  "gateway_target_name": "bugreports",
  "harness_execution_role_arn": "..."
}
```

`create_harness.py`, `chat.py`, and `generate-eval-dataset.py` all read this
file. It is gitignored, since it is account-specific.

## Troubleshooting

**`setup_gateway.py` fails with an access or validation error naming a
role, right after the stack finished.** IAM propagation delay. The script
already retries three times with a 10-second gap; if it still fails, wait a
minute and run it again.

**`Model produced invalid sequence as part of ToolUse`.** The gateway target
name contains a dash. Target names may only contain letters, digits, and
underscores — this breaks Nova tool calling specifically. Use the default
`bugreports`, or pass `--target-name my_target`.

**`KeyError: 'LambdaFunctionArn'`.** The stack name passed to
`setup_gateway.py` does not match a deployed stack, or the deploy failed
partway. Check `aws cloudformation describe-stacks --stack-name
bug-report-tool-stack --region us-east-1`.

**Running `setup_gateway.py` twice** creates a second gateway. If you need a
clean slate, run `python cleanup_agentcore.py` first.

**The Lambda's view of reality.** Every invocation prints its raw event and
resolved tool name to CloudWatch Logs at
`/aws/lambda/bug-report-tool-stack-create-bug-report`. When the model
"claims" it filed a ticket but nothing appears in DynamoDB, this log is the
ground truth for whether the Lambda was ever called.

## Next

Step 2 — write your system prompt in `system_prompt.txt`, then:

```bash
python create_harness.py    # first run takes ~2-3 minutes
python chat.py
```
