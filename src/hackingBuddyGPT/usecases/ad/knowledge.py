class Knowledge:
    """A small, explicit episodic memory shared across the planner and its ephemeral executors.

    It holds two tables -- compromised accounts and free-form entity information -- keyed by an
    auto-incrementing integer id and rendered to the LLM as markdown tables. Each executor gets a
    fresh, *local* Knowledge; the planner merges only the executor's newly-touched (``dirty``)
    entries back into its global Knowledge via :meth:`merge`. Ported near-verbatim from cochise's
    ``knowledge.py`` (the rich-console logging was dropped; the framework already logs every tool
    call).
    """

    def __init__(self):
        self.compromised_accounts = {}
        self.entity_information = {}
        self.counter = 1

    def _numeric_key(self, key) -> "int | None":
        """Return the integer value of a key, or None if it is not numeric.

        The id/index of every entry is supposed to be numeric. The LLM occasionally passes a
        non-numeric identifier (e.g. a username or entity name) as the key, so we cannot blindly
        cast keys to int.
        """
        try:
            return int(str(key).strip())
        except (TypeError, ValueError):
            return None

    def merge(self, other_knowledge):
        """Merge another Knowledge instance into this one, taking only its dirty entries."""
        if not other_knowledge:
            return

        for key, value in other_knowledge.compromised_accounts.items():
            if value["dirty"]:
                numeric_key = self._numeric_key(key)
                if numeric_key is not None and numeric_key >= self.counter:
                    self.counter = numeric_key + 1
                self.compromised_accounts[key] = value
                self.compromised_accounts[key]["dirty"] = False

        for key, value in other_knowledge.entity_information.items():
            if value["dirty"]:
                numeric_key = self._numeric_key(key)
                if numeric_key is not None and numeric_key >= self.counter:
                    self.counter = numeric_key + 1
                self.entity_information[key] = value
                self.entity_information[key]["dirty"] = False

    async def add_compromised_account(self, username: str, password: str, context: str) -> str:
        self.compromised_accounts[self.counter] = {
            "username": username,
            "password": password,
            "context": context,
            "dirty": True,
        }
        self.counter += 1
        return f"noted compromised account {username} with context: {context}"

    def _resolve_key(self, store: dict, key, identity_field: str, identity_value: str) -> int:
        """Resolve the integer key of the entry to update.

        If ``key`` is numeric and already identifies an existing entry it is used as-is. Otherwise
        the LLM most likely passed a non-numeric identifier (e.g. the username/entity name) instead
        of the numeric id, so we try to locate the matching entry by its identity field; failing
        that we allocate a fresh numeric id so nothing is ever stored under a non-numeric key.
        """
        numeric_key = self._numeric_key(key)
        if numeric_key is not None and numeric_key in store:
            return numeric_key

        for existing_key, value in store.items():
            if value.get(identity_field) == identity_value:
                return existing_key

        new_key = self.counter
        self.counter += 1
        return new_key

    async def update_compromised_account(self, key: int, username: str, password: str, context: str) -> str:
        key = self._resolve_key(self.compromised_accounts, key, "username", username)
        self.compromised_accounts[key] = {
            "username": username,
            "password": password,
            "context": context,
            "dirty": True,
        }
        return f"updated account {username} with context: {context}"

    async def add_entity_information(self, entity: str, information: str) -> str:
        self.entity_information[self.counter] = {
            "entity": entity,
            "information": information,
            "dirty": True,
        }
        self.counter += 1
        return f"noted information for entity {entity}: {information}"

    async def update_entity_information(self, key: int, entity: str, information: str) -> str:
        key = self._resolve_key(self.entity_information, key, "entity", entity)
        self.entity_information[key] = {
            "entity": entity,
            "information": information,
            "dirty": True,
        }
        return f"noted information for entity {entity}: {information}"

    def get_compromised_accounts_markdown_table(self) -> str:
        result = "| Id | Username | Password | Context |\n|-----|----------|----------|---------|\n"
        for key, account in self.compromised_accounts.items():
            result += f"| {key} | {account['username']} | {account['password']} | {account['context']} |\n"
        return result

    def get_entity_information_markdown_table(self) -> str:
        result = "| Id | Entity | Information |\n|---|----------|---------|\n"
        for key, entity in self.entity_information.items():
            result += f"| {key} | {entity['entity']} | {entity['information']} |\n"
        return result

    def get_knowledge(self) -> str:
        result = ""
        if len(self.compromised_accounts) > 0:
            result += "## Compromised Accounts\n\n"
            result += self.get_compromised_accounts_markdown_table()
            result += "\n\n"
        if len(self.entity_information) > 0:
            result += "## Entity Information\n\n"
            result += self.get_entity_information_markdown_table()
            result += "\n\n"
        return result
