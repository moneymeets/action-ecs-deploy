from typing import Any

import click
from botocore.client import BaseClient

from actions_helper.commands.get_active_task_definition_by_tag import get_active_task_definition_arn_by_tag
from actions_helper.outputs import CreateTaskDefinitionOutput
from actions_helper.utils import PLACEHOLDER_TEXT, set_error

KEYS_TO_DELETE_FROM_TASK_DEFINITION = (
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
)


def get_rendered_task_definition(ecs_client: BaseClient, task_definition_arn: str, image_uri: str) -> dict[str, Any]:
    task_definition = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)["taskDefinition"]

    try:
        (container_image,) = {
            container_definition["image"] for container_definition in task_definition["containerDefinitions"]
        }
        if container_image != PLACEHOLDER_TEXT:
            set_error(f"Not all values for containerDefinitions 'image' equal to '{PLACEHOLDER_TEXT}'")
    except ValueError:
        set_error("Only a single image name is allowed")

    for container_definition in task_definition["containerDefinitions"]:
        container_definition["image"] = image_uri

    for key in KEYS_TO_DELETE_FROM_TASK_DEFINITION:
        del task_definition[key]

    return task_definition


def create_task_definition(
    ecs_client: BaseClient,
    application_id: str,
    image_uri: str,
    deployment_tag: str,
) -> CreateTaskDefinitionOutput:
    active_task_definition_by_pulumi = get_active_task_definition_arn_by_tag(
        ecs_client=ecs_client,
        task_definition_family_prefix=application_id,
        task_definition_tags=f"created_by:Pulumi,Name:{application_id}",
        allow_initial_deployment=False,
    )

    task_definition = get_rendered_task_definition(
        ecs_client=ecs_client,
        task_definition_arn=active_task_definition_by_pulumi,
        image_uri=image_uri,
    )

    active_task_definition_by_github = get_active_task_definition_arn_by_tag(
        ecs_client=ecs_client,
        task_definition_family_prefix=application_id,
        task_definition_tags=f"created_by:{deployment_tag},Name:{application_id}",
        allow_initial_deployment=True,
    )

    deployed_task_definition = ecs_client.register_task_definition(
        **task_definition,
        tags=[
            {"key": "created_by", "value": deployment_tag},
            {"key": "Name", "value": application_id},
        ],
    )["taskDefinition"]["taskDefinitionArn"]

    click.echo(f"previous_task_definition_arn={active_task_definition_by_github}")
    click.echo(f"latest_task_definition_arn={deployed_task_definition}")

    return CreateTaskDefinitionOutput(
        previous_task_definition_arn=active_task_definition_by_github,
        latest_task_definition_arn=deployed_task_definition,
    )
