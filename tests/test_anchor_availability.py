"""
Tests for the anchor-aware availability computation.

Tests the core overlap logic in get_available_anchors() by mocking
external dependencies (Google Calendar API, Supabase).
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.adaptive_scheduler import (
    get_available_anchors,
    format_availability_for_prompt,
    anchor_to_timestamp,
    ANCHOR_TIME_MAP,
)

TZ = ZoneInfo("America/Los_Angeles")
ANCHORS = ["Morning Coffee", "After Lunch", "End of Day"]
# Morning Coffee = 8:00, After Lunch = 13:30, End of Day = 17:00


def make_event(date_str: str, start_hour: int, start_min: int, end_hour: int, end_min: int, summary: str = "Meeting") -> dict:
    """Helper to create a busy event dict."""
    d = datetime.fromisoformat(date_str)
    return {
        "start": d.replace(hour=start_hour, minute=start_min, tzinfo=TZ),
        "end": d.replace(hour=end_hour, minute=end_min, tzinfo=TZ),
        "summary": summary,
    }


def run(coro):
    """Run an async function synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# Patch targets
PATCH_CALENDAR = "app.services.calendar_service.fetch_raw_calendar_events"
PATCH_SUPABASE = "app.agent.adaptive_scheduler.supabase"


class TestAnchorToTimestamp:
    """Test the basic anchor → timestamp conversion."""

    def test_known_anchor(self):
        base = datetime(2026, 2, 10, tzinfo=TZ)
        result = anchor_to_timestamp("Morning Coffee", "America/Los_Angeles", base)
        assert result.hour == 8
        assert result.minute == 0

    def test_after_lunch(self):
        base = datetime(2026, 2, 10, tzinfo=TZ)
        result = anchor_to_timestamp("After Lunch", "America/Los_Angeles", base)
        assert result.hour == 13
        assert result.minute == 30

    def test_unknown_anchor_defaults_to_afternoon(self):
        base = datetime(2026, 2, 10, tzinfo=TZ)
        result = anchor_to_timestamp("Random Nonsense", "America/Los_Angeles", base)
        assert result.hour == 14  # Default fallback
        assert result.minute == 0

    def test_case_insensitive_matching(self):
        base = datetime(2026, 2, 10, tzinfo=TZ)
        result = anchor_to_timestamp("morning coffee time", "America/Los_Angeles", base)
        assert result.hour == 8


class TestGetAvailableAnchors:
    """Test the anchor availability computation with mocked externals."""

    @patch(PATCH_SUPABASE, None)  # No Supabase
    @patch(PATCH_CALENDAR, new_callable=AsyncMock, return_value=[])
    def test_no_events_all_anchors_available(self, mock_cal):
        """With no calendar events and no Goally tasks, all anchors should be available."""
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert "2026-02-10" in result
        assert result["2026-02-10"] == ["Morning Coffee", "After Lunch", "End of Day"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_full_overlap_blocks_anchor(self, mock_cal):
        """An event covering the entire Morning Coffee window should block it."""
        # Event: 7:30-9:00 covers Morning Coffee (8:00-8:20)
        mock_cal.return_value = [
            make_event("2026-02-10", 7, 30, 9, 0, "Standup"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert "Morning Coffee" not in result["2026-02-10"]
        assert "After Lunch" in result["2026-02-10"]
        assert "End of Day" in result["2026-02-10"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_partial_overlap_start(self, mock_cal):
        """Event starting 5 minutes into the anchor window should block it."""
        # Event: 8:05-8:30 overlaps with Morning Coffee (8:00-8:20)
        mock_cal.return_value = [
            make_event("2026-02-10", 8, 5, 8, 30, "Quick call"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert "Morning Coffee" not in result["2026-02-10"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_partial_overlap_end(self, mock_cal):
        """Event ending during the anchor window should block it."""
        # Event: 7:45-8:10 ends during Morning Coffee (8:00-8:20)
        mock_cal.return_value = [
            make_event("2026-02-10", 7, 45, 8, 10, "Early meeting"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert "Morning Coffee" not in result["2026-02-10"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_adjacent_event_no_overlap(self, mock_cal):
        """Event ending exactly when anchor starts should NOT block it."""
        # Event: 7:00-8:00 ends right when Morning Coffee starts
        mock_cal.return_value = [
            make_event("2026-02-10", 7, 0, 8, 0, "Early standup"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        # No overlap: event ends at 8:00, anchor starts at 8:00
        # Overlap formula: (8:00 < 8:00) is False, so not blocked
        assert "Morning Coffee" in result["2026-02-10"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_all_day_event_blocks_everything(self, mock_cal):
        """A full-day event (conference) should block all anchors."""
        mock_cal.return_value = [
            make_event("2026-02-10", 0, 0, 23, 59, "All-Day Conference"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert result["2026-02-10"] == []

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_multi_day_only_affects_correct_days(self, mock_cal):
        """Events on day 1 should not affect day 2 availability."""
        mock_cal.return_value = [
            # Day 1: block morning
            make_event("2026-02-10", 7, 30, 9, 0, "Day 1 meeting"),
            # Day 2: block afternoon
            make_event("2026-02-11", 13, 0, 14, 0, "Day 2 meeting"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=2))

        # Day 1: Morning blocked, others free
        assert "Morning Coffee" not in result["2026-02-10"]
        assert "After Lunch" in result["2026-02-10"]

        # Day 2: After Lunch blocked, others free
        assert "Morning Coffee" in result["2026-02-11"]
        assert "After Lunch" not in result["2026-02-11"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_multiple_events_block_multiple_anchors(self, mock_cal):
        """Multiple events should independently block their respective anchors."""
        mock_cal.return_value = [
            make_event("2026-02-10", 7, 30, 9, 0, "Morning sync"),
            make_event("2026-02-10", 13, 0, 14, 0, "Lunch meeting"),
            make_event("2026-02-10", 16, 45, 17, 30, "EOD review"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert result["2026-02-10"] == []  # All three anchors blocked

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_event_before_anchor_no_block(self, mock_cal):
        """Event well before anchor time should not block it."""
        # Event at 6:00-7:00, Morning Coffee at 8:00
        mock_cal.return_value = [
            make_event("2026-02-10", 6, 0, 7, 0, "Early workout"),
        ]
        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert "Morning Coffee" in result["2026-02-10"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_custom_task_duration(self, mock_cal):
        """Longer task duration should make the anchor window wider and easier to block."""
        # Event at 8:15-8:45. With 20min duration: anchor window 8:00-8:20 overlaps.
        # With 5min duration: anchor window 8:00-8:05, no overlap.
        mock_cal.return_value = [
            make_event("2026-02-10", 8, 15, 8, 45, "Short call"),
        ]

        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            # 20 min task: anchor 8:00-8:20 overlaps with event 8:15-8:45
            result_20 = run(get_available_anchors("user1", ANCHORS, days_ahead=1, task_duration_minutes=20))
            assert "Morning Coffee" not in result_20["2026-02-10"]

            # 5 min task: anchor 8:00-8:05 does NOT overlap with event 8:15-8:45
            result_5 = run(get_available_anchors("user1", ANCHORS, days_ahead=1, task_duration_minutes=5))
            assert "Morning Coffee" in result_5["2026-02-10"]

    @patch(PATCH_SUPABASE, None)
    @patch(PATCH_CALENDAR, new_callable=AsyncMock)
    def test_calendar_fetch_failure_returns_all_available(self, mock_cal):
        """If Google Calendar fetch fails, all anchors should be available."""
        mock_cal.side_effect = Exception("API error")

        with patch("app.agent.adaptive_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 10, 7, 0, tzinfo=TZ)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = run(get_available_anchors("user1", ANCHORS, days_ahead=1))

        assert result["2026-02-10"] == ["Morning Coffee", "After Lunch", "End of Day"]


class TestFormatAvailabilityForPrompt:
    """Test the prompt formatting."""

    def test_mixed_availability(self):
        availability = {
            "2026-02-10": ["Morning Coffee", "End of Day"],
            "2026-02-11": [],
            "2026-02-12": ["Morning Coffee", "After Lunch", "End of Day"],
        }
        result = format_availability_for_prompt(availability)

        assert "Morning Coffee, End of Day" in result
        assert "NO available slots" in result
        assert "Morning Coffee, After Lunch, End of Day" in result

    def test_empty_availability(self):
        result = format_availability_for_prompt({})
        assert "Available Time Slots" in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
