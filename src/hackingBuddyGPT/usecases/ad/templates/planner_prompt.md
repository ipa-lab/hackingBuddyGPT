From all the tasks, identify those that can be performed next. Analyze those
tasks and decide which one should be performed next based on their likelihood to
achieve the objective.

Include relevant information for the selected task as its context. This includes
detailed information such as usernames, credentials, etc. You are allowed to
gather this information from throughout the whole task plan. Do only include information that is specific to our objective, do not generic information. Be very concise.

Note down findings and potential leads that might be relevant for future tasks.
Make sure to always include full information, i.e., always include the full hash
or token and not abbreviated ones.

## Requirements for every response:

1. **You MUST call the `perform_task` tool.** Every response must delegate
   exactly one task to the worker. Do not respond with text analysis alone.

2. **Include complete context.** The worker has no memory of previous rounds.
   The `next_step_context` field must include:
   - Target IP address(es) and domain name
   - Domain Controller IP for the relevant domain
   - Full credentials (username + password/hash) if the task requires authentication
   - Any relevant findings from the knowledge base

3. **Do not re-assign failed tasks.** If a worker reported that a task failed,
   you must either assign a modified version with a different approach/tool or
   mark the task as non-relevant and move on.

4. **Keep full information intact.** Always include full hashes, tokens, and
   passwords -- never abbreviate them.

The worker has NO memory of previous rounds. Everything it needs must be in the
context you provide.