# Capability

A capability is a simple function that can be used by an LLM to perform a task.

We currently support using capabilities in multiple ways, one of which is to manually parse out a capability call from LLM output
(as can be seen in the [Minimal Linux Priv-Escalation](/usecases/minimal/minimal.py)), or by using function calling / instructor
to automatically have the parameters passed and validated (as in [Web Page Hacking](/usecases/web/simple.py)).

Both of the approaches have their own advantages and disadvantages, and we are currently exploring those and further ones to see
which work best for our use-cases.
