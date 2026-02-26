"""
E2E tests for MenuSystem - dispatch, dashboard, help.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.menu import MenuSystem


pytestmark = pytest.mark.e2e


class TestMenuDispatch:
    """Test menu returns correct action strings."""

    @pytest.mark.parametrize("key,expected", [
        ("q", "quick_practice"),
        ("e", "exam"),
        ("1", "learn"),
        ("2", "practice"),
        ("3", "adaptive"),
        ("4", "dashboard"),
        ("5", "export"),
        ("s", "setup"),
        ("?", "help"),
        ("0", "exit"),
    ])
    def test_menu_key_dispatch(self, key, expected):
        menu = MenuSystem()
        with patch("builtins.input", return_value=key), \
             patch("core.menu.fmt"):
            result = menu.display_main_menu()
        assert result == expected

    def test_invalid_key_reprompts(self):
        menu = MenuSystem()
        # Invalid -> press enter on error prompt -> repaint menu -> exit
        with patch("builtins.input", side_effect=["x", "", "0"]), \
             patch("core.menu.fmt"):
            result = menu.display_main_menu()
        assert result == "exit"


class TestDashboard:
    """Test dashboard display."""

    def test_dashboard_empty_db(self, tmp_db):
        menu = MenuSystem()
        with patch("core.menu.fmt") as mock_fmt, \
             patch("builtins.input", return_value=""), \
             patch("core.results_db.get_results_db", return_value=tmp_db):
            mock_fmt.bold.side_effect = lambda x: x
            mock_fmt.info.side_effect = lambda x: x
            mock_fmt.success.side_effect = lambda x: x
            mock_fmt.error.side_effect = lambda x: x
            mock_fmt.dim.side_effect = lambda x: x
            mock_fmt.format_category_name.side_effect = lambda x: x
            menu.show_dashboard()

    def test_dashboard_with_data(self, tmp_db):
        tmp_db.save_exam_result(
            exam_id="exam-001",
            start_time="2025-01-01T10:00:00",
            end_time="2025-01-01T13:00:00",
            duration_seconds=10800,
            total_score=250,
            max_score=300,
            passed=True,
            reboot_passed=True,
        )
        tmp_db.save_practice_attempt(
            task_id="t1", category="lvm", difficulty="exam", domain=4,
            score=10, max_score=10, passed=True,
        )

        menu = MenuSystem()
        with patch("core.menu.fmt") as mock_fmt, \
             patch("builtins.input", return_value=""), \
             patch("core.results_db.get_results_db", return_value=tmp_db):
            mock_fmt.bold.side_effect = lambda x: x
            mock_fmt.info.side_effect = lambda x: x
            mock_fmt.success.side_effect = lambda x: x
            mock_fmt.error.side_effect = lambda x: x
            mock_fmt.dim.side_effect = lambda x: x
            mock_fmt.format_category_name.side_effect = lambda x: x
            menu.show_dashboard()


class TestHelp:
    """Test help display."""

    def test_help_mentions_version(self, capsys):
        menu = MenuSystem()
        with patch("builtins.input", return_value=""), \
             patch("core.menu.fmt") as mock_fmt:
            mock_fmt.bold.side_effect = lambda x: x
            mock_fmt.dim.side_effect = lambda x: x
            menu.show_help()
        captured = capsys.readouterr()
        assert "4.0.0" in captured.out
