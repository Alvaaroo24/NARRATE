import requests
import json
import logging
from langchain_core.tools import Tool

from imc.modules.utils.crypto import EncryptDecrypt
from imc.config import settings

from langchain_community.utilities.openapi import OpenAPISpec
from imc.modules.llms.llm import get_llm

logger = logging.getLogger(__name__)


def create_openapi_tool(
    *,
    name: str,
    base_url: str,
    openapi_spec: dict,
    system_description: str,
    auth_headers: dict = None,
) -> Tool:

    if auth_headers is None:
        auth_headers = {"Content-Type": "application/json"}

    def executor(payload_str: str) -> str:
        try:
            cleaned_input = payload_str.strip()
            if cleaned_input.startswith("```"):
                cleaned_input = cleaned_input.replace("```json", "").replace("```", "")
            payload = json.loads(cleaned_input)
            if isinstance(payload, str):
                payload = json.loads(payload)
        except json.JSONDecodeError:
            return f"Error: Input is not valid JSON. Received: {payload_str}"

        path = payload.get("path") or payload.get("url") or payload.get("endpoint", "")
        body = payload.get("body") or payload.get("data")
        payload_method = payload.get("method")
        method = (
            payload_method.upper() if payload_method else ("POST" if body else "GET")
        )
        params = payload.get("params") or payload.get("query")

        if not path:
            return "Error: Missing 'path' (or 'url') in the input JSON."

        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

        logger.info(f"Executing Deterministic Request: {method} {full_url}")

        try:
            response = requests.request(
                method=method,
                url=full_url,
                headers=auth_headers,
                params=params,
                json=body if isinstance(body, (dict, list)) else None,
                verify=False,
            )

            try:
                json_data = response.json()
            except ValueError:
                json_data = {
                    "raw_text": response.text,
                    "status_code": response.status_code,
                }

            if response.status_code >= 400:
                return f"Error: API returned status {response.status_code}. Details: {json_data}"

            text_out = json.dumps(json_data, separators=(",", ":"))
            MAX_CHARS = 15000
            if len(text_out) > MAX_CHARS:
                return f"{text_out[:MAX_CHARS]}\n\n... [TRUNCATED RESPONSE] ...\nConsider using more specific query parameters."

            return text_out

        except Exception as e:
            return f"Critical error executing HTTP Request: {str(e)}"

    endpoints_docs = []
    paths = openapi_spec.get("paths", openapi_spec)
    if isinstance(paths, dict):
        for path, methods in paths.items():
            if isinstance(methods, dict):
                for m, meta in methods.items():
                    if not isinstance(meta, dict):
                        continue
                    summary = meta.get("summary", "No description")
                    required_params = [
                        p.get("name")
                        for p in meta.get("parameters", [])
                        if p.get("required")
                    ]
                    req_text = (
                        f" (Req: {', '.join(required_params)})"
                        if required_params
                        else ""
                    )
                    endpoints_docs.append(f"{m.upper()} {path} {req_text} -> {summary}")

    description = (
        f"{system_description}\n"
        "QUICK START GUIDE:\n"
        "1. This tool has 'Smart Fallback': If the API fails to search, I will download everything and filter for you.\n"
        "2. You ALWAYS send specific params (e.g., query='Love'). I will handle the rest.\n"
        "3. Authentication is handled automatically if keys are saved.\n"
        "---------------------------------------------------------------\n"
        + "\n".join(endpoints_docs)
    )

    return Tool(name=name, func=executor, description=description)
