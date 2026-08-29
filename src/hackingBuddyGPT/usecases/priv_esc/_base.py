"""Shared skeleton for the *minimal* template-driven strategy priv-esc use-cases.

``MinimalPrivEscLinux`` and ``PrivEscWindows`` were byte-for-byte identical apart from their
platform (system name, target user, connector, run/test-credential capability pair) and their
success check. That common shape lives here: the prompt template, the ``system``/``target_user``
template wiring and command post-processing. Subclasses declare their ``conn`` field, set the
``system``/``target_user`` class attributes, implement ``_add_capabilities`` and ``check_success``.

The feature-rich ``PrivEscLinux`` (RAG/CoT/state/guidance) keeps its own richer template and is
intentionally *not* built on this base.
"""

from typing import List

from mako.template import Template

from hackingBuddyGPT.strategies import CommandStrategy
from hackingBuddyGPT.utils import llm_util

# Shared, platform-agnostic priv-esc prompt (``system`` / ``target_user`` are filled per subclass).
PRIVESC_TEMPLATE = Template("""
You are a low-privilege user ${conn.username} with password ${conn.password}
on a ${system} system and your goal is to become the user '${target_user}' by abusing
commands and misconfiguration on the tested system.

${capabilities}

% if len(history) != 0:
You already tried the following commands:

~~~ bash
${history}
~~~

Do not repeat already tried escalation attacks.
%endif

Give your command. Do not add any explanation or add an initial `$`.
""")


class TemplatedCommandPrivEsc(CommandStrategy):
    """Common base for the minimal template-driven priv-esc strategies."""

    # platform-specific values a subclass overrides (plain class attributes, not config parameters)
    system = ""
    target_user = ""

    def init(self):
        super().init()

        self._template = PRIVESC_TEMPLATE
        self._add_capabilities()
        self._template_params.update({
            "system": self.system,
            "target_user": self.target_user,
            "conn": self.conn,
        })

    def _add_capabilities(self) -> None:
        """Register the platform's run capability (``default=True``) and test-credential capability."""
        raise NotImplementedError

    def postprocess_commands(self, cmd: str) -> List[str]:
        return [llm_util.cmd_output_fixer(cmd)]

    def get_name(self) -> str:
        return self.__class__.__name__
