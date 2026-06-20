import requests
import json
import logging
from langchain_core.tools import Tool

from imc.modules.utils.crypto import EncryptDecrypt
from imc.config import settings

from langchain_community.utilities.openapi import OpenAPISpec
from imc.modules.llms.llm import get_llm

logger = logging.getLogger(__name__)


def get_decrypted_headers(auth_type: str, encrypted_auth_params: bytes) -> dict:
    """Decrypts stored credentials."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if not encrypted_auth_params or not auth_type:
        return headers
    try:
        secret_key = settings.encrypt_secret_key
        decrypted = EncryptDecrypt.decrypt_secret_key(
            encrypted_auth_params, secret_key=secret_key
        )
        parsed = json.loads(decrypted.replace("'", '"'))
        if auth_type == "bearer_token":
            headers["Authorization"] = f"Bearer {parsed.get('bearer_token')}"
        elif auth_type == "api_key":
            h_name = parsed.get("header_name", "apikey")
            headers[h_name] = parsed.get("api_key")
    except Exception as e:
        logger.error(f"Critical error decrypting credentials: {e}")
    return headers


def _smart_filter_data(data, params):
    """Recursively filters lists based on search parameters."""
    if not params:
        return data
    search_terms = [str(v).lower() for v in params.values() if v]
    if not search_terms:
        return data
    if isinstance(data, list):
        filtered_list = []
        for item in data:
            item_str = json.dumps(item).lower()
            if any(term in item_str for term in search_terms):
                filtered_list.append(item)
        return filtered_list
    elif isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                filtered_v = _smart_filter_data(v, params)
                if filtered_v:
                    new_dict[k] = filtered_v
            else:
                new_dict[k] = v
        return new_dict
    return data


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

            api_failed_search = False
            if method == "GET" and params:
                if isinstance(json_data, dict) and (
                    "error" in str(json_data).lower() or response.status_code == 404
                ):
                    api_failed_search = True
                elif isinstance(json_data, list) and len(json_data) == 0:
                    api_failed_search = True

            if api_failed_search:
                logger.warning(
                    f"Activating Fallback: Downloading full list for local filtering at {path}"
                )

                fb_resp = requests.get(full_url, headers=auth_headers, verify=False)
                full_data = fb_resp.json() if fb_resp.status_code == 200 else []
                json_data = _smart_filter_data(full_data, params)

            if not json_data:
                return f"Status: {response.status_code} Success but without content/results."

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
