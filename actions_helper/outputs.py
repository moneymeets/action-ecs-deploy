from dataclasses import dataclass


@dataclass(frozen=True)
class CreateTaskDefinitionOutput:
    previous_task_definition_arn: str
    latest_task_definition_arn: str


@dataclass(frozen=True)
class RunPreflightOutput:
    preflight_task_arn: str
