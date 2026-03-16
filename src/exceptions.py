class VLLMError(Exception):
    """Raised by VLLMClient when vLLM is unreachable or returns an error.

    Why a custom exception instead of returning error dicts: route handlers
    stay clean (no try/except), and the error shape is enforced in one place —
    the app-level exception handler in main.py.
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)
