### UNTESTED!
from dataclasses import dataclass


from jinja2 import Template

from hackingBuddyGPT.utils.openai.openai_lib import OpenAILib


@dataclass
class PlanTestTreeStrategy:
    plan: str
    scenario: str
    llm: OpenAILib

    def next_task_prompt(self) -> str:
        template_path = __file__.replace(".py", "/prompts/ptt_next_task.md")
        with open(template_path, "r") as f:
            template_text = f.read()
        template = Template(template_text)
        return template.render(scenario=self.scenario, plan=self.plan)

    def update_prompt(self) -> str:
        template_path = __file__.replace(".py", "/prompts/ptt_update_plan.md")
        with open(template_path, "r") as f:
            template_text = f.read()
        template = Template(template_text)
        return template.render(scenario=self.scenario, plan=self.plan, last_task=self._last_task)

    def update_plan(self, last_task: ExecutedTask) -> None:
        if last_task != None:
            history_size = reduce(lambda value, x: value + len(x["cmd"]) + len(x["result"]), last_task.cmd_history, 0)
            if history_size >= 100000:
                print(f"!!! warning: history size {history_size} >= 100.000, removing it to cut down costs")
                last_task.cmd_history = []

        input = {"user_input": self.scenario, "plan": self.plan, "last_task": last_task}

        replanner = TEMPLATE_UPDATE | self.llm.with_structured_output(UpdatedPlan, include_raw=True)
        tik = datetime.datetime.now()
        result = replanner.invoke(input)
        tok = datetime.datetime.now()

        # output tokens
        metadata = result["raw"].response_metadata
        print(str(metadata))

        self.logger.write_llm_call(
            "strategy_update",
            TEMPLATE_UPDATE.invoke(input).text,
            result["parsed"].plan,
            result["raw"].response_metadata,
            (tok - tik).total_seconds(),
        )

        self.plan = result["parsed"].plan

    def select_next_task(self, llm=None) -> PlanResult:
        input = {
            "user_input": self.scenario,
            "plan": self.plan,
        }

        select = TEMPLATE_NEXT | llm.with_structured_output(PlanResult, include_raw=True)
        tik = datetime.datetime.now()
        result = select.invoke(input)
        tok = datetime.datetime.now()

        # output tokens
        print(str(result["raw"].response_metadata))

        if isinstance(result["parsed"].action, PlanFinished):
            self.logger.write_llm_call(
                "strategy_finished",
                TEMPLATE_NEXT.invoke(input).text,
                result["parsed"].action.response,
                result["raw"].response_metadata,
                (tok - tik).total_seconds(),
            )
        else:
            self.logger.write_llm_call(
                "strategy_next_task",
                TEMPLATE_NEXT.invoke(input).text,
                {
                    "next_step": result["parsed"].action.next_step,
                    "next_step_context": result["parsed"].action.next_step_context,
                },
                result["raw"].response_metadata,
                (tok - tik).total_seconds(),
            )
        return result["parsed"]

    def get_plan(self) -> str:
        return self.plan
