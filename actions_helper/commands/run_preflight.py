import click
from botocore.client import BaseClient

from actions_helper.commands.wait_for_task_stopped import wait_for_task_stopped
from actions_helper.outputs import RunPreflightOutput
from actions_helper.utils import set_error


def run_preflight_container(
    ecs_client: BaseClient,
    cluster: str,
    service: str,
    latest_task_definition_arn: str,
) -> RunPreflightOutput:
    network_config = ecs_client.describe_services(
        cluster=cluster,
        services=[service],
    )["services"][0]["networkConfiguration"]["awsvpcConfiguration"]

    click.echo("Running preflight task...")
    task_arn = ecs_client.run_task(
        cluster=cluster,
        count=1,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": network_config["subnets"],
                "securityGroups": network_config["securityGroups"],
                "assignPublicIp": "DISABLED",
            },
        },
        taskDefinition=latest_task_definition_arn,
    )["tasks"][0]["taskArn"]

    wait_for_task_stopped(ecs_client=ecs_client, cluster=cluster, task=task_arn)

    (stopped_preflight_container,) = ecs_client.describe_tasks(
        cluster=cluster,
        tasks=[task_arn],
    )["tasks"][0]["containers"]

    exit_code = stopped_preflight_container.get("exitCode")
    reason = stopped_preflight_container.get("reason")

    if exit_code != 0:
        set_error(f"Preflight container failed with a non zero exit code - {exit_code} \n Reason: {reason}")

    click.echo(f"preflight_task_arn={task_arn}")

    return RunPreflightOutput(preflight_task_arn=task_arn)
