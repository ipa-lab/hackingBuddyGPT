To achieve the scenario, focus upon the following task:

`${next_step}`

You are given the following additional information about the task:

```
${next_step_context}
```
${knowledge_block}
You have up to ${max} tries to achieve the given task, stop if you were not able
to achieve it before that. If successful give a short technical summary.

Always note down findings and potential leads.

If you encounter errors, try to solve them.

## Execution rules:

1. **Never retry the same command more than twice.** If a command produces
   empty output or the same error on two attempts, it will not work on a third.
   Either try a fundamentally different tool/approach or report the failure.

2. **Empty output means failure.** Tools like `nxc` often return empty stdout
   on authentication failure rather than an error message.  Treat empty output as
   a failed attempt.

3. **Stop early on success.** If you achieved the task objective in round 3, do
   not continue running commands for the remaining rounds. Immediately provide
   your summary.

4. **Stop early on dead ends.** If after 3-4 rounds you have made no progress
   and have no new ideas, provide a summary of what you tried, what failed, and
   why, so the planner can adjust strategy.

5. **Report failures specifically.** Your summary must include: what was
   attempted, what the specific error or failure was, and what alternative
   approaches might work.
