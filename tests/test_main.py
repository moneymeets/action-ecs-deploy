import unittest
from typing import Any
from unittest.mock import Mock, patch

from click.testing import CliRunner

from actions_helper.main import cmd_ecs_deploy
from actions_helper.outputs import CreateTaskDefinitionOutput
from tests.utils import TEST_APPLICATION_ID, TEST_AWS_DEFAULT_REGION

TEST_ENVIRONMENT = "dev"


@patch("actions_helper.main.boto3.Session")
@patch(
    "actions_helper.main.create_task_definition",
    return_value=CreateTaskDefinitionOutput(
        latest_task_definition_arn=Mock(return_value=""),
        previous_task_definition_arn=Mock(return_value=""),
    ),
)
@patch("actions_helper.main.get_image_uri")
class CmdECSDeployTestCase(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner(env={"AWS_DEFAULT_REGION": TEST_AWS_DEFAULT_REGION})

        self.pulumi_command_args = {
            "--environment": TEST_ENVIRONMENT,
            "--ecr-repository": TEST_APPLICATION_ID,
            "--deployment-tag": "Github-Action",
            "--image-tag": "master-e0428b7",
            "--run-preflight": False,
            "--allow-feature-branch-deployment": True,
        }

    @staticmethod
    def make_args(command_args: dict[str, Any]) -> str:
        return " ".join([f"{key} {value}" for key, value in command_args.items()])

    def test_allow_feature_branch_wrong_environment(self, *args, **kwargs):
        result = self.runner.invoke(
            cmd_ecs_deploy,
            args=f"{self.make_args(self.pulumi_command_args | {"--environment": "live"})}",
        )
        self.assertIsInstance(result.exception, RuntimeError)
        self.assertEqual(result.exit_code, 1)

    def test_cmd_ecs_deploy_without_preflight(self, *args, **kwargs):
        with (
            patch("actions_helper.main.run_preflight_container") as run_preflight_mock,
            patch("actions_helper.main.deregister_task_definition") as deregister_task_definition_mock,
        ):
            result = self.runner.invoke(cmd_ecs_deploy, args=self.make_args(self.pulumi_command_args))

            run_preflight_mock.assert_not_called()
            deregister_task_definition_mock.assert_called()
            self.assertEqual(result.exit_code, 0)

    def test_cmd_ecs_deploy_with_preflight(self, *args, **kwargs):
        with (
            patch("actions_helper.main.run_preflight_container") as run_preflight_mock,
            patch("actions_helper.main.deregister_task_definition") as deregister_task_definition_mock,
        ):
            result = self.runner.invoke(
                cmd_ecs_deploy,
                args=self.make_args(self.pulumi_command_args | {"--run-preflight": True}),
            )
            run_preflight_mock.assert_called()
            deregister_task_definition_mock.assert_called()
            self.assertEqual(result.exit_code, 0)
