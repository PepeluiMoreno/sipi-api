"""Resolver Decorators"""
from functools import wraps

def async_safe_resolver(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"[Resolver Error] {func.__name__}: {e}")
            return None
    return wrapper
