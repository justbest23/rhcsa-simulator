"""
Task registry system for RHCSA Simulator v4.0.0
Auto-discovers task modules using pkgutil.iter_modules().
"""

import random
import logging
import pkgutil
import importlib
from collections import defaultdict
from typing import List, Optional
from config import settings


logger = logging.getLogger(__name__)


class TaskRegistry:
    """Central registry for all task classes using auto-discovery."""

    _instance = None
    _tasks = defaultdict(list)
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, category):
        """Decorator to register task classes."""
        def wrapper(task_class):
            cls._tasks[category].append(task_class)
            logger.debug(f"Registered task: {task_class.__name__} in category {category}")
            return task_class
        return wrapper

    @classmethod
    def get_all_categories(cls):
        return list(cls._tasks.keys())

    @classmethod
    def get_tasks_by_category(cls, category):
        return cls._tasks.get(category, [])

    @classmethod
    def get_tasks_by_domain(cls, domain_number):
        """Get all task classes for a given exam domain (1-9)."""
        domain_categories = [
            cat for cat, dom in settings.CATEGORY_TO_DOMAIN.items()
            if dom == domain_number
        ]
        tasks = []
        for cat in domain_categories:
            tasks.extend(cls._tasks.get(cat, []))
        return tasks

    @classmethod
    def get_persistence_tasks(cls):
        """Get all task classes that require persistence validation."""
        results = []
        for cat_tasks in cls._tasks.values():
            for task_class in cat_tasks:
                try:
                    instance = task_class()
                    if instance.requires_persistence:
                        results.append(task_class)
                except Exception:
                    pass
        return results

    @classmethod
    def get_tasks_by_tag(cls, tag):
        """Get all task classes with a specific tag."""
        results = []
        for cat_tasks in cls._tasks.values():
            for task_class in cat_tasks:
                try:
                    instance = task_class()
                    if tag in instance.tags:
                        results.append(task_class)
                except Exception:
                    pass
        return results

    @classmethod
    def get_task_count(cls, category=None):
        if category:
            return len(cls._tasks.get(category, []))
        return sum(len(tasks) for tasks in cls._tasks.values())

    @classmethod
    def get_random_task(cls, category=None, difficulty=None):
        if category:
            task_classes = cls._tasks.get(category, [])
        else:
            task_classes = []
            for cat_tasks in cls._tasks.values():
                task_classes.extend(cat_tasks)

        if not task_classes:
            return None

        # Filter by difficulty
        if difficulty:
            filtered = []
            for tc in task_classes:
                try:
                    inst = tc()
                    if inst.difficulty == difficulty:
                        filtered.append(tc)
                except Exception:
                    pass
            if filtered:
                task_classes = filtered

        task_class = random.choice(task_classes)
        try:
            task = task_class()
            task.generate()
            return task
        except Exception as e:
            logger.error(f"Error creating task from {task_class.__name__}: {e}")
            return None

    @classmethod
    def get_random_tasks(cls, count, categories=None, difficulty=None, exclude_ids=None):
        tasks = []
        exclude_ids = exclude_ids or []
        attempts = 0
        max_attempts = count * 10

        if categories:
            available_categories = [c for c in categories if c in cls._tasks]
        else:
            available_categories = list(cls._tasks.keys())

        if not available_categories:
            return []

        while len(tasks) < count and attempts < max_attempts:
            attempts += 1
            category = available_categories[len(tasks) % len(available_categories)]
            task = cls.get_random_task(category=category, difficulty=difficulty)
            if task and task.id not in exclude_ids:
                tasks.append(task)
                exclude_ids.append(task.id)

        return tasks

    @classmethod
    def get_exam_tasks(cls, count=None):
        if count is None:
            count = settings.DEFAULT_EXAM_TASKS
        return cls.get_random_tasks(count, difficulty="exam")

    @classmethod
    def generate_exam(cls, count=12):
        """
        Generate a balanced exam across all 9 domains.
        60%+ persistence tasks, weighted by domain importance.
        """
        tasks = []
        exclude_ids = []

        # Distribute tasks across domains weighted by domain weight
        from config.exam_objectives import EXAM_OBJECTIVES
        total_weight = sum(d["weight"] for d in EXAM_OBJECTIVES.values())

        domain_counts = {}
        remaining = count
        for domain_num in sorted(EXAM_OBJECTIVES.keys()):
            weight = EXAM_OBJECTIVES[domain_num]["weight"]
            domain_counts[domain_num] = max(1, round(count * weight / total_weight))
            remaining -= domain_counts[domain_num]

        # Distribute any remainder
        while remaining > 0:
            for d in sorted(domain_counts, key=lambda x: domain_counts[x]):
                if remaining <= 0:
                    break
                domain_counts[d] += 1
                remaining -= 1

        # Trim if over count
        while sum(domain_counts.values()) > count:
            trimmed = False
            for d in sorted(domain_counts, key=lambda x: -domain_counts[x]):
                if sum(domain_counts.values()) <= count:
                    break
                if domain_counts[d] > 0:
                    domain_counts[d] -= 1
                    trimmed = True
            if not trimmed:
                break

        # Generate tasks per domain
        for domain_num, needed in domain_counts.items():
            domain_cats = [
                cat for cat, dom in settings.CATEGORY_TO_DOMAIN.items()
                if dom == domain_num
            ]
            available_cats = [c for c in domain_cats if c in cls._tasks]
            if not available_cats:
                continue

            for _ in range(needed):
                cat = random.choice(available_cats)
                # Prefer exam difficulty, fall back to medium/hard
                task = cls.get_random_task(category=cat, difficulty="exam")
                if not task:
                    task = cls.get_random_task(category=cat)
                if task and task.id not in exclude_ids:
                    tasks.append(task)
                    exclude_ids.append(task.id)

        # If we couldn't fill all slots, add random tasks
        while len(tasks) < count:
            task = cls.get_random_task(difficulty="exam")
            if task and task.id not in exclude_ids:
                tasks.append(task)
                exclude_ids.append(task.id)

        random.shuffle(tasks)
        return tasks

    @classmethod
    def get_practice_tasks(cls, category, difficulty="exam", count=None):
        if count is None:
            count = settings.DEFAULT_PRACTICE_TASKS
        tasks = cls.get_random_tasks(count, categories=[category], difficulty=difficulty)
        # Sort by task_order to ensure logical dependency ordering (None = no constraint, sort last)
        tasks.sort(key=lambda t: (t.task_order is None, t.task_order or 0))
        return tasks

    @classmethod
    def initialize(cls):
        """Initialize task registry by auto-discovering all task modules."""
        if cls._initialized:
            return

        logger.info("Initializing task registry (auto-discovery)...")

        import tasks as tasks_package
        package_path = tasks_package.__path__

        for importer, module_name, is_pkg in pkgutil.iter_modules(package_path):
            if module_name in ('base', 'registry', '__init__'):
                continue
            full_module_name = f"tasks.{module_name}"
            try:
                importlib.import_module(full_module_name)
                logger.debug(f"Imported {full_module_name}")
            except ImportError as e:
                logger.warning(f"Could not import {full_module_name}: {e}")
            except Exception as e:
                logger.error(f"Error importing {full_module_name}: {e}")

        cls._initialized = True
        logger.info(
            f"Task registry initialized with {cls.get_task_count()} tasks "
            f"across {len(cls.get_all_categories())} categories"
        )

    @classmethod
    def print_statistics(cls):
        """Print task registry statistics."""
        print("\nTask Registry Statistics:")
        print("=" * 60)
        print(f"Total categories: {len(cls.get_all_categories())}")
        print(f"Total tasks: {cls.get_task_count()}")

        # By domain
        print("\nTasks by Exam Domain:")
        for domain_num, domain_name in sorted(settings.EXAM_DOMAINS.items()):
            domain_tasks = cls.get_tasks_by_domain(domain_num)
            print(f"  Domain {domain_num}: {domain_name} - {len(domain_tasks)} tasks")

        print("\nTasks by Category:")
        for category in sorted(cls.get_all_categories()):
            count = cls.get_task_count(category)
            domain = settings.CATEGORY_TO_DOMAIN.get(category, "?")
            print(f"  {category}: {count} tasks (Domain {domain})")


_registry = TaskRegistry()


def get_registry():
    return _registry
