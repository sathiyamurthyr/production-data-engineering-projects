"""Tool Registry - Register and manage agent tools."""

import inspect
import logging
from typing import Any, Callable

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Tool definition."""
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable
    category: str
    requires_approval: bool = False


class ToolRegistry:
    """Registry for agent tools."""
    
    def __init__(self):
        """Initialize tool registry."""
        self.tools: dict[str, ToolDefinition] = {}
        self.categories: dict[str, list[str]] = {}
    
    def register(self, tool: ToolDefinition) -> None:
        """Register tool.
        
        Args:
            tool: Tool definition
        """
        self.tools[tool.name] = tool
        
        if tool.category not in self.categories:
            self.categories[tool.category] = []
        
        self.categories[tool.category].append(tool.name)
        
        logger.info(f"Registered tool: {tool.name}")
    
    def register_from_function(
        self,
        func: Callable,
        name: str = None,
        description: str = None,
        category: str = "general",
        requires_approval: bool = False,
    ) -> None:
        """Register tool from function.
        
        Args:
            func: Function to register
            name: Tool name (default: function name)
            description: Tool description (default: function docstring)
            category: Tool category
            requires_approval: Whether tool requires approval
        """
        tool_name = name or func.__name__
        tool_description = description or (func.__doc__ or "")
        
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                "required": param.default == inspect.Parameter.empty,
            }
            
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            
            parameters[param_name] = param_info
        
        tool = ToolDefinition(
            name=tool_name,
            description=tool_description,
            parameters=parameters,
            function=func,
            category=category,
            requires_approval=requires_approval,
        )
        
        self.register(tool)
    
    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition or None
        """
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> list[ToolDefinition]:
        """Get tools by category.
        
        Args:
            category: Tool category
            
        Returns:
            List of tools
        """
        tool_names = self.categories.get(category, [])
        return [self.tools[name] for name in tool_names]
    
    def list_tools(self) -> list[ToolDefinition]:
        """List all tools.
        
        Returns:
            List of all tools
        """
        return list(self.tools.values())
    
    def list_categories(self) -> list[str]:
        """List all categories.
        
        Returns:
            List of categories
        """
        return list(self.categories.keys())
    
    def execute(self, name: str, **kwargs) -> Any:
        """Execute tool.
        
        Args:
            name: Tool name
            **kwargs: Tool parameters
            
        Returns:
            Tool result
        """
        tool = self.get_tool(name)
        
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        if tool.requires_approval:
            logger.warning(f"Tool {name} requires approval")
        
        try:
            result = tool.function(**kwargs)
            logger.info(f"Executed tool: {name}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {name}, error: {e}")
            raise


class CalculatorTool:
    """Calculator tool for mathematical operations."""
    
    name = "calculator"
    description = "Perform mathematical calculations"
    category = "utility"
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Sum
        """
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Difference
        """
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Product
        """
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide two numbers.
        
        Args:
            a: Numerator
            b: Denominator
            
        Returns:
            Quotient
        """
        if b == 0:
            raise ValueError("Division by zero")
        return a / b


class WebSearchTool:
    """Web search tool."""
    
    name = "web_search"
    description = "Search the web for information"
    category = "information"
    
    def __init__(self, api_key: str = None):
        """Initialize web search tool.
        
        Args:
            api_key: Search API key
        """
        self.api_key = api_key
    
    def search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """Search web for query.
        
        Args:
            query: Search query
            num_results: Number of results
            
        Returns:
            Search results
        """
        # Simplified - use actual search API in production
        return [
            {
                "title": f"Result for: {query}",
                "url": "https://example.com",
                "snippet": f"Information about {query}",
            }
        ]
    
    def get_page(self, url: str) -> str:
        """Get web page content.
        
        Args:
            url: Page URL
            
        Returns:
            Page content
        """
        # Simplified - use requests or playwright in production
        return f"Content from {url}"


class DatabaseQueryTool:
    """Database query tool."""
    
    name = "database_query"
    description = "Query database for information"
    category = "data"
    
    def __init__(self, connection_string: str):
        """Initialize database tool.
        
        Args:
            connection_string: Database connection string
        """
        self.connection_string = connection_string
    
    def query(self, sql: str, params: dict[str, Any] = None) -> list[dict[str, Any]]:
        """Execute SQL query.
        
        Args:
            sql: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        # Simplified - use actual database connection in production
        return []
    
    def get_schema(self, table_name: str) -> dict[str, Any]:
        """Get table schema.
        
        Args:
            table_name: Table name
            
        Returns:
            Table schema
        """
        # Simplified
        return {}


class CodeInterpreterTool:
    """Code interpreter tool."""
    
    name = "code_interpreter"
    description = "Execute Python code"
    category = "computation"
    
    def execute(self, code: str, timeout: int = 30) -> dict[str, Any]:
        """Execute Python code.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Execution result
        """
        try:
            # Simplified - use restricted execution in production
            # Use Docker or sandbox for safety
            result = eval(code)
            return {
                "success": True,
                "result": result,
                "output": str(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def analyze_data(self, data: list[dict[str, Any]], analysis_type: str) -> dict[str, Any]:
        """Analyze data.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            
        Returns:
            Analysis results
        """
        # Simplified - use pandas in production
        return {
            "analysis_type": analysis_type,
            "count": len(data),
        }


class FileOperationTool:
    """File operation tool."""
    
    name = "file_operation"
    description = "Perform file operations"
    category = "utility"
    
    def read_file(self, file_path: str) -> str:
        """Read file content.
        
        Args:
            file_path: File path
            
        Returns:
            File content
        """
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Write content to file.
        
        Args:
            file_path: File path
            content: Content to write
            
        Returns:
            True if successful
        """
        try:
            with open(file_path, "w") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"File write failed: {e}")
            return False
    
    def list_directory(self, directory_path: str) -> list[str]:
        """List directory contents.
        
        Args:
            directory_path: Directory path
            
        Returns:
            List of files
        """
        import os
        try:
            return os.listdir(directory_path)
        except Exception as e:
            logger.error(f"Directory listing failed: {e}")
            return []


class APIClientTool:
    """API client tool."""
    
    name = "api_client"
    description = "Make API requests"
    category = "integration"
    
    def __init__(self):
        """Initialize API client."""
        import requests
        self.requests = requests
    
    def get(self, url: str, headers: dict[str, str] = None, params: dict[str, str] = None) -> dict[str, Any]:
        """Make GET request.
        
        Args:
            url: Request URL
            headers: Request headers
            params: Query parameters
            
        Returns:
            Response
        """
        try:
            response = self.requests.get(url, headers=headers, params=params)
            return {
                "status_code": response.status_code,
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def post(self, url: str, headers: dict[str, str] = None, body: dict[str, Any] = None) -> dict[str, Any]:
        """Make POST request.
        
        Args:
            url: Request URL
            headers: Request headers
            body: Request body
            
        Returns:
            Response
        """
        try:
            response = self.requests.post(url, headers=headers, json=body)
            return {
                "status_code": response.status_code,
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            }
        except Exception as e:
            return {"error": str(e)}