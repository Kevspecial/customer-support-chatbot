# Evaluation Summary

I tested two versions of my customer support chatbot using an automated judge (an AI model).

## The Bottom Line:
The chatbot is doing a great job most of the time but has one specific, repeatable failure. The overall score is dragged down by a small number of questions where it fails in the exact same way.
## Overall Scores

    Support Chatbot (version 1): Scored 0.84 (Correctness)

    Support Chatbot (version 2): Scored 0.83 (Correctness)

# What the Scores Really Mean

A score of 0.84 does not mean the chatbot is 84% correct on every answer. Instead, the tests show it’s a "pass or fail" situation:

    16 out of 19 questions answered perfectly (score of 1.0).

    3 out of 19 questions answered completely wrong (score of 0.0).

This means the issue is not that the AI is generally bad. It has a specific problem that needs a focused fix.
Where the Chatbot is Strong

    FAQ Questions: It perfectly answers questions about returns, refunds, damaged items, and promotions by quoting the FAQ directly.

    "Hand-off" Questions: When asked about things not in the FAQ (like warranty or customs), it correctly refuses to guess and tells the customer to contact support.

Where the Chatbot Fails (The Main Problem)

All three failed tests were related to bug reports. The AI is too eager to file a report.

    The Failure: If a user says "your website is broken" but doesn't give the specific details we require, the AI should ask for more information. Instead, it invents missing details (like steps to reproduce the error) and files a fake ticket.

    Why it happens: The AI's instructions say "don't file a report until you have all three required pieces of info." The AI ignores this rule and tries anyway. A safety feature (a "guard") in the system blocks it only if a field is completely empty. However, if the AI invents fake info (which isn't empty), the guard fails and a fake ticket is created.

# A Surprising Discovery

On one test, the AI invented a whole policy about customs and duty fees that wasn’t in the FAQ. It was a complete hallucination. The scoring system measured this as:

    Faithfulness (0.98): Very high score, meaning the answer sounded consistent with itself and the FAQ.

    Correctness (0.83): Lower score, meaning the answer was factually wrong.

## Lesson:
 A high score in "Faithfulness" does not mean the AI isn't making things up. You need a "Correctness" test to catch hallucinations.
