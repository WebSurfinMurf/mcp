Updated Workflow

  # 1. Implement a new MCP service
  ./deploy.sh setup
  # Create services/mcp_newservice.py

  # 2. Test the service
  ./deploy.sh run newservice stdio
  ./deploy.sh run newservice sse

  # 3. Register with Claude Code (ONE COMMAND)
  ./deploy.sh register newservice

  # 4. Restart Claude Code - service is ready!
