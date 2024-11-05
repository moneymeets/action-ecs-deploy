import unittest
from unittest.mock import Mock, patch

import boto3

from actions_helper.commands.get_active_task_definition_by_tag import (
    NonSingleValueError,
    Tag,
    format_tags,
    get_active_task_definition_arn_by_tag,
)
from tests.utils import TEST_APPLICATION_ID


class GetTaskDefinitionByTagTestCase(unittest.TestCase):
    @patch.object(boto3, attribute="client")
    def setUp(self, boto3_client):
        self.ecs_client = boto3_client
        self.pulumi_tag = {"key": "created_by", "value": "Pulumi"}

    def test_format_tags(self):
        with self.subTest("Invalid tag format"), self.assertRaises(expected_exception=ValueError):
            format_tags("invalid-tag")
            format_tags("key:value key:value")

        with self.subTest("valid tag format"):
            tags = format_tags("key:value, key2:value2")
            self.assertTupleEqual(tags, (Tag("key", "value"), Tag("key2", "value2")))

    def test_get_active_definition_by_tag(self):
        with (
            self.subTest("Tag does not exist"),
            self.assertRaises(NonSingleValueError),
            patch.object(
                self.ecs_client,
                attribute="list_task_definitions",
                side_effect=Mock(return_value={"taskDefinitionArns": []}),
            ),
        ):
            get_active_task_definition_arn_by_tag(
                ecs_client=self.ecs_client,
                task_definition_family_prefix=TEST_APPLICATION_ID,
                task_definition_tags="created_by:Pulumi",
                allow_initial_deployment=False,
            )

        with (
            self.subTest("More than one task definition with the same tag"),
            patch.object(
                self.ecs_client,
                attribute="list_task_definitions",
                side_effect=Mock(return_value={"taskDefinitionArns": ["dummy", "dummy"]}),
            ),
            patch.object(
                self.ecs_client,
                attribute="describe_task_definition",
                side_effect=Mock(
                    return_value={"taskDefinition": {"taskDefinitionArn": "dummy"}, "tags": [self.pulumi_tag]},
                ),
            ),
            self.assertRaises(NonSingleValueError),
        ):
            get_active_task_definition_arn_by_tag(
                ecs_client=self.ecs_client,
                task_definition_family_prefix=TEST_APPLICATION_ID,
                task_definition_tags=f"{self.pulumi_tag['key']}:{self.pulumi_tag['value']}",
                allow_initial_deployment=False,
            )

        with (
            self.subTest("Tag exists"),
            patch.object(
                self.ecs_client,
                attribute="list_task_definitions",
                side_effect=Mock(return_value={"taskDefinitionArns": ["dummy"]}),
            ),
            patch.object(
                self.ecs_client,
                attribute="describe_task_definition",
                side_effect=Mock(
                    return_value={"taskDefinition": {"taskDefinitionArn": "dummy"}, "tags": [self.pulumi_tag]},
                ),
            ),
        ):
            arn = get_active_task_definition_arn_by_tag(
                ecs_client=self.ecs_client,
                task_definition_family_prefix=TEST_APPLICATION_ID,
                task_definition_tags=f"{self.pulumi_tag['key']}:{self.pulumi_tag['value']}",
                allow_initial_deployment=False,
            )
            self.assertEqual(arn, "dummy")

    def test_initial_deployment(self):
        created_by = "Github Actions Deployment"
        with (
            self.subTest("Initial deployment, no active task definition found"),
            patch.object(
                self.ecs_client,
                attribute="list_task_definitions",
                side_effect=Mock(return_value={"taskDefinitionArns": []}),
            ),
            self.assertRaises(NonSingleValueError),
        ):
            get_active_task_definition_arn_by_tag(
                ecs_client=self.ecs_client,
                task_definition_family_prefix=TEST_APPLICATION_ID,
                task_definition_tags=f"created_by:{created_by}",
                allow_initial_deployment=True,
            )

        with (
            self.subTest("Initial deployment, one active task definition found, but not created by Pulumi"),
            patch.object(
                self.ecs_client,
                attribute="list_task_definitions",
                side_effect=Mock(return_value={"taskDefinitionArns": ["dummy"]}),
            ),
            patch.object(
                self.ecs_client,
                attribute="describe_task_definition",
                side_effect=Mock(
                    return_value={
                        "taskDefinition": {"taskDefinitionArn": ""},
                        "tags": [{"key": "created_by", "value": "dummy"}],
                    },
                ),
            ),
            self.assertRaises(ValueError),
        ):
            get_active_task_definition_arn_by_tag(
                ecs_client=self.ecs_client,
                task_definition_family_prefix="foo",
                task_definition_tags="created_by:dummy",
                allow_initial_deployment=True,
            )

        with (
            self.subTest("Initial deployment, only task definition form Pulumi exists"),
            patch.object(
                self.ecs_client,
                attribute="list_task_definitions",
                side_effect=Mock(return_value={"taskDefinitionArns": ["dummy"]}),
            ),
            patch.object(
                self.ecs_client,
                attribute="describe_task_definition",
                side_effect=Mock(
                    return_value={
                        "taskDefinition": {"taskDefinitionArn": "dummy"},
                        "tags": [self.pulumi_tag],
                    },
                ),
            ),
        ):
            arn = get_active_task_definition_arn_by_tag(
                ecs_client=self.ecs_client,
                task_definition_family_prefix=TEST_APPLICATION_ID,
                task_definition_tags=f"created_by:{created_by}",
                allow_initial_deployment=True,
            )
            self.assertEqual(arn, "")
