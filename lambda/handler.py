"""AWS Lambda handler for the OpenAerialMap stac-fastapi-geoparquet server."""

import logging

import stac_fastapi.geoparquet.api
from mangum import Mangum
from stac_fastapi.geoparquet.settings import Settings

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

settings = Settings(
    stac_fastapi_title="OpenAerialMap STAC API",
    stac_fastapi_description="OpenAerialMap items served from stac-geoparquet",
)
api = stac_fastapi.geoparquet.api.create(settings)
handler = Mangum(api.app, lifespan="on")
