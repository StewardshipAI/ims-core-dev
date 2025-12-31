class GatewayError(Exception):
    """Base exception for Action Gateway"""
    pass

class AdapterError(GatewayError):
    """Error in vendor adapter"""
    pass

class AuthenticationError(AdapterError):
    """Invalid credentials"""
    pass

class RateLimitError(AdapterError):
    """Rate limit exceeded"""
    pass

class ExecutionError(AdapterError):
    """Execution failed"""
    pass

class ModelNotSupportedError(AdapterError):
    """Model not supported by adapter"""
    pass
