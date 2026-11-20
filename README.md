# hot-oam-stac-geoparquet

A minimal [AWS CDK](https://docs.aws.amazon.com/cdk/) stack that serves OpenAerialMap items with [stac-fastapi-geoparquet](https://github.com/stac-utils/stac-fastapi-geoparquet).

The stack creates:

- A public S3 bucket, readable over HTTPS with CORS enabled, to hold `collections.json` and `items-openaerialmap.parquet`
- A container-image Lambda function running **stac-fastapi-geoparquet**, exposed through a public Function URL
  - CORS is handled by **stac-fastapi**'s middleware (any origin, per the STAC API spec), so don't also configure CORS on the Function URL: Lambda would return both sets of headers, and browsers reject a duplicated `Access-Control-Allow-Origin`
- The function reads `https://<bucket>.s3.<region>.amazonaws.com/collections.json`, and queries the parquet file each collection's `data` asset points to

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/), used to build the Lambda image
- A recent AWS CDK CLI (`npx aws-cdk@latest`)
- AWS credentials for the target account, with the account and region [bootstrapped](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)

## Deploy

```shell
uv sync
npx aws-cdk@latest deploy
```

Every resource is tagged with `Project`, `Owner`, `Client`, and `Stack`, following Development Seed's tagging guidelines.
Defaults live in the `context` section of `cdk.json` and can be overridden per deploy, e.g. `npx aws-cdk@latest deploy -c Stack=prod`.

The stack outputs `BucketName`, `CollectionsHref`, `GeoparquetHref`, and `ApiUrl`.
Then upload the parquet file:

```shell
aws s3 cp items-openaerialmap.parquet s3://<BucketName>/items-openaerialmap.parquet
```

## Collections

`collections.json` holds the collection definitions, and each deploy uploads it to the bucket.
Relative asset hrefs (e.g. `./items-openaerialmap.parquet`) are rewritten to absolute bucket URLs on upload, so clients see working links.
The server re-reads the file every 60 seconds, so changes show up without a cold start.

The `openaerialmap` collection is taken from the OAM dump's `collections.ndjson.gz`.
Its extents aren't recomputed from the parquet file, so update them in `collections.json` if the items change.

## Updating stac-fastapi-geoparquet

`lambda/requirements.txt` pins **stac-fastapi-geoparquet** and its runtime dependencies to the versions in that release's `uv.lock`.
The published package only sets lower bounds on dependencies, so an unpinned install pulls in incompatible releases (e.g. **stac-fastapi** 7.x).
When bumping the version, regenerate the pins from the matching upstream `uv.lock`.
