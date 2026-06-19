import requests
import json
import time
from urllib.parse import urlparse, urljoin
import urllib3
from collections import defaultdict
import copy
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from langchain_core.tools import StructuredTool

from imc.modules.agents.tools.openapi_tool_factory import (
    create_openapi_tool,
    get_decrypted_headers,
)

from imc.databases.credentials import get_all_credentials


from pydantic import BaseModel, Field
from typing import List
from imc.api.plugins.services import save_plugin_to_db
import logging


# ADD THE IMPORT OF THE NEW TOOLS:
from imc.modules.agents.tools.sub_agent_factory import (
    create_specialized_agent_tool,
)

# 1. We instantiate the LLM and instructions directly from the backend
from imc.modules.llms.llm import get_llm
from imc.modules.agents.core.react_prompt import SYSTEM_INSTRUCTIONS


from imc.databases.postgres.database import SessionLocal
from imc.api.plugins.models import PluginCreate


# --- IN-MEMORY STATE REGISTRY (Replaces cl.user_session) ---
# In a robust production environment, this state should be managed by the LangGraph checkpointer
# or persisted in the database to survive restarts and handle concurrent requests properly.
_APP_STATE = {
    "fetched_specs": {},
}


# --- 2. CORE TOOLS WITH UNIVERSAL GUARDRAILS ---
def reset_turn_flags():
    """
    Resets single-use locks.
    Must be called mandatorily before processing a new user query.
    """
    global _APP_STATE
    _APP_STATE["has_saved_workflow"] = False
    _APP_STATE["has_consulted_memory"] = False


def _extract_keywords_from_spec(spec_dict: dict) -> str:
    """Extracts KEY entities to tell the Supervisor what is inside."""
    paths_dict = spec_dict.get("paths", {})
    unique_entities = set()

    for p in paths_dict.keys():
        parts = [
            part
            for part in p.split("/")
            if part and "{" not in part and "v1" not in part and "api" not in part
        ]
        unique_entities.update(parts)

    sorted_entities = sorted(list(unique_entities))
    return ", ".join(sorted_entities[:10])


def _get_relational_type(schema: dict) -> str:
    """
    Extracts the data type and keeps references (@Ref) explicit
    so the Supervisor Agent understands the relationships between classes.
    """
    if "$ref" in schema:
        return f"@{schema['$ref'].split('/')[-1]}"

    stype = schema.get("type", "any")

    # Handling lists that contain relationships (e.g., List of Suppliers)
    if stype == "array":
        items = schema.get("items", {})
        if "$ref" in items:
            return f"List[@{items['$ref'].split('/')[-1]}]"
        return f"List[{items.get('type', 'any')}]"

    return stype


def _extract_schemas_map(spec_dict: dict) -> str:
    """
    Extracts a detailed map of DATA MODELS with their TYPES and RELATIONSHIPS.
    Example output:
    Model 'Order': { 'id'*: string, 'status': string, 'supplier': @Supplier }
    """
    schemas = spec_dict.get("components", {}).get("schemas", {}) or spec_dict.get(
        "definitions", {}
    )
    schema_map = []

    for name, details in schemas.items():
        properties = details.get("properties", {})
        if not properties:
            continue

        props_list = []
        for key, val in properties.items():
            # WE USE THE NEW RELATIONAL EXTRACTOR HERE
            type_str = _get_relational_type(val)

            required = details.get("required", [])
            req_mark = "*" if key in required else ""
            props_list.append(f"'{key}'{req_mark}: {type_str}")

        formatted_props = ", ".join(props_list)
        schema_map.append(f"Model '{name}': {{ {formatted_props} }}")

    return "\n".join(schema_map) if schema_map else "No Data Schemas found."


def _simplify_schema(schema: dict, definitions: dict = None, depth=0) -> str:
    """
    Converts a complex OpenAPI Schema into a simple Python/JSON string representation.
    NOW RESOLVES REFERENCES SO THE LLM SEES THE REAL FIELDS (ID, NAME, ETC).
    """

    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        if definitions and ref_name in definitions:
            return _simplify_schema(definitions[ref_name], definitions, depth + 1)
        return f"@{ref_name}"

    stype = schema.get("type")

    if stype == "array":
        items = schema.get("items", {})
        inner = _simplify_schema(items, definitions, depth + 1)
        return f"List[{inner}]"

    elif stype == "object" or "properties" in schema:
        props = schema.get("properties", {})
        out = {}
        for k, v in props.items():
            out[k] = _simplify_schema(v, definitions, depth + 1)
        return str(out).replace("'", '"')

    return stype or "any"


def _build_api_cheat_sheet(spec_dict: dict) -> str:
    """
    Generates a strict guide of ENDPOINTS -> METHOD -> PARAMETERS -> RESPONSE -> BODY.
    """
    cheat_sheet = []
    definitions = spec_dict.get("components", {}).get("schemas", {}) or spec_dict.get(
        "definitions", {}
    )

    paths = spec_dict.get("paths", {})

    for path, methods in paths.items():
        for method, meta in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue

            method_str = method.upper()

            # 1. Recover both summary and description
            raw_summary = meta.get("summary", "")
            raw_description = meta.get("description", "")

            # 2. Prioritize description if exists
            info_text = raw_description if raw_description else raw_summary
            info_text = info_text.replace("\n", " ")[:200]

            params = meta.get("parameters", [])
            query_params = []
            path_params = []

            for p in params:
                if "$ref" in p:
                    continue

                name = p.get("name")
                in_loc = p.get("in")
                schema = p.get("schema", p)
                p_type = _simplify_schema(schema)

                req = "*" if p.get("required") else ""

                if in_loc == "query":
                    query_params.append(f"{name}{req}={p_type}")
                elif in_loc == "path":
                    path_params.append(f"{name}")

            # --- CORRECTION: CALCULATE BODY ---
            body_hint = ""
            if "requestBody" in meta:
                content = meta["requestBody"].get("content", {})
                json_content = content.get("application/json", {})

                if json_content:
                    schema = json_content.get("schema", {})
                    example = json_content.get("example")
                    if example:
                        body_hint = f"BODY_EXAMPLE: {json.dumps(example)[:300]}"
                    else:
                        structure = _simplify_schema(schema, definitions)
                        body_hint = f"BODY_SCHEMA: {structure}"

            returns_str = ""
            responses = meta.get("responses", {})
            success_resp = (
                responses.get("200", {})
                or responses.get("2xx", {})
                or responses.get(200, {})
            )
            if success_resp:
                content = success_resp.get("content", {}).get("application/json", {})
                if content and "schema" in content:
                    returns_str = f" ➡️ RETURNS: {_simplify_schema(content['schema'], definitions)}"
                elif "schema" in success_resp:
                    returns_str = f" ➡️ RETURNS: {_simplify_schema(success_resp['schema'], definitions)}"

            is_list = method_str == "GET" and "{" not in path
            tag = " [GENERAL LISTING / SEARCH]" if is_list else ""

            # --- CORRECTION: ASSEMBLE COMPLETE LINE ---
            line = f"{method_str} {path}{tag}"

            # HERE WAS THE BUG! Now we inject body_hint
            if body_hint:
                line += f" REQUIRES PAYLOAD: {body_hint}"

            if returns_str:
                line += returns_str
            if info_text:
                line += f"  (Info: {info_text})"

            # Add only once
            cheat_sheet.append(line)

    return "\n".join(cheat_sheet)


def _detect_gateway_pattern(spec_dict: dict) -> str:
    """
    Analyzes routes to detect if it is a Gateway (Strict Criteria).
    """
    paths = spec_dict.get("paths", {}).keys()
    if not paths:
        return ""

    # 1. Grouping by prefixes
    groups = defaultdict(int)
    for p in paths:
        parts = p.strip("/").split("/")
        if parts:
            root = "/" + parts[0]
            groups[root] += 1

    if len(groups) < 2:
        return ""

    # 2. Security Criteria
    components = spec_dict.get("components", {})
    security_schemes = components.get("securitySchemes", {}) or spec_dict.get(
        "securityDefinitions", {}
    )
    global_security = spec_dict.get("security", [])

    has_path_security = False
    for path_data in spec_dict.get("paths", {}).values():
        for method_data in path_data.values():
            if isinstance(method_data, dict) and "security" in method_data:
                has_path_security = True
                break
        if has_path_security:
            break

    is_secure_gateway = bool(security_schemes or global_security or has_path_security)

    if is_secure_gateway:
        report = []
        for root, count in groups.items():
            report.append(f"   - `{root}` ({count} endpoints)")

        return (
            "\nGATEWAY ALERT: I have detected multiple root prefixes WITH security (Auth).\n"
            "Meets the criteria for Secure Gateway.\n"
            "RECOMMENDATION: Register a separate agent for each of these prefixes:\n"
            + "\n".join(report)
        )

    return ""


def _filter_spec_by_path(spec: dict, path_filter: str) -> dict:
    """
    Filters a large Swagger to leave only the routes of a sub-service.
    IMPORTANT: Maintains the original 'components'/'definitions' to not lose Schemas.
    """
    if not path_filter:
        return spec

    new_spec = copy.deepcopy(spec)

    new_paths = {p: d for p, d in spec.get("paths", {}).items() if path_filter in p}
    new_spec["paths"] = new_paths

    info = spec.get("info", {})
    new_spec["info"] = {
        "title": f"{info.get('title')} (Sub: {path_filter})",
        "version": info.get("version"),
    }
    return new_spec


def _determine_real_base_url(original_url: str, spec_dict: dict) -> str:
    """
    Calculates the correct base URL for requests, prioritizing the Gateway.
    1. Prioritizes cleaning the original URL, assuming it was accessed via Kong.
    2. Only as a fallback, uses the URL defined in the 'servers' block of the OpenAPI.
    """
    clean_url = original_url.strip().rstrip("/")
    bad_suffixes = [
        "/openapi.json",
        "/swagger.json",
        "/openapi.yaml",
        "/swagger.yaml",
        "/api/docs/blueprint-query-api.yaml",
        "/api/docs/blueprint-generic-api.yaml",
        "/api/docs",
        "/docs",
        "/v1/openapi.json",
        "/v3/api-docs",
    ]

    # 1. PRIORITY: Origin URL (Gateway Kong)
    for suffix in bad_suffixes:
        if clean_url.endswith(suffix):
            clean_url = clean_url[: -len(suffix)]
            # If we managed to clean it, we know it comes from the Gateway. We use it and return immediately.
            return clean_url.rstrip("/")

    # 2. FALLBACK: 'servers' from OpenAPI (Only if the URL did not have the previous suffixes)
    servers = spec_dict.get("servers", [])
    if servers and isinstance(servers, list) and "url" in servers[0]:
        server_url = servers[0]["url"]

        if server_url.startswith("http"):
            return server_url.rstrip("/")

        if server_url.startswith("/"):
            parsed = urlparse(original_url)
            host = f"{parsed.scheme}://{parsed.netloc}"
            return f"{host}{server_url}".rstrip("/")

    # If it does not have known suffixes and no servers block, we return the original URL
    return clean_url.rstrip("/")


# --- CORE FUNCTIONS ---


def _get_auth_headers(identifier: str) -> dict:
    """
    Searches SQLite to see if the service name or URL contains
    a saved keyword (risk, blueprint, gmao, narrate)
    and constructs the authorization header.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if not identifier:
        return headers

    try:
        creds = (
            get_all_credentials()
        )  # Returns dict: {'risk': {'value': 'user-a-key', 'header': 'apikey'}, ...}

        # We look for whether the key (e.g., 'risk') is within the identifier (e.g., 'api-risk' or 'tool_risk')
        for service_name, data in creds.items():
            if service_name.lower() in identifier.lower():
                header_name = data.get("header", "apikey")
                header_value = data.get("value")
                headers[header_name] = header_value
                break  # We found the credential, we break the loop
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            f"Could not load credentials for {identifier}: {e}"
        )

    return headers


def _internal_download_spec(base_url: str, identifier: str = ""):
    """Robust download with Auth and YAML support."""
    candidates = [
        base_url,
        f"{base_url}/openapi.yaml",
        f"{base_url}/swagger.yaml",
        f"{base_url}/openapi.json",
        f"{base_url}/swagger.json",
        f"{base_url}/docs/openapi.json",
        f"{base_url}/v1/openapi.json",
        f"{base_url}/v3/api-docs",
    ]

    headers = _get_auth_headers(identifier or base_url)
    for target in candidates:
        try:
            resp = requests.get(target, headers=headers, timeout=5, verify=False)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and (
                        "openapi" in data or "swagger" in data
                    ):
                        return data, target
                except:
                    try:
                        # Attempt 2: As YAML (NEW)
                        data = yaml.safe_load(resp.text)
                        if isinstance(data, dict) and (
                            "openapi" in data or "swagger" in data
                        ):
                            return data, target
                    except Exception as e:
                        pass
            elif resp.status_code in [401, 403]:
                if "openapi.json" in target or "swagger.json" in target:
                    raise PermissionError(f"Auth required for {base_url}")
        except PermissionError as pe:
            raise pe
        except Exception:
            continue
    return None, None


logger = logging.getLogger(__name__)


def fetch_api_structure(url: str) -> str:
    """
    Public tool. Analyzes the URL and SUGGESTS division if it detects a Gateway.
    """
    global _APP_STATE
    clean_url = url.strip().strip("'").strip('"')

    logger.info(f"Scanning API structure at: {clean_url}...")

    try:
        spec, final_url = _internal_download_spec(clean_url, clean_url)
    except PermissionError:
        return f"ACCESS DENIED (401/403): Requires authentication. Use `save_api_key` first."

    if spec:
        # Save spec
        _APP_STATE["fetched_specs"][clean_url] = spec

        preview = _extract_keywords_from_spec(spec)
        title = spec.get("info", {}).get("title", "API")

        # --- GATEWAY ANALYSIS ---
        gateway_analysis = _detect_gateway_pattern(spec)

        if not gateway_analysis:
            gateway_analysis = "API Detected: No Gateway criteria detected (Multiple Auth or sub-swaggers). A single agent is recommended."

        return (
            f"Structure Found at `{final_url}` ({title}).\n"
            f"General Content: {preview}\n"
            f"{gateway_analysis}\n\n"
            f"ACTION: If you see the Gateway Alert above, use `register_dynamic_api` multiple times. If you do NOT see an alert, use `register_dynamic_api` once with path_filter='/'."
        )

    return f"No valid OpenAPI JSON found at {clean_url}."


def register_dynamic_api(json_input: str) -> str:
    """
    Registers an agent with smart Fallback logic for Gateways.
    INPUT: JSON with keys: "service_name" (MANDATORY), "path_filter", "base_url".
    """
    global _APP_STATE
    try:
        if isinstance(json_input, dict):
            data = json_input
        else:
            clean_str = json_input.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_str)

        base_url = data.get("base_url", "").strip().rstrip("/")
        path_filter = data.get("path_filter", "")

        raw_name = data.get("service_name") or data.get("tool_name")

        if not raw_name and path_filter:
            raw_name = path_filter.replace("/", "").strip()

        if not raw_name:
            raw_name = f"tool_{int(time.time())}"

        tool_name = (
            raw_name.lower()
            .strip()
            .replace("/", "")
            .replace(" ", "_")
            .replace("-", "_")
        )

        saved_specs = _APP_STATE["fetched_specs"]
        root_spec = None
        for u, s in saved_specs.items():
            if base_url in u or u in base_url:
                root_spec = s
                break

        if not root_spec:
            return f"Error: Execute `fetch_api_structure` first for {base_url}."

        final_spec = None

        logger = logging.getLogger(__name__)

        if path_filter:
            sub_service_url = f"{base_url}{path_filter}"
            try:
                logger.info(f"Registering: '{tool_name}' (Path: {path_filter})")

                fetched_sub, _ = _internal_download_spec(sub_service_url, tool_name)
                has_schemas = bool(
                    fetched_sub
                    and (
                        fetched_sub.get("components", {}).get("schemas")
                        or fetched_sub.get("definitions")
                    )
                )

                if fetched_sub and has_schemas:
                    final_spec = fetched_sub
                    base_url = sub_service_url
                    logger.info(
                        f"Deep Discovery: Complete Swagger found for {tool_name}."
                    )
                elif fetched_sub:
                    logger.warning(
                        f"Deep Discovery Ignored: Empty Swagger for {tool_name}. Using filtered Root Spec."
                    )

            except PermissionError:
                return f"AUTH REQUIRED: The service `{tool_name}` requests a key. Use `save_api_key` and retry."

        if not final_spec:
            final_spec = (
                _filter_spec_by_path(root_spec, path_filter)
                if path_filter
                else root_spec
            )

        if not final_spec.get("paths"):
            return f"Error: Empty spec for '{tool_name}' after filtering."

        keywords = _extract_keywords_from_spec(final_spec)
        schema_map = _extract_schemas_map(final_spec)
        cheat_sheet = _build_api_cheat_sheet(final_spec)

        rich_internal_doc = (
            f"--- API KNOWLEDGE FOR {tool_name.upper()} ---\n"
            f"1. Main Resources: {keywords}\n\n"
            f"2. DATA MODELS (Schemas):\n{schema_map}\n\n"
            f"3. USAGE EXAMPLES (Cheat Sheet):\n"
            f"STRICT SEARCH AND FILTERING RULES:\n"
            f"   A) ID SEARCH (HIGH PRIORITY): If the Orchestrator already provides you with the exact ID (e.g., 'MS_002', 'PROD_001'), "
            f"ALWAYS use the specific endpoint (e.g., GET /resource/{{id}}). Do not use filtering parameters if you already possess the ID.\n"
            f"   B) MAGIC FILTERING TRICK (WITHOUT ID): If the Orchestrator asks you to search by a Name or other textual attribute, "
            f"search in the endpoint marked with [GENERAL LISTING / SEARCH]. You have ABSOLUTE PERMISSION to send it a filter "
            f'in the `params` field (e.g., `params: {{"name": "Bespoke Baby Cot"}}`). Even if the endpoint does not officially accept parameters '
            f"in the Swagger, the system will download the complete list and locally filter the exact object for you. "
            f"NEVER respond that you cannot search by name, always use this technique!\n\n"
            f"{cheat_sheet}\n"
        )

        # --- NEW: Detect if the sub-agent can actually list ---
        has_list_endpoint = False
        for p, methods in final_spec.get("paths", {}).items():
            if "get" in [m.lower() for m in methods.keys()] and "{" not in p:
                has_list_endpoint = True
                break

        if has_list_endpoint:
            usage_rules = f"1. GENERAL QUERIES: Use it to 'list all {keywords.split(',')[0]}', view summaries, or search without an ID.\n"
        else:
            usage_rules = f"1. STRICTLY BY ID: This agent DOES NOT HAVE ENDPOINTS to search by name or list. REQUIRES OBTAINING THE ID PREVIOUSLY from another inventory agent or database. NEVER ask it to list.\n"
        # ----------------------------------------------------------------

        supervisor_description = (
            f"OFFICIAL agent for the service '{tool_name}'.\n"
            f"CONTAINS DATA ABOUT: [{keywords}].\n"
            f"RELATIONAL STRUCTURE (DATA MODELS):\n"
            f"Use this to know how entities are associated (e.g., what IDs an object contains):\n"
            f"{schema_map}\n\n"
            f"USAGE MANUAL:\n"
            f"{usage_rules}"
            f"2. SPECIFIC QUERIES: If you have an ID, pass it to see details.\n"
            f"3. FILTERS: If you search by name/tag, tell it.\n"
            f"Do not ask the user for new URLs if the question is about these topics. USE THIS AGENT."
        )

        final_base_url = _determine_real_base_url(base_url, final_spec)

        # --- NEW: EXTRACT BASIC METADATA FOR THE DATABASE ---
        # 1. Obtain a brief user-oriented description from the spec
        info_block = final_spec.get("info", {})
        api_title = info_block.get("title", tool_name)
        raw_desc = info_block.get("description", f"API Client for {api_title}.")
        basic_description = (
            (raw_desc[:250] + "...") if len(raw_desc) > 250 else raw_desc
        )

        # 2. Capture the exact OpenAPI (Swagger) URL
        exact_openapi_url = None
        if path_filter and "fetched_sub" in locals() and fetched_sub:
            # If we used a sub-path, we try to derive its URL
            _, exact_openapi_url = _internal_download_spec(sub_service_url, tool_name)

        if not exact_openapi_url:
            # We re-evaluate with the final base_url
            _, exact_openapi_url = _internal_download_spec(final_base_url, tool_name)

        if not exact_openapi_url:
            exact_openapi_url = f"{final_base_url}/openapi.json"  # Fallback
        # --------------------------------------------------------------

        llm = get_llm()

        # We use empty or DB-injected auth_headers
        auth_headers = _get_auth_headers(tool_name)

        raw_api_tool = create_openapi_tool(
            name=f"http_client_{tool_name}",
            base_url=final_base_url,
            openapi_spec=final_spec,
            system_description=f"HTTP Client for {tool_name}.",
            auth_headers=auth_headers,
        )

        agent_tool = create_specialized_agent_tool(
            llm=llm,
            api_tool=raw_api_tool,
            name=tool_name,
            title=f"{tool_name.upper()}",
            internal_doc=rich_internal_doc,
            description=supervisor_description,
        )

        # 2. Replaced cl.user_session with _APP_STATE
        curr = _APP_STATE.get("dynamic_tools", [])
        upd = [t for t in curr if t.name != agent_tool.name] + [agent_tool]

        _APP_STATE["dynamic_tools"] = upd

        base_tools = get_initial_tools()
        all_tools = base_tools + upd
        from imc.modules.agents.core.agent import initialize_agent

        # 3. We initialize the new graph with the updated tools
        new_agent_graph, _ = initialize_agent(
            llm, tools_override=all_tools, system_instructions=SYSTEM_INSTRUCTIONS
        )

        _APP_STATE["executor"] = new_agent_graph

        # Saved to database
        db_session = SessionLocal()
        try:
            # 1. Create the Pydantic object with clean fields
            plugin_data = PluginCreate(
                name=tool_name,
                base_url=final_base_url,
                openapi_url=exact_openapi_url,  # We save the exact path of the spec
                description=basic_description,  # We save the friendly description
            )

            # 2. Call the service passing the session and the object
            success = save_plugin_to_db(db=db_session, plugin_data=plugin_data)
            if success:
                logger.info(f"Agent '{tool_name}' saved to the IMC Database.")
            else:
                logger.warning(
                    f"The agent '{tool_name}' could not be saved (possibly it already exists)."
                )

        except Exception as e:
            logger.error(f"Error saving agent to DB: {e}")
            db_session.rollback()
        finally:
            db_session.close()

        schema_status = (
            f"Schemas: {len(schema_map.splitlines())}"
            if schema_map != "No Data Schemas found."
            else "No Schemas"
        )

        return (
            f"Agent '{tool_name}' successfully registered and saved to the Database.\n"
            f"   - {schema_status}\n"
            f"   - Examples: {len(cheat_sheet.splitlines())}"
        )

    except Exception as e:
        return f"Error: {str(e)}"


def load_plugins_from_db():
    """
    Runs at system startup to recover plugins saved in PostgreSQL,
    download their Swaggers, and re-register them as LangGraph tools.
    """
    global _APP_STATE

    # If we have already loaded them, we do not do it again
    if _APP_STATE.get("plugins_loaded"):
        return _APP_STATE.get("dynamic_tools", [])

    from imc.databases.postgres.database import SessionLocal
    from imc.api.plugins.services import get_plugin_catalog
    from imc.modules.llms.llm import get_llm
    import logging

    logger = logging.getLogger(__name__)
    db_session = SessionLocal()

    try:
        saved_plugins = get_plugin_catalog(db_session)
        llm = get_llm()
        loaded_tools = []

        for plugin in saved_plugins:
            tool_name = plugin["name"]
            base_url = plugin["base_url"]
            openapi_url = plugin.get("openapi_url")  # We get the Swagger URL

            # We prioritize openapi_url to download the spec. If it does not exist (old plugins), we use base_url
            target_url = openapi_url if openapi_url else base_url

            logger.info(
                f"Rehydrating plugin from DB: {tool_name} (API: {base_url} | Spec: {target_url})"
            )

            # 1. We download the spec again using the priority exact URL
            spec, _ = _internal_download_spec(target_url, tool_name)

            if not spec:
                logger.warning(
                    f"Could not download Swagger for {tool_name}. Skipping..."
                )
                continue

            # 2. We rebuild internal documents
            keywords = _extract_keywords_from_spec(spec)
            schema_map = _extract_schemas_map(spec)
            cheat_sheet = _build_api_cheat_sheet(spec)

            # --- Rebuild Supervisor Description with Schemas ---
            has_list_endpoint = False
            for p, methods in spec.get("paths", {}).items():
                if "get" in [m.lower() for m in methods.keys()] and "{" not in p:
                    has_list_endpoint = True
                    break

            if has_list_endpoint:
                usage_rules = f"1. GENERAL QUERIES: Use it to 'list all {keywords.split(',')[0]}', view summaries, or search without an ID.\n"
            else:
                usage_rules = f"1. STRICTLY BY ID: This agent DOES NOT HAVE ENDPOINTS to search by name or list. REQUIRES OBTAINING THE ID PREVIOUSLY from another inventory agent or database. NEVER ask it to list.\n"

            supervisor_description = (
                f"OFFICIAL agent for the service '{tool_name}'.\n"
                f"CONTAINS DATA ABOUT: [{keywords}].\n"
                f"RELATIONAL STRUCTURE (DATA MODELS):\n"
                f"Use this to know how entities are associated (e.g., what IDs an object contains):\n"
                f"{schema_map}\n\n"
                f"USAGE MANUAL:\n"
                f"{usage_rules}"
                f"2. SPECIFIC QUERIES: If you have an ID, pass it to see details.\n"
                f"3. FILTERS: If you search by name/tag, tell it.\n"
                f"Do not ask the user for new URLs if the question is about these topics. USE THIS AGENT."
            )
            # --------------------------------------------------------

            rich_internal_doc = (
                f"--- API KNOWLEDGE FOR {tool_name.upper()} ---\n"
                f"1. Main Resources: {keywords}\n\n"
                f"2. DATA MODELS (Schemas):\n{schema_map}\n\n"
                f"3. USAGE EXAMPLES (Cheat Sheet):\n"
                f"STRICT SEARCH AND FILTERING RULES:\n"
                f"   A) ID SEARCH (HIGH PRIORITY): If the Orchestrator already provides you with the exact ID (e.g., 'MS_002', 'PROD_001'), "
                f"ALWAYS use the specific endpoint (e.g., GET /resource/{{id}}). Do not use filtering parameters if you already possess the ID.\n"
                f"   B) MAGIC FILTERING TRICK (WITHOUT ID): If the Orchestrator asks you to search by a Name or other textual attribute, "
                f"search in the endpoint marked with [GENERAL LISTING / SEARCH]. You have ABSOLUTE PERMISSION to send it a filter "
                f'in the `params` field (e.g., `params: {{"name": "Bespoke Baby Cot"}}`). Even if the endpoint does not officially accept parameters '
                f"in the Swagger, the system will download the complete list and locally filter the exact object for you. "
                f"NEVER respond that you cannot search by name, always use this technique!\n\n"
                f"{cheat_sheet}\n"
            )
            auth_headers = _get_auth_headers(tool_name)

            # 3. We recreate the HTTP tool and the Agent
            raw_api_tool = create_openapi_tool(
                name=f"http_client_{tool_name}",
                base_url=base_url,
                openapi_spec=spec,
                system_description=f"HTTP Client for {tool_name}.",
                auth_headers=auth_headers,
            )

            agent_tool = create_specialized_agent_tool(
                llm=llm,
                api_tool=raw_api_tool,
                name=tool_name,
                title=f"{tool_name.upper()}",
                internal_doc=rich_internal_doc,
                description=supervisor_description,
            )

            loaded_tools.append(agent_tool)
            logger.info(f"Plugin {tool_name} successfully loaded into memory.")

        # Save to global state
        _APP_STATE["dynamic_tools"] = loaded_tools
        _APP_STATE["plugins_loaded"] = True
        return loaded_tools

    except Exception as e:
        logger.error(f"Critical error loading plugins from DB: {e}")
        return []
    finally:
        db_session.close()


def get_initial_tools():
    static_tools = [
        StructuredTool.from_function(fetch_api_structure),
        StructuredTool.from_function(register_dynamic_api),
    ]
    # 2. Recover dynamic ones from DB (will only consult Postgres the first time)
    dynamic_tools = load_plugins_from_db()

    # 3. Return the complete arsenal
    return static_tools + dynamic_tools
