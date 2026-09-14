class MaxIterationsExceeded(Exception):
    """The loop used its whole budget of steps without the model finishing."""


class ResponseTruncated(Exception):
    """The model hit max_tokens mid-reply, so its answer is incomplete."""
