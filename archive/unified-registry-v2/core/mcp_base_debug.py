"""
Enhanced MCP Base with comprehensive debugging
"""
import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Import the original base
from .mcp_base import MCPService

class MCPServiceDebug(MCPService):
    """Enhanced MCP Service with detailed debugging"""
    
    def __init__(self, name: str, version: str, config: dict):
        super().__init__(name, version, config)
        
        # Create debug log file
        log_dir = Path("/home/administrator/projects/mcp/unified-registry-v2/logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.debug_file = log_dir / f"debug_{name}_{timestamp}.jsonl"
        self.timing_file = log_dir / f"timing_{name}_{timestamp}.log"
        
        self._log_debug("SERVICE_INIT", {
            "name": name,
            "version": version,
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "env_database_url": bool(os.environ.get('DATABASE_URL')),
            "python_version": sys.version
        })
    
    def _log_debug(self, event_type: str, data: dict):
        """Log debug event to file"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }
        with open(self.debug_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def _log_timing(self, message: str):
        """Log timing information"""
        with open(self.timing_file, 'a') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}\n")
    
    def process_json_rpc_request(self, request: dict) -> dict:
        """Process request with detailed logging"""
        start_time = time.time()
        
        method = request.get("method")
        request_id = request.get("id")
        
        self._log_debug("REQUEST_RECEIVED", {
            "method": method,
            "id": request_id,
            "has_params": "params" in request
        })
        self._log_timing(f"Request {request_id}: {method}")
        
        try:
            response = super().process_json_rpc_request(request)
            
            elapsed = time.time() - start_time
            self._log_debug("RESPONSE_SENT", {
                "method": method,
                "id": request_id,
                "elapsed_ms": round(elapsed * 1000, 2),
                "has_result": "result" in response,
                "has_error": "error" in response
            })
            self._log_timing(f"Response {request_id}: {elapsed:.3f}s")
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            self._log_debug("REQUEST_ERROR", {
                "method": method,
                "id": request_id,
                "error": str(e),
                "elapsed_ms": round(elapsed * 1000, 2)
            })
            self._log_timing(f"Error {request_id}: {e}")
            raise
    
    def run_stdio_mode(self):
        """Run with enhanced debugging"""
        self._log_debug("STDIO_MODE_START", {
            "stdin_isatty": sys.stdin.isatty(),
            "stdout_isatty": sys.stdout.isatty(),
            "stderr_isatty": sys.stderr.isatty(),
            "buffering": {
                "python_unbuffered": bool(os.environ.get('PYTHONUNBUFFERED')),
                "mcp_debug": bool(os.environ.get('MCP_DEBUG'))
            }
        })
        self._log_timing("STDIO mode started")
        
        # Ensure unbuffered output
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
        sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)
        
        line_count = 0
        try:
            for line in sys.stdin:
                line_count += 1
                line = line.strip()
                
                self._log_debug("STDIN_LINE", {
                    "line_number": line_count,
                    "length": len(line),
                    "empty": not line
                })
                
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.process_json_rpc_request(request)
                    
                    # Write response
                    response_str = json.dumps(response)
                    print(response_str, flush=True)
                    
                    self._log_debug("STDOUT_WRITE", {
                        "line_number": line_count,
                        "response_length": len(response_str)
                    })
                    
                except json.JSONDecodeError as e:
                    self._log_debug("JSON_PARSE_ERROR", {
                        "line_number": line_count,
                        "error": str(e),
                        "line_preview": line[:100]
                    })
                    error_response = self.wrap_json_rpc_error(-32700, "Parse error", None)
                    print(json.dumps(error_response), flush=True)
                    
                except Exception as e:
                    self._log_debug("UNEXPECTED_ERROR", {
                        "line_number": line_count,
                        "error": str(e),
                        "type": type(e).__name__
                    })
                    error_response = self.wrap_json_rpc_error(-32603, "Internal error", None)
                    print(json.dumps(error_response), flush=True)
                    
        except KeyboardInterrupt:
            self._log_debug("STDIO_MODE_INTERRUPTED", {"lines_processed": line_count})
            self._log_timing("STDIO mode interrupted")
        except Exception as e:
            self._log_debug("STDIO_MODE_FATAL", {
                "lines_processed": line_count,
                "error": str(e)
            })
            self._log_timing(f"STDIO mode fatal error: {e}")
        finally:
            self._log_debug("STDIO_MODE_END", {"lines_processed": line_count})
            self._log_timing("STDIO mode ended")