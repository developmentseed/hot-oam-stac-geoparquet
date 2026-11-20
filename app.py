"""AWS CDK app that serves OpenAerialMap items via stac-fastapi-geoparquet.

The stack creates a public bucket and a Lambda function (exposed with a
Function URL). `collections.json` is deployed to the bucket, with relative
asset hrefs resolved against the bucket's URL, and the server reads it over
HTTPS. Its parquet asset, `items-openaerialmap.parquet`, must be uploaded to
the bucket manually.
"""

import json
from pathlib import Path
from typing import Any

from aws_cdk import App, CfnOutput, Duration, RemovalPolicy, Stack, Tags
from aws_cdk.aws_ecr_assets import Platform
from aws_cdk.aws_lambda import (
    Architecture,
    DockerImageCode,
    DockerImageFunction,
    FunctionUrlAuthType,
)
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_s3 import BlockPublicAccess, Bucket, CorsRule, HttpMethods
from aws_cdk.aws_s3_deployment import BucketDeployment, Source
from constructs import Construct

COLLECTIONS_KEY = "collections.json"
GEOPARQUET_KEY = "items-openaerialmap.parquet"


def load_collections(path: str, base_url: str) -> list[dict[str, Any]]:
    """Loads a JSON list of collections, making relative asset hrefs absolute.

    Relative hrefs are resolved against `base_url`, which may be a CDK token.
    """
    collections: list[dict[str, Any]] = json.loads(Path(path).read_text())
    for collection in collections:
        for asset in collection.get("assets", {}).values():
            href = asset["href"]
            if "://" not in href:
                asset["href"] = f"{base_url}/{href.removeprefix('./')}"
    return collections


class HotOamStacGeoparquetStack(Stack):
    """A public bucket plus a stac-fastapi-geoparquet Lambda reading from it."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = Bucket(
            self,
            "Bucket",
            public_read_access=True,
            block_public_access=BlockPublicAccess(
                block_public_acls=True,
                ignore_public_acls=True,
                block_public_policy=False,
                restrict_public_buckets=False,
            ),
            cors=[
                CorsRule(
                    allowed_methods=[HttpMethods.GET, HttpMethods.HEAD],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag", "Content-Length", "Content-Range"],
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )
        bucket_url = f"https://{bucket.bucket_regional_domain_name}"
        bucket_deployment = BucketDeployment(
            self,
            "BucketDeployment",
            sources=[
                Source.json_data(
                    COLLECTIONS_KEY, load_collections(COLLECTIONS_KEY, bucket_url)
                )
            ],
            destination_bucket=bucket,
            prune=False,
        )
        collections_href = f"{bucket_url}/{COLLECTIONS_KEY}"
        geoparquet_href = f"{bucket_url}/{GEOPARQUET_KEY}"

        function = DockerImageFunction(
            self,
            "Function",
            code=DockerImageCode.from_image_asset(
                "lambda", platform=Platform.LINUX_AMD64
            ),
            architecture=Architecture.X86_64,
            memory_size=3008,
            timeout=Duration.seconds(30),
            log_group=LogGroup(
                self,
                "FunctionLogGroup",
                retention=RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            ),
            environment={
                "STAC_FASTAPI_COLLECTIONS_HREF": collections_href,
                "HOME": "/tmp",
            },
        )
        function.node.add_dependency(bucket_deployment)
        function_url = function.add_function_url(auth_type=FunctionUrlAuthType.NONE)

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "CollectionsHref", value=collections_href)
        CfnOutput(self, "GeoparquetHref", value=geoparquet_href)
        CfnOutput(self, "ApiUrl", value=function_url.url)


app = App()
stack = HotOamStacGeoparquetStack(app, "hot-oam-stac-geoparquet")
for key in ["Project", "Owner", "Client", "Stack"]:
    Tags.of(stack).add(key, app.node.get_context(key), apply_to_launched_instances=True)
app.synth()
