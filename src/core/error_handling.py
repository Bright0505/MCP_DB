"""Unified error handling for REST API and MCP protocol.

Provides standardized error response formats and exception handling.
"""

import logging
import traceback
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorFormat(Enum):
    """Error response format types."""
    REST_API = "rest_api"      # REST API format: {"success": false, "error": "..."}
    MCP_TOOL = "mcp_tool"       # MCP tool format: {"content": [{"type": "text", "text": "Error: ..."}]}


def format_error_response(
    error: Exception,
    format_type: ErrorFormat = ErrorFormat.REST_API,
    include_stacktrace: bool = False,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format error response in specified format.

    Args:
        error: The exception that occurred
        format_type: Desired response format (REST_API or MCP_TOOL)
        include_stacktrace: Whether to include stack trace (for debugging)
        context: Additional context information

    Returns:
        Formatted error response dict
    """
    error_message = str(error)
    error_type = type(error).__name__

    if format_type == ErrorFormat.REST_API:
        response = {
            "success": False,
            "error": error_message,
            "error_type": error_type
        }

        if context:
            response["context"] = context

        if include_stacktrace:
            response["stacktrace"] = traceback.format_exc()

    elif format_type == ErrorFormat.MCP_TOOL:
        error_text = f"Error: {error_message}"

        if include_stacktrace:
            error_text += f"\n\nStack trace:\n{traceback.format_exc()}"

        if context:
            error_text += f"\n\nContext: {context}"

        response = {
            "content": [{
                "type": "text",
                "text": error_text
            }],
            "isError": True
        }

    logger.error(f"{error_type}: {error_message}", exc_info=include_stacktrace)

    return response


def format_success_response(
    data: Any,
    format_type: ErrorFormat = ErrorFormat.REST_API,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Format success response in specified format.

    Args:
        data: The response data
        format_type: Desired response format
        message: Optional success message

    Returns:
        Formatted success response dict
    """
    if format_type == ErrorFormat.REST_API:
        response = {
            "success": True,
            "data": data
        }
        if message:
            response["message"] = message

    elif format_type == ErrorFormat.MCP_TOOL:
        # For MCP, if data is already in content format, return as-is
        if isinstance(data, dict) and "content" in data:
            return data

        # Otherwise, wrap in content format
        if isinstance(data, str):
            text = data
        elif isinstance(data, dict):
            # Convert dict to formatted text
            import json
            text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            text = str(data)

        response = {
            "content": [{
                "type": "text",
                "text": text
            }]
        }

    return response


def safe_execute(
    func: callable,
    format_type: ErrorFormat = ErrorFormat.REST_API,
    include_stacktrace: bool = False,
    context: Optional[Dict[str, Any]] = None
):
    """Safely execute a function and return formatted response.

    Args:
        func: Function to execute
        format_type: Error response format
        include_stacktrace: Include stacktrace in error responses
        context: Additional context for error reporting

    Returns:
        Formatted success or error response
    """
    try:
        result = func()
        return format_success_response(result, format_type)
    except Exception as e:
        return format_error_response(e, format_type, include_stacktrace, context)


async def safe_execute_async(
    func: callable,
    format_type: ErrorFormat = ErrorFormat.REST_API,
    include_stacktrace: bool = False,
    context: Optional[Dict[str, Any]] = None
):
    """Safely execute an async function and return formatted response.

    Args:
        func: Async function to execute
        format_type: Error response format
        include_stacktrace: Include stacktrace in error responses
        context: Additional context for error reporting

    Returns:
        Formatted success or error response
    """
    try:
        result = await func()
        return format_success_response(result, format_type)
    except Exception as e:
        return format_error_response(e, format_type, include_stacktrace, context)
