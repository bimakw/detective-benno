"""Detective Benno - An intelligent code review detective powered by LLM.

Every line of code tells a story. I find the plot holes.
"""

__version__ = "0.2.0"
__author__ = "Bima Kharisma Wicaksana"

from detective_benno.models import ReviewComment, ReviewResult, Severity
from detective_benno.reviewer import CodeReviewer

__all__ = [
    "CodeReviewer",
    "ReviewResult",
    "ReviewComment",
    "Severity",
]
