import os
import time
import traceback
from logging import DEBUG, Logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from werkzeug.exceptions import HTTPException

from imc.modules.utils import custom_logs

logger = custom_logs.getLogger(__name__, DEBUG)

DEFAULT_ERROR_MESSAGE = "Unknown API error"


# From https://flask.palletsprojects.com/en/1.1.x/patterns/apierrors/#simple-exception-class
class ApiError(HTTPException):
    default_status_code = 500

    def __init__(
        self,
        message=None,
        status_code=None,
        payload=None,
        from_error=None,
        from_error_name="Unknown error origin",
    ):
        # default to 'Unknown API error'
        description = DEFAULT_ERROR_MESSAGE
        # Deduce the description message from the parameters.
        if message is not None:
            # If explicit, always use it.
            description = message
        else:
            # Else try to retrieve it from from_error
            if isinstance(from_error, dict):
                message = from_error.get("message", DEFAULT_ERROR_MESSAGE)
                description = f"{from_error_name}: {message}"

        HTTPException.__init__(self, description)

        if payload is not None:
            self.payload = payload
        elif isinstance(from_error, dict):
            self.payload = from_error.get("error", {}).get("payload", None)

        self.from_error = from_error
        self.from_error_name = from_error_name
        if isinstance(from_error, dict):
            self.prev_tb = from_error.get("error", {}).get("traceback", None)
            self.prev_tb_cause = f"\nThe above exception was generated in the {from_error_name} module and was a direct cause of the following exception:\n\n"
        else:
            self.prev_tb = None

        # Deduce the status code.
        if status_code is not None:
            self.code = status_code
        elif isinstance(from_error, dict):
            self.code = from_error.get("code", self.default_status_code)
        else:
            self.code = self.default_status_code


IMAGE_VARIABLES = {
    "BASE_IMAGE",
    "BASE_IMAGE_TAG",
    "DEVICE",
    "VERSION",
    "COMMIT_ID",
    "BUILD_ID",
    "TAG",
    "BUILD_IMAGE",
    "PRODUCTION_IMAGE",
}


async def version_probe():
    return JSONResponse(
        status_code=200,
        content={
            "version": os.getenv("VERSION", "unknown"),
            "env": os.getenv("BUILD", "unknown"),
            "build_info": {k.lower(): os.getenv(k, "") for k in IMAGE_VARIABLES},
        },
    )


async def health_probe():
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
        },
    )


async def ready_probe():
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
        },
    )


async def exception_probe(message: str = DEFAULT_ERROR_MESSAGE, status_code: int = 500):
    raise ApiError(message=message, status_code=status_code)


async def handle_api_error(request: Request, error: Exception):
    logger = logging.getLogger("vekai")
    logger.exception("API error")

    message = str(error)

    # Format the error response.
    response = {
        "code": getattr(error, "code", 500),
        "message": message,
        "error": {},
    }

    # if the headers contain x-tracebak
    # or the env API_DEBUG is set to true, return the traceback
    if (
        "x-traceback" in request.headers
        or os.getenv("API_RETURN_TRACEBACK", "false").lower() == "true"
    ):
        # Retrieve the traceback if it exists.
        tb = format_traceback_message(error, message)

        if tb:
            response["error"]["traceback"] = tb

    # Retrieve the payload.
    payload = getattr(error, "payload", None)
    if payload is not None:
        response["error"]["payload"] = payload

    # Send the response.
    return JSONResponse(
        status_code=response["code"],
        content=response,
    )


def format_traceback_message(error, message):
    tb = ""

    prev_tb = getattr(error, "prev_tb", None)
    prev_tb_cause = getattr(error, "prev_tb_cause", None)
    if prev_tb is not None:
        tb += f"{prev_tb}"

    curr_tb = getattr(error, "__traceback__", None)
    if curr_tb is not None:
        if prev_tb_cause:
            tb += prev_tb_cause
        tb += f"{message}\n" + "".join(
            traceback.format_exception(type(error), error, curr_tb)
        )

    return tb


async def apply_default_headers(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Add process time header.
    response.headers["X-Process-Time"] = str(process_time)

    # NOTE: Add more headers here if needed.

    # Forward tracing headers.
    for name, value in get_tracing_headers(request).items():
        response.headers[name] = value

    return response


def configure_cors(app):
    # Configurar CORS
    origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

    logger.debug(f"Allowed origins: {origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


def create_app(*args, **kwargs):
    logger.info("Creating FastAPI app")
    app = FastAPI(*args, **kwargs)

    logger.debug("Adding probes to FastAPI app")
    app.get("/version")(version_probe)
    app.get("/health")(health_probe)
    app.get("/ready")(ready_probe)

    logger.debug("Adding exception probe to FastAPI app")
    app.get("/exception")(exception_probe)

    # Add cors middleware
    configure_cors(app)

    # The exception handler manages the exceptions raised by the API in a consistent way.
    # and returns a formatted response.
    # It also logs the error and the traceback.
    logger.debug("Adding exception handler to FastAPI app")
    app.exception_handler(Exception)(handle_api_error)

    logger.debug("Adding default headers middleware to FastAPI app")
    app.middleware("http")(apply_default_headers)

    logger.info("FastAPI app created")

    return app


tracing_headers = [
    # From https://istio.io/docs/tasks/telemetry/distributed-tracing/overview/
    "x-request-id",
    "x-b3-traceid",
    "x-b3-spanid",
    "x-b3-parentspanid",
    "x-b3-sampled",
    "x-b3-flags",
    "x-ot-span-context",
    "x-trace-id",
    "x-correlation-id",
]


def get_tracing_headers(request):
    return {k: v for k, v in request.headers.items() if k.lower() in tracing_headers}
