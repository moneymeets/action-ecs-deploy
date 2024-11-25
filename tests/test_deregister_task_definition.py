import unittest
from typing import Any, Literal
from unittest.mock import Mock, call, patch

import boto3

from actions_helper.commands.deregister_task_definition import deregister_task_definition
from actions_helper.outputs import CreateTaskDefinitionOutput


class DeregisterTaskDefinitionTestCase(unittest.TestCase):
    @patch.object(boto3, attribute="client")
    def setUp(self, boto3_client):
        self.ecs_client = boto3_client

    @staticmethod
    def describe_service_return_value(status: Literal["ACTIVE", "INACTIVE", "PRIMARY"], arn: str) -> dict[str, Any]:
        return {"services": [{"deployments": [{"status": status, "taskDefinition": arn}]}]}

    def test_deregister_task_definition_no_task_definitions(self):
        with (
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=""),
            ) as ecs_describe_services_patch,
            self.assertRaises(SystemExit),
        ):
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                production_task_definition_output=None,
                preflight_task_definition_output=None,
                local_task_definition_output=None,
                run_preflight=True,
            )
            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_not_called()

    def test_deregister_task_definition_failed_pipeline(self):
        local_exec_task_definition_1 = Mock()
        with (
            self.subTest("Failed initial deployment"),
            self.assertRaises(SystemExit),
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=""),
            ) as ecs_describe_services_patch,
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
        ):
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                local_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn="",
                    latest_task_definition_arn=local_exec_task_definition_1,
                ),
                production_task_definition_output=None,
                preflight_task_definition_output=None,
                run_preflight=True,
            )
            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_called_once_with(local_exec_task_definition_1)

        with (
            self.subTest("Failed deployment"),
            self.assertRaises(SystemExit),
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=""),
            ) as ecs_describe_services_patch,
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
        ):
            local_exec_task_definition_2 = Mock(return_value="local_exec_arn_2")
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                local_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=local_exec_task_definition_1,
                    latest_task_definition_arn=local_exec_task_definition_2,
                ),
                production_task_definition_output=None,
                preflight_task_definition_output=None,
                run_preflight=True,
            )
            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_called_once_with(local_exec_task_definition_2)

    def test_deregister_task_definition_successful_initial_deploy(self):
        local_task_definition_1 = production_task_definition_1 = preflight_task_definition_1 = Mock()

        with (
            self.subTest("Successful initial deployment"),
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=production_task_definition_1),
            ) as ecs_describe_services_patch,
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
        ):
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                local_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn="",
                    latest_task_definition_arn=local_task_definition_1,
                ),
                production_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn="",
                    latest_task_definition_arn=production_task_definition_1,
                ),
                preflight_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn="",
                    latest_task_definition_arn=preflight_task_definition_1,
                ),
                run_preflight=True,
            )

            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_not_called()

    def test_deregister_task_definition_successful_deploy(self):
        local_task_definition_1 = production_task_definition_1 = preflight_task_definition_1 = Mock()
        local_task_definition_2 = production_task_definition_2 = preflight_task_definition_2 = Mock()
        with (
            self.subTest("Successful deployment"),
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=production_task_definition_2),
            ) as ecs_describe_services_patch,
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
        ):
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                local_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=local_task_definition_1,
                    latest_task_definition_arn=local_task_definition_2,
                ),
                production_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=production_task_definition_1,
                    latest_task_definition_arn=production_task_definition_2,
                ),
                preflight_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=preflight_task_definition_1,
                    latest_task_definition_arn=preflight_task_definition_2,
                ),
                run_preflight=True,
            )

            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_has_calls(
                (
                    call(taskDefinition=local_task_definition_1),
                    call(taskDefinition=preflight_task_definition_1),
                    call(taskDefinition=production_task_definition_1),
                ),
            )

    def test_deregister_task_definition_successful_deploy_without_preflight(self):
        local_task_definition_1 = production_task_definition_1 = Mock()
        local_task_definition_2 = production_task_definition_2 = Mock()
        with (
            self.subTest("Successful deployment"),
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=production_task_definition_2),
            ) as ecs_describe_services_patch,
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
        ):
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                local_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=local_task_definition_1,
                    latest_task_definition_arn=local_task_definition_2,
                ),
                production_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=production_task_definition_1,
                    latest_task_definition_arn=production_task_definition_2,
                ),
                preflight_task_definition_output=None,
                run_preflight=False,
            )

            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_has_calls(
                (
                    call(taskDefinition=local_task_definition_1),
                    call(taskDefinition=production_task_definition_1),
                ),
            )

    def test_deregister_task_definition_failed_deployment(self):
        local_task_definition_1 = production_task_definition_1 = preflight_task_definition_1 = Mock()
        local_task_definition_2 = production_task_definition_2 = preflight_task_definition_2 = Mock()

        with (
            self.subTest("Failed deployment, roll back to previous task definition"),
            patch.object(
                self.ecs_client,
                attribute="describe_services",
                return_value=self.describe_service_return_value(status="PRIMARY", arn=production_task_definition_1),
            ) as ecs_describe_services_patch,
            patch.object(self.ecs_client, attribute="deregister_task_definition") as ecs_deregister_patch,
            self.assertRaises(SystemExit),
        ):
            deregister_task_definition(
                ecs_client=self.ecs_client,
                service="",
                cluster="",
                local_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=local_task_definition_1,
                    latest_task_definition_arn=local_task_definition_2,
                ),
                production_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=production_task_definition_1,
                    latest_task_definition_arn=production_task_definition_2,
                ),
                preflight_task_definition_output=CreateTaskDefinitionOutput(
                    previous_task_definition_arn=preflight_task_definition_1,
                    latest_task_definition_arn=preflight_task_definition_2,
                ),
                run_preflight=True,
            )

            ecs_describe_services_patch.assert_called()
            ecs_deregister_patch.assert_has_calls(
                (
                    call(taskDefinition=local_task_definition_2),
                    call(taskDefinition=preflight_task_definition_2),
                    call(taskDefinition=production_task_definition_2),
                ),
            )
