import unittest
from typing import Sequence

import boto3
from click.testing import CliRunner
from moto import mock_aws

from actions_helper.main import NonSingleValueError, Tag, format_tags
from actions_helper.main import cmd_get_active_task_definition_arn_by_tag as command

TEST_AWS_DEFAULT_REGION = "us-east-1"
TEST_APPLICATION_ID = "foo"


@mock_aws
class GetTaskDefinitionByTagTestCase(unittest.TestCase):
    def setUp(self):
        self.client = boto3.Session(region_name=TEST_AWS_DEFAULT_REGION).client("ecs")
        self.runner = CliRunner(
            env={
                "AWS_DEFAULT_REGION": TEST_AWS_DEFAULT_REGION,
            },
        )
        self.pulumi_tag = {"key": "created_by", "value": "Pulumi"}
        self.pulumi_command_arg = f"--application-id {TEST_APPLICATION_ID} --tags created_by:Pulumi"

    def create_task_definition(self, tags: Sequence[dict[str, str]]) -> dict:
        return self.client.register_task_definition(
            family=TEST_APPLICATION_ID,
            containerDefinitions=[],
            tags=tags,
        )

    def test_format_tags(self):
        with self.subTest("Invalid tag format"), self.assertRaises(expected_exception=ValueError):
            format_tags("invalid-tag")
            format_tags("key:value key:value")

        with self.subTest("valid tag format"):
            tags = format_tags("key:value, key2:value2")
            self.assertEqual(len(tags), 2)
            self.assertTupleEqual(tags, (Tag("key", "value"), Tag("key2", "value2")))

    def test_get_active_definition_by_tag(self):
        with self.subTest("Tag does not exist"):
            result = self.runner.invoke(
                command,
                args=self.pulumi_command_arg,
            )
            self.assertEqual(result.exit_code, 1)
            self.assertIsInstance(result.exception, NonSingleValueError)

        with self.subTest("Tag exist"):
            task_definition = self.create_task_definition(tags=[self.pulumi_tag])["taskDefinition"]

            result = self.runner.invoke(
                command,
                args=self.pulumi_command_arg,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.output.strip(), task_definition["taskDefinitionArn"])

        with self.subTest("More than 1 definition with same Tag exist"):
            self.create_task_definition(tags=[self.pulumi_tag])
            result = self.runner.invoke(
                command,
                args=self.pulumi_command_arg,
            )
            self.assertEqual(result.exit_code, 1)
            self.assertIsInstance(result.exception, NonSingleValueError)

    def test_initial_deployment_tag_exist(self):
        with self.subTest("Initial deployment, Pulumi's definition does not exist but Tag exist"):
            created_by = "Github Action Deployment"
            task_definition = self.create_task_definition(tags=[{"key": "created_by", "value": created_by}])[
                "taskDefinition"
            ]
            result = self.runner.invoke(
                command,
                args=f'--application-id foo --tags "created_by:{created_by}" --allow-initial-deployment',
            )
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.output.strip(), task_definition["taskDefinitionArn"])

    def test_initial_deployment_tag_does_not_exist(self):
        created_by = "Github Action Deployment"
        command_args = (
            f"--application-id {TEST_APPLICATION_ID} --tags 'created_by:{created_by}' --allow-initial-deployment"
        )
        with self.subTest("Initial deployment, Tag and Pulumi's definition does not exist"):
            result = self.runner.invoke(
                command,
                args=command_args,
            )
            self.assertEqual(result.exit_code, 1)
            self.assertIsInstance(result.exception, NonSingleValueError)

        with self.subTest("Initial deployment, Tag does not exist but Pulumi's definition exist"):
            self.create_task_definition(tags=[self.pulumi_tag])
            result = self.runner.invoke(
                command,
                args=command_args,
            )
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.output.strip(), "")
