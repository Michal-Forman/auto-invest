from uuid import uuid4

def generate_uuid() -> str:
    """
    Generate a unique identifier using UUID4.
    """
    return str(uuid4())
