class RateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)
        super().__init__(f"Platform rate limit reached; retry after {self.retry_after} seconds.")
