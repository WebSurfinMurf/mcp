I have tried to deploy litellm with mcp gateway and failed multiple times. 
This time i want to simplify the deploy by sticking to LAN access on server linuxserver.lan. 
PLEASE do some deep digging on best practices to register an MCP server to litellm for stdio, http, and sse. I want to avoide altering litellm and downloaded mcp's, but if its more straight forward to do so, that is OK. 
PLEASE summarize why and ASK me first. I am very fine with each mcp runs in a docker container, i dont view that as modifying, but as a wrapper. P
lease keep this in mind when reading below. ALSO please target litellm v1.77.3-stable

litellm should be deployed at:
projects/litellm

the mcp's should be at:
projects/mcp/{services}
example:
projects/mcp/postgres

For any MCP, propritize mcp tools that have material community support and adoption, if there is more than one with similiar adoption, choose the one aligned with the core project if one exists.
I want all of them deployed locally in respective directories.

I want to register them to a central mcp server to make them all available via a single connection.
I want the single central mcp server capability to be available on my linuxserver.lan for claude code cli, gemini cli, optionally chatgpt codex cli, open-webui, and vs code on a different machine on the local network.
First assigment is to identify what community supported tools are available to help maintain and make mcp's available in this manner.
I'll add to this requirement once we identify the right solution.
