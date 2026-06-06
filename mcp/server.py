"""
A tiny local MCP server (stdio) exposing a few wildlife tools.

This runs as a subprocess and speaks the Model Context Protocol over stdin/stdout. The example
connects Claude to it via the Anthropic SDK's MCP helpers (see `_mcp_demo.py`). It's deliberately
self-contained — a small in-memory "database", no network.

Run it directly to sanity-check (it will wait for an MCP client on stdio; Ctrl+C to exit):

    .venv\\Scripts\\python.exe mcp/server.py
"""

from mcp.server.fastmcp import FastMCP

server = FastMCP("wildlife-tools")

# A small in-memory knowledge base + sighting tallies.
_SPECIES = {
    "red fox": "Vulpes vulpes — the most widely distributed wild carnivore; an opportunistic "
               "omnivore found from arctic tundra to city centers.",
    "polar bear": "Ursus maritimus — an Arctic bear that hunts seals from the sea ice and is "
                  "highly dependent on it.",
    "gray wolf": "Canis lupus — a social canid that hunts large hoofed mammals in family packs.",
    "barred owl": "Strix varia — a nocturnal woodland owl known for its 'who-cooks-for-you' call.",
    "river otter": "Lontra canadensis — a playful semi-aquatic mustelid of rivers and wetlands.",
}
_SIGHTINGS = {"red fox": 42, "polar bear": 7, "gray wolf": 15, "barred owl": 23, "river otter": 19}


@server.tool()
def list_species() -> list[str]:
    """List the species available in the wildlife database."""
    return sorted(_SPECIES)


@server.tool()
def get_species_info(name: str) -> str:
    """Get a short factual blurb about a species by common name."""
    key = name.strip().lower()
    if key not in _SPECIES:
        return f"Unknown species '{name}'. Known: {', '.join(sorted(_SPECIES))}."
    return _SPECIES[key]


@server.tool()
def count_sightings(species: str) -> int:
    """Return the number of recorded sightings for a species (-1 if unknown)."""
    return _SIGHTINGS.get(species.strip().lower(), -1)


if __name__ == "__main__":
    server.run()  # stdio transport by default
