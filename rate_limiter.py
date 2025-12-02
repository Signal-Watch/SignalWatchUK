"""
Rate limiter for API requests
Ensures compliance with Companies House rate limits (600 requests per 5 minutes)
"""
import time
from collections import deque
from threading import Lock
from config import Config


class RateLimiter:
    """Thread-safe rate limiter for API requests"""
    
    def __init__(self, max_requests=None, period=None):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed in period
            period: Time period in seconds
        """
        self.max_requests = max_requests or Config.RATE_LIMIT_REQUESTS
        self.period = period or Config.RATE_LIMIT_PERIOD
        self.requests = deque()
        self.lock = Lock()
    
    def acquire(self):
        """
        Acquire permission to make a request
        Blocks if rate limit would be exceeded
        """
        with self.lock:
            now = time.time()
            
            # Remove requests older than the period
            while self.requests and self.requests[0] < now - self.period:
                self.requests.popleft()
            
            # If at limit, wait until oldest request expires
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # Clean up again after sleeping
                    now = time.time()
                    while self.requests and self.requests[0] < now - self.period:
                        self.requests.popleft()
            
            # Record this request
            self.requests.append(now)
    
    def get_remaining_requests(self):
        """Get number of requests remaining in current period"""
        with self.lock:
            now = time.time()
            # Remove old requests
            while self.requests and self.requests[0] < now - self.period:
                self.requests.popleft()
            return self.max_requests - len(self.requests)
    
    def get_reset_time(self):
        """Get time in seconds until rate limit resets"""
        with self.lock:
            if not self.requests:
                return 0
            now = time.time()
            oldest = self.requests[0]
            reset_time = oldest + self.period - now
            return max(0, reset_time)
    
    def reset(self):
        """Clear all recorded requests"""
        with self.lock:
            self.requests.clear()
