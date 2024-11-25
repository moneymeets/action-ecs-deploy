from typing import Optional

import click
from botocore.client import BaseClient

from actions_helper.outputs import CreateTaskDefinitionOutput
from actions_helper.utils import set_error


def deregister_task_definition(
    ecs_client: BaseClient,
    cluster: str,
    service: str,
    run_preflight: bool,
    production_task_definition_output: Optional[CreateTaskDefinitionOutput],
    local_task_definition_output: Optional[CreateTaskDefinitionOutput],
    preflight_task_definition_output: Optional[CreateTaskDefinitionOutput],
):
    (primary_deployment_definition_arn,) = (
        deployment["taskDefinition"]
        for deployment in ecs_client.describe_services(
            cluster=cluster,
            services=[service],
        )["services"][0]["deployments"]
        if deployment["status"] == "PRIMARY"
    )

    click.echo(f"{primary_deployment_definition_arn=}")

    fail_pipeline = True
    if (
        all(
            (
                production_task_definition_output,
                local_task_definition_output,
                *((preflight_task_definition_output,) if run_preflight else ()),
            ),
        )
        and primary_deployment_definition_arn == production_task_definition_output.latest_task_definition_arn
    ):
        # Do not deregister task definition for initial deployment
        if not production_task_definition_output.previous_task_definition_arn:
            return
        fail_pipeline = False

    for task_definition in (
        local_task_definition_output,
        preflight_task_definition_output,
        production_task_definition_output,
    ):
        if task_definition:
            click.echo(f"Deregister {task_definition}")
            ecs_client.deregister_task_definition(
                taskDefinition=task_definition.latest_task_definition_arn
                if fail_pipeline
                else task_definition.previous_task_definition_arn,
            )

    if fail_pipeline:
        set_error(message="Deployment failed; rollback triggered.")
