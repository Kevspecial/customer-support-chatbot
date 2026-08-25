# Screenshots

Evidence images for the project submission. Each entry says what the image
shows and which rubric item it supports.

| Image | Shows |
|-------|-------|
| [aws console.png](aws%20console.png) | Full AgentCore setup run in one terminal session. |
| [harness.png](harness.png) | The same run, wider view. Near-duplicate of the above. |
| [aws1.png](aws1.png) | Testing stack deployment. |
| [chat show tool call and ticketid.png](chat%20show%20tool%20call%20and%20ticketid.png) | `chat.py` bug-report conversation with the tool call and ticket IDs. |
| [faq and bug prompt.png](faq%20and%20bug%20prompt.png) | Flow diagram, condition node expressions, and two passing test runs. |
| [other prompt.png](other%20prompt.png) | Flow diagram with the import-duty test run. |

---

## aws console.png / harness.png

A single terminal session covering Step 1 and Step 2 end to end:

- `aws cloudformation deploy` creating `bug-report-tool-stack`
- `setup_gateway.py` creating gateway
  `bug-report-tool-stack-gateway-v1wzguqnty`, reaching status `READY`, and
  registering Lambda target `bugreports` with the tool `create_bug_report`
- `create_harness.py` loading the system prompt (14,087 characters after the
  FAQ is substituted for `{{FAQ}}`), polling through `CREATING`, and
  reporting the harness `support_chatbot-Nq0RyI4o4a` as `READY`

Together these evidence the tool, the gateway wiring, and the harness. The
two images are the same run — `harness.png` is the wider VS Code capture.
One of them can be dropped.

## aws1.png

`aws cloudformation deploy` creating `bug-report-testing-stack`, which
provisions the S3 bucket and the `bedrock-eval-role` used by Bedrock
Evaluations. Supports the testing-infrastructure part of Step 3.

## chat show tool call and ticketid.png

A `chat.py` session captured with `script`, showing the
`[tool call] bugreports___create_bug_report` line and the ticket IDs returned
to the customer.

> **Needs re-capturing before submission.** The rubric requires the assistant
> to collect the description, steps to reproduce, and environment *before*
> calling the tool. In this transcript the tool fires on turn 1, in response
> to "Hi, something on your site isn't working" — a message containing none
> of the three fields — and the follow-up questions come afterwards. It also
> shows a second fabricated ticket re-quoted across three turns, and an
> unprompted refund explanation the customer never asked for.
>
> Re-run after `create_harness.py` has pushed the current `system_prompt.txt`
> (the version containing the `THE GATE` section), opening with a vague bug
> report and answering one question per turn.

## faq and bug prompt.png

The Bedrock Flow `customers-requestss` in the flow builder. This one image
covers two rubric requirements at once:

- **Full flow diagram** — `Flow Input` fanning out to `classifier`,
  `Prompt_2`, `Prompt_3`, and `Prompt_4`; the condition node routing to the
  three responders; and each responder terminating at its own output node
  (`FlowOutputNode_1`, `_2`, `_3`).
- **Condition node expressions** — the `category` node showing
  `category == "bug"` → `Prompt_2`, `category == "faq"` → `Prompt_3`, and
  the "if all conditions are false" default → `Prompt_4`.

The test panel on the right shows two correct runs: a complete bug report
routed to `FlowOutputNode_1` and answered without inventing a ticket ID, and
a refund-timing complaint routed to `FlowOutputNode_2` and answered with the
FAQ's 3–10 business day figure.

Still missing for the classifier requirement: a capture of the `classifier`
node's own configuration panel, showing its prompt text and temperature 0.

## other prompt.png

The same flow, scrolled, with the test panel showing the message *"If I order
from Germany, will I have to pay import duty?"* routed to `FlowOutputNode_2`.

> **Documents a bug, not a success.** The reply invents an entire customs
> policy — duties levied by German customs, charges payable on delivery, "we
> have no control over these charges" — none of which appears in
> `online_shop_faq.md`. The cause is that `Prompt_3` contained the raw FAQ
> with no grounding instructions, so the model answered from general
> knowledge.
>
> The fix is in [../flow-prompts/faq-responder.txt](../flow-prompts/faq-responder.txt),
> which adds "answer only from the FAQ" and an explicit hand-off rule naming
> import duties and customs as not covered. After pasting it into `Prompt_3`
> and re-preparing, this message should return the 1-800-555-0199 hand-off.
> Re-capture then — it makes a good demonstration of the hand-off path.

---

## Note on filenames

Several filenames contain spaces, which need URL-encoding in Markdown links
and are awkward to reference from a submission. Renaming them to
hyphenated lowercase (`aws-console.png`, `flow-diagram.png`, and so on) would
be tidier, though nothing depends on it.
