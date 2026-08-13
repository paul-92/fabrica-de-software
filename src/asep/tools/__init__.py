"""Contratos e implementações oficiais de Tools da ASEP."""

from asep.tools.builtin import (
    CompileAllTool,
    ListDirectoryTool,
    ReadDocumentationTool,
    ReadFileTool,
    RunTestsTool,
    SearchFilesTool,
    WriteFileTool,
)
from asep.tools.contracts import Tool, ToolExecutor
from asep.tools.exceptions import (
    InvalidToolRegistrationError,
    ToolAlreadyRegisteredError,
    ToolCapabilityNotSupportedError,
    ToolDuplicateExecutionError,
    ToolException,
    ToolExecutionError,
    ToolNotRegisteredError,
    ToolRetryExhaustedError,
    ToolSecurityError,
    ToolTimeoutError,
    ToolValidationError,
)
from asep.tools.execution_service import ToolExecutionService
from asep.tools.metrics import (
    InMemoryToolMetrics,
    ToolMetricsRecorder,
    ToolMetricsSnapshot,
)
from asep.tools.models import (
    ToolCapability,
    ToolContext,
    ToolError,
    ToolExecutionPolicy,
    ToolExecutionStatus,
    ToolId,
    ToolMetadata,
    ToolRequest,
    ToolResult,
)
from asep.tools.node_validation import (
    NpmScriptValidationTool,
    node_validation_tools,
    resolve_npm_executable,
)
from asep.tools.registry import InMemoryToolRegistry, ToolRegistry
from asep.tools.validator import ToolValidator

__all__ = [
    "CompileAllTool",
    "InMemoryToolMetrics",
    "InMemoryToolRegistry",
    "InvalidToolRegistrationError",
    "ListDirectoryTool",
    "NpmScriptValidationTool",
    "ReadDocumentationTool",
    "ReadFileTool",
    "RunTestsTool",
    "SearchFilesTool",
    "Tool",
    "ToolAlreadyRegisteredError",
    "ToolCapability",
    "ToolCapabilityNotSupportedError",
    "ToolContext",
    "ToolDuplicateExecutionError",
    "ToolError",
    "ToolException",
    "ToolExecutionError",
    "ToolExecutionPolicy",
    "ToolExecutionService",
    "ToolExecutionStatus",
    "ToolExecutor",
    "ToolId",
    "ToolMetadata",
    "ToolMetricsRecorder",
    "ToolMetricsSnapshot",
    "ToolNotRegisteredError",
    "ToolRegistry",
    "ToolRequest",
    "ToolResult",
    "ToolRetryExhaustedError",
    "ToolSecurityError",
    "ToolTimeoutError",
    "ToolValidationError",
    "ToolValidator",
    "WriteFileTool",
    "node_validation_tools",
    "resolve_npm_executable",
]
