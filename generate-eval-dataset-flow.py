#!/usr/bin/env python3
"""Run the Bedrock Flow against a test suite and emit a Bedrock Evaluations
JSONL dataset (LLM-as-a-judge, bring-your-own-inference).

    python generate-eval-dataset-flow.py --tests-json flow-tests.json \
        --flow-id ABCDEF1234 --flow-alias-id TSTALIASID

This is the flow counterpart to generate-eval-dataset.py, which drives the
AgentCore harness instead. A flow invocation is stateless and single-turn:
one message in, one branch runs, one output node replies.

Output format, one record per line:

    {"prompt": ..., "referenceResponse": ...,
     "modelResponses": [{"response": ..., "modelIdentifier": ...}]}
"""

import argparse
import json
import sys
from pathlib import Path

import boto3
from botocore.config import Config


def invoke_flow_once(client, flow_id, alias_id, node_name, prompt):
    """Send one message through the flow and return the output text.

    Only the branch selected by the condition node runs, so exactly one
    output node fires per invocation.
    """
    response = client.invoke_flow(
        flowIdentifier=flow_id,
        flowAliasIdentifier=alias_id,
        inputs=[{
            "content": {"document": prompt},
            "nodeName": node_name,
            "nodeOutputName": "document",
        }],
    )

    chunks = []
    for event in response["responseStream"]:
        if "flowOutputEvent" in event:
            doc = event["flowOutputEvent"]["content"]["document"]
            chunks.append(doc if isinstance(doc, str) else json.dumps(doc))
        elif "flowCompletionEvent" in event:
            reason = event["flowCompletionEvent"].get("completionReason")
            if reason and reason != "SUCCESS":
                raise RuntimeError(f"flow completed with reason: {reason}")
    return "\n".join(chunks).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tests-json", default="flow-tests.json",
                   help="Test suite JSON (see flow-test.json for the shape).")
    p.add_argument("--flow-id", required=True,
                   help="Flow identifier, from the flow's console page.")
    p.add_argument("--flow-alias-id", required=True,
                   help="Flow ALIAS identifier — not the version number.")
    p.add_argument("--input-node", default=None,
                   help="Flow input node name (default: from the tests file, "
                        "else FlowInputNode).")
    p.add_argument("--model-identifier", default="support-flow",
                   help="Label written to modelResponses[0].modelIdentifier.")
    p.add_argument("--out-jsonl", default="output_eval_dataset_flow.jsonl",
                   help="Where to write the eval dataset JSONL.")
    p.add_argument("--region", default="us-east-1", help="AWS region.")
    args = p.parse_args()

    suite = json.loads(Path(args.tests_json).read_text(encoding="utf-8"))
    tests = suite["tests"]
    node_name = (args.input_node
                 or suite.get("flowInputNode", {}).get("nodeName")
                 or "FlowInputNode")

    client = boto3.client(
        "bedrock-agent-runtime",
        region_name=args.region,
        config=Config(read_timeout=300, retries={"max_attempts": 1}),
    )

    out_path = Path(args.out_jsonl)
    n_ok = 0

    with out_path.open("w", encoding="utf-8") as f:
        for t in tests:
            prompt = t.get("prompt", "")
            try:
                response_text = invoke_flow_once(
                    client, args.flow_id, args.flow_alias_id, node_name, prompt)
                n_ok += 1
            except Exception as e:  # noqa: BLE001
                # Record failures rather than skipping them, so a broken
                # branch is visible in the dataset instead of silently absent.
                print(e, file=sys.stderr)
                response_text = f"[FLOW_ERROR] {type(e).__name__}: {e}"

            f.write(json.dumps({
                "prompt": prompt,
                "referenceResponse": t.get("expected", ""),
                "modelResponses": [{
                    "response": response_text,
                    "modelIdentifier": args.model_identifier,
                }],
            }, ensure_ascii=False) + "\n")
            print(f"{t['id']}: wrote eval line", file=sys.stderr)

    print(f"\nWrote {len(tests)} JSONL lines to {out_path} "
          f"({n_ok} flow calls succeeded).", file=sys.stderr)


if __name__ == "__main__":
    main()
