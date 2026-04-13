# MCP Server

Model Context Protocol server for AI assistant integration.

## Overview

MCP server implementation enabling Claude and other AI assistants to interact with external tools and services.

## Structure

```
mcp-server/
├── server.py           # MCP server implementation
├── tools.py            # Tool definitions
├── config.py           # Configuration
└── requirements.txt
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| MCP Protocol | JSON-RPC based communication |
| Tools | Callable functions exposed to AI |
| Resources | Data sources accessible to AI |

## Setup

```bash
pip install -r requirements.txt
python server.py
```

## References

- [MCP Specification](https://modelcontextprotocol.io/)
