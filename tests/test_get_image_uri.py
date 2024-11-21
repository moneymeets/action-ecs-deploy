import unittest
from unittest.mock import Mock, patch

import boto3

from actions_helper.commands.get_image_uri import get_image_uri


class GetImageUriTestCase(unittest.TestCase):
    @patch.object(boto3, attribute="client")
    def setUp(self, boto3_client):
        self.ecr_client = boto3_client
        self.image_tag = "master-e0428b7"

    def test_get_image_uri(self):
        with (
            patch.object(
                self.ecr_client,
                attribute="describe_images",
                side_effect=Mock(return_value={"imageDetails": [{"imageTags": [self.image_tag]}]}),
            ),
            patch.object(
                self.ecr_client,
                attribute="describe_repositories",
                side_effect=Mock(return_value={"repositories": [{"repositoryUri": "dummy"}]}),
            ),
        ):
            image_uri = get_image_uri(ecr_client=self.ecr_client, ecr_repository=Mock(), tag=Mock())
            self.assertEqual(image_uri, f"dummy:{self.image_tag}")
