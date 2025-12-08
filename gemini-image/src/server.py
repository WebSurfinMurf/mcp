"""
MCP Gemini Image Server
Provides Google Gemini (Nano Banana) image generation via MCP endpoint
Supports text-to-image and image editing capabilities
"""
import os
import json
import base64
import requests
from typing import Dict, Any, Optional, Union, List
from fastapi import FastAPI
from pydantic import BaseModel
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Gemini Image Server", version="1.0.0")

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/workspace/generated-images")

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

# MCP Tool Definitions
TOOLS = [
    {
        "name": "generate_image",
        "description": "Generate an image using Google Gemini (Nano Banana). Provide a detailed text prompt describing exactly what you want. Great for creating specific images that stock photos can't provide (e.g., 'Irish flat cap made of Donegal tweed on a wooden pub table').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate. Be specific about style, colors, composition, lighting, etc."
                },
                "model": {
                    "type": "string",
                    "description": "Model to use: 'flash' (fast, Nano Banana) or 'pro' (better quality, Nano Banana Pro)",
                    "enum": ["flash", "pro"],
                    "default": "flash"
                },
                "aspect_ratio": {
                    "type": "string",
                    "description": "Aspect ratio for the image",
                    "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"],
                    "default": "16:9"
                },
                "filename": {
                    "type": "string",
                    "description": "Optional filename (without extension) to save the image. If not provided, a timestamp-based name is used."
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "generate_image_with_reference",
        "description": "Generate an image based on a reference image plus text prompt. Useful for style transfer, variations, or editing existing images.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text prompt describing how to modify or use the reference image"
                },
                "reference_image_path": {
                    "type": "string",
                    "description": "Path to the reference image file"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use: 'flash' or 'pro'",
                    "enum": ["flash", "pro"],
                    "default": "flash"
                },
                "filename": {
                    "type": "string",
                    "description": "Optional filename for the output"
                }
            },
            "required": ["prompt", "reference_image_path"]
        }
    },
    {
        "name": "list_generated_images",
        "description": "List all previously generated images in the output directory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of images to list (default: 20)",
                    "default": 20
                }
            }
        }
    }
]

def get_model_name(model_type: str) -> str:
    """Get the full model name from short type"""
    # Nano Banana Pro (higher quality, 4K support)
    if model_type == "pro":
        return "gemini-2.5-flash-image"
    # Nano Banana (fast)
    return "gemini-2.0-flash-exp-image-generation"

def generate_image_api(prompt: str, model: str = "flash", aspect_ratio: str = "16:9",
                       reference_image_base64: Optional[str] = None) -> Dict[str, Any]:
    """Call Gemini API to generate an image"""

    model_name = get_model_name(model)
    url = f"{GEMINI_API_BASE}/models/{model_name}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    # Build the request payload
    contents = []

    # Add reference image if provided
    if reference_image_base64:
        contents.append({
            "role": "user",
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": reference_image_base64
                    }
                },
                {"text": prompt}
            ]
        })
    else:
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

    payload = {
        "contents": contents,
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    logger.info(f"Calling Gemini API with model {model_name}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        raise

def save_image(image_data: str, filename: Optional[str] = None) -> str:
    """Save base64 image data to file and return path"""
    if not filename:
        filename = f"gemini_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    filepath = os.path.join(OUTPUT_DIR, f"{filename}.png")

    # Decode and save
    image_bytes = base64.b64decode(image_data)
    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    logger.info(f"Saved image to {filepath}")
    return filepath

def handle_generate_image(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle image generation request"""
    prompt = arguments.get("prompt")
    model = arguments.get("model", "flash")
    aspect_ratio = arguments.get("aspect_ratio", "16:9")
    filename = arguments.get("filename")

    # Enhance prompt with aspect ratio hint
    enhanced_prompt = f"{prompt}. Generate in {aspect_ratio} aspect ratio."

    try:
        result = generate_image_api(enhanced_prompt, model, aspect_ratio)

        # Extract image from response
        candidates = result.get("candidates", [])
        if not candidates:
            return {"success": False, "error": "No image generated"}

        parts = candidates[0].get("content", {}).get("parts", [])

        image_data = None
        text_response = None

        for part in parts:
            if "inlineData" in part:
                image_data = part["inlineData"].get("data")
            if "text" in part:
                text_response = part["text"]

        if not image_data:
            return {
                "success": False,
                "error": "No image in response",
                "text_response": text_response
            }

        # Save the image
        filepath = save_image(image_data, filename)

        return {
            "success": True,
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "model": model,
            "prompt": prompt,
            "text_response": text_response,
            "message": f"Image generated and saved to {filepath}"
        }

    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

def handle_generate_with_reference(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle image generation with reference image"""
    prompt = arguments.get("prompt")
    reference_path = arguments.get("reference_image_path")
    model = arguments.get("model", "flash")
    filename = arguments.get("filename")

    # Read and encode reference image
    try:
        with open(reference_path, 'rb') as f:
            reference_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        return {"success": False, "error": f"Could not read reference image: {e}"}

    try:
        result = generate_image_api(prompt, model, reference_image_base64=reference_base64)

        candidates = result.get("candidates", [])
        if not candidates:
            return {"success": False, "error": "No image generated"}

        parts = candidates[0].get("content", {}).get("parts", [])

        image_data = None
        text_response = None

        for part in parts:
            if "inlineData" in part:
                image_data = part["inlineData"].get("data")
            if "text" in part:
                text_response = part["text"]

        if not image_data:
            return {
                "success": False,
                "error": "No image in response",
                "text_response": text_response
            }

        filepath = save_image(image_data, filename)

        return {
            "success": True,
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "reference_used": reference_path,
            "model": model,
            "prompt": prompt,
            "text_response": text_response,
            "message": f"Image generated and saved to {filepath}"
        }

    except Exception as e:
        logger.error(f"Error generating image with reference: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

def handle_list_images(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """List generated images"""
    limit = arguments.get("limit", 20)

    try:
        images = []
        for f in sorted(Path(OUTPUT_DIR).glob("*.png"), key=os.path.getmtime, reverse=True)[:limit]:
            stat = f.stat()
            images.append({
                "filename": f.name,
                "filepath": str(f),
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

        return {
            "success": True,
            "count": len(images),
            "images": images,
            "output_dir": OUTPUT_DIR
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP endpoint"""
    try:
        method = request.method
        params = request.params or {}

        if method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "gemini-image",
                        "version": "1.0.0"
                    }
                }
            )

        elif method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={"tools": TOOLS}
            )

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "generate_image":
                result = handle_generate_image(arguments)
            elif tool_name == "generate_image_with_reference":
                result = handle_generate_with_reference(arguments)
            elif tool_name == "list_generated_images":
                result = handle_list_images(arguments)
            else:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Unknown tool: {tool_name}"}
                )

            return MCPResponse(
                id=request.id,
                result={
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2)}
                    ]
                }
            )

        else:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Unknown method: {method}"}
            )

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return MCPResponse(
            id=request.id,
            error={"code": -32603, "message": str(e)}
        )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api_key_configured": bool(GEMINI_API_KEY),
        "output_dir": OUTPUT_DIR
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
