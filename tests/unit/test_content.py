"""
Tests for core.content - ContentRegistry loading and domain categories.
"""

import pytest
from core.content import ContentRegistry
from config import settings


pytestmark = pytest.mark.unit


class TestContentRegistry:
    """Test ContentRegistry initialization and queries."""

    def test_initializes_without_error(self):
        ContentRegistry._initialized = False
        ContentRegistry._content = {}
        ContentRegistry.initialize()
        assert ContentRegistry._initialized is True

    def test_all_domains_have_categories(self):
        ContentRegistry.initialize()
        for domain_num in settings.EXAM_DOMAINS:
            cats = ContentRegistry.get_categories_for_domain(domain_num)
            assert len(cats) >= 1, f"Domain {domain_num} has no categories"

    def test_get_topic_returns_dict(self):
        ContentRegistry.initialize()
        topic = ContentRegistry.get_topic("lvm")
        assert topic is not None
        assert isinstance(topic, dict)
        assert "name" in topic
        assert "explanation" in topic
        assert "commands" in topic

    def test_get_topic_unknown_returns_none(self):
        ContentRegistry.initialize()
        topic = ContentRegistry.get_topic("nonexistent_category")
        assert topic is None

    def test_get_categories_for_domain_matches_settings(self):
        ContentRegistry.initialize()
        for cat, domain in settings.CATEGORY_TO_DOMAIN.items():
            domain_cats = ContentRegistry.get_categories_for_domain(domain)
            # Not all settings categories may have content, but content categories
            # should be a subset of settings
            if cat in ContentRegistry.get_all_categories():
                assert cat in domain_cats, (
                    f"{cat} (domain {domain}) missing from ContentRegistry"
                )
