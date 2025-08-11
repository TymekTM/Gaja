"""Moduł obsługi timeoutów i retry dla systemu testowego."""

import asyncio
import functools
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union

from loguru import logger

T = TypeVar('T')


def simple_timeout(seconds: float):
    """Prosty dekorator timeout dla funkcji async."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {seconds}s")
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
        return wrapper
    return decorator


def simple_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Prosty dekorator retry z exponential backoff."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts")
                        if last_exception:
                            raise last_exception
                        raise e
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
            
            # To nie powinno się wydarzyć, ale dla pewności
            if last_exception:
                raise last_exception
            raise Exception("All retry attempts failed")
        
        return wrapper
    return decorator


class TimeoutManager:
    """Manager timeoutów dla różnych operacji."""
    
    def __init__(self, default_timeout: float = 45.0):
        self.default_timeout = default_timeout
        self.operation_timeouts = {
            "api_call": 30.0,
            "tts_generation": 60.0,
            "audio_processing": 45.0,
            "grader_evaluation": 20.0,
            "file_operation": 10.0
        }
    
    def get_timeout(self, operation: str) -> float:
        """Zwraca timeout dla danej operacji."""
        return self.operation_timeouts.get(operation, self.default_timeout)
    
    async def with_timeout(
        self, 
        operation: str, 
        coro: Awaitable[T],
        custom_timeout: Optional[float] = None
    ) -> T:
        """Wykonuje operację z timeoutem."""
        timeout_value = custom_timeout or self.get_timeout(operation)
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout_value)
        except asyncio.TimeoutError:
            logger.error(f"Operation '{operation}' timed out after {timeout_value}s")
            raise TimeoutError(f"Operation '{operation}' timed out after {timeout_value} seconds")


# Dekoratory gotowe do użycia
api_timeout = simple_timeout(30.0)
tts_timeout = simple_timeout(60.0)
grader_timeout = simple_timeout(20.0)

api_retry = simple_retry(max_attempts=3, delay=2.0)
network_retry = simple_retry(max_attempts=5, delay=1.0, exceptions=(ConnectionError, TimeoutError))
