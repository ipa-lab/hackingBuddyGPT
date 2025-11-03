You are given the following objective by the user:

```
{{ scenario }}
```

You are given the following hierarchical task plan:

```
{{ plan }}
```

From all the tasks, identify those that can be performed next. Analyze those tasks and decide which ones should be performed next based on their likelihood to achieve the objective. Call the function `execute_task` once for each task with a description of the selected task as its argument.

Write the task description as if you were passing the task on to a junior pentester. Include relevant information for the selected tasks as its context. This includes detailed information such as usernames, credentials, etc. You are allowed to gather this information from throughout the whole task plan. Do only include information that is specific to our objective, do not generic information.

Keep in mind, that you are only done if you have found all flags!
