from imc.api.plugins.models import PluginInfo

# TODO: plugin host as env vars
mock_plugin = PluginInfo(
    id=1,
    url="http://host.docker.internal:8012",
    title="Blueprint API",
    description="Provides data related to the blueprint graph DB. Contains the database models an end-to-end manufacturing and supply chain knowledge graph for production, orderes by a retailer, manufacture by a lead producer, and tracking through all production stages — from raw materials and components to final assembly and quality control. ",
    schema_url="http://host.docker.internal:8012/schema",
    prompt="Use the provided API to get data from the graph data base to responde the user's question. User's question:{question}",
    verify_ssl=True
)