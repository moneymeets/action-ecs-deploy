from dataclasses import dataclass

import click
from botocore.client import BaseClient


class NonSingleValueError(Exception):
    pass


@dataclass
class Tag:
    key: str
    value: str


def format_tags(task_definition_tags: str) -> tuple[Tag, ...]:
    try:
        return tuple(
            Tag(tag.strip().split(":")[0], tag.strip().split(":")[1]) for tag in task_definition_tags.split(",")
        )
    except IndexError:
        raise ValueError(
            "Invalid task definition tag format, expects 'key:value,key:value'",
        )


def get_active_task_definition_arn_by_tag(
    *,
    ecs_client: BaseClient,
    task_definition_family_prefix: str,
    task_definition_tags: str,
    allow_initial_deployment: bool,
) -> str:
    tags = format_tags(task_definition_tags)

    active_task_definition_arns = ecs_client.list_task_definitions(
        familyPrefix=task_definition_family_prefix,
        status="ACTIVE",
        sort="DESC",
    )["taskDefinitionArns"]

    tagged_active_task_definitions = tuple(
        task_definition["taskDefinition"]["taskDefinitionArn"]
        for task_definition_arn in active_task_definition_arns
        if (
            task_definition := ecs_client.describe_task_definition(
                taskDefinition=task_definition_arn,
                include=["TAGS"],
            )
        )
        and all({"key": tag.key, "value": tag.value} in task_definition["tags"] for tag in tags)
    )

    # Allows for initial deployment of task definition.
    # Requires that the only other active task definition was created by Pulumi,
    # in order to prevent multiple deployed task definitions with different tags.
    if allow_initial_deployment and len(active_task_definition_arns) == 1:
        if {"key": "created_by", "value": "Pulumi"} not in ecs_client.describe_task_definition(
            taskDefinition=active_task_definition_arns[0],
            include=["TAGS"],
        )["tags"]:
            raise ValueError("Expected initial deployment to only have Pulumi task definition")
        return ""

    try:
        (task_definition,) = tagged_active_task_definitions
        click.echo(task_definition)
        return task_definition
    except ValueError as e:
        raise NonSingleValueError(
            f"Expected exactly one active task definition with tags {task_definition_tags}. "
            f"Found: {tagged_active_task_definitions}",
        ) from e
