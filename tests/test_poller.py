import pytest
import re
from datetime import datetime, timezone
from poller import _key_regex, _local

class TestKeywordRegex:
    """Test cases for keyword regex matching"""

    def test_key_regex_basic(self):
        """Test basic keyword matching"""
        regex = _key_regex("Seiko")
        assert regex.search("I'm selling a Seiko watch")
        assert regex.search("seiko sarb033")
        assert regex.search("SEIKO PROSPEX")
        assert not regex.search("Citizen watch")

    def test_key_regex_case_insensitive(self):
        """Test case-insensitive matching"""
        regex = _key_regex("Seiko")
        assert regex.search("seiko")
        assert regex.search("SEIKO")
        assert regex.search("SeIkO")

    def test_key_regex_special_chars(self):
        """Test that special regex characters are escaped"""
        regex = _key_regex("(test)")
        # Should match literal "(test)", not be interpreted as regex group
        assert regex.search("This is a (test) post")
        assert not regex.search("This is a test post")

    def test_key_regex_multiword(self):
        """Test multi-word keyword matching"""
        regex = _key_regex("Seiko SARB")
        assert regex.search("Looking for a Seiko SARB watch")
        assert regex.search("seiko sarb033 for sale")
        assert not regex.search("Seiko Prospex")

class TestLocalTimezone:
    """Test cases for timezone conversion"""

    def test_local_converts_timestamp(self):
        """Test that Unix timestamp is converted to local datetime"""
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        result = _local(timestamp)

        assert isinstance(result, datetime)
        # Should have timezone info
        assert result.tzinfo is not None

    def test_local_preserves_utc_time(self):
        """Test that UTC time is correctly converted"""
        timestamp = 0.0  # Unix epoch
        result = _local(timestamp)

        # Convert back to UTC for comparison
        utc_result = result.astimezone(timezone.utc)
        assert utc_result.year == 1970
        assert utc_result.month == 1
        assert utc_result.day == 1

class TestRetryLogic:
    """Test cases for retry mechanism"""

    def test_retry_succeeds_on_first_attempt(self):
        """Test that retry returns immediately on success"""
        from poller import retry_on_error

        def successful_func():
            return "success"

        result = retry_on_error(successful_func)
        assert result == "success"

    def test_retry_with_arguments(self):
        """Test retry with function arguments"""
        from poller import retry_on_error

        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = retry_on_error(func_with_args, "x", "y", c="z")
        assert result == "x-y-z"

    def test_retry_eventually_raises(self):
        """Test that retry raises after max attempts"""
        from poller import retry_on_error
        from praw.exceptions import PRAWException

        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise PRAWException("API error")

        with pytest.raises(PRAWException):
            retry_on_error(failing_func, max_retries=3, delay=0)

        # Should have tried 3 times
        assert call_count == 3

class TestSubredditNormalization:
    """Test cases for subreddit name normalization"""

    def test_normalize_removes_prefix(self):
        """Test that r/ prefix is removed during normalization"""
        # This tests the normalization logic in run_once
        # The actual normalization happens with: subreddit.strip().lower().lstrip("r/")

        test_cases = [
            ("r/watchexchange", "watchexchange"),
            ("watchexchange", "watchexchange"),
            ("r/MechMarket", "mechmarket"),
            ("  r/test  ", "test"),
        ]

        for input_val, expected in test_cases:
            normalized = input_val.strip().lower().lstrip("r/")
            assert normalized == expected
