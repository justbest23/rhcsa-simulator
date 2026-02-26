"""
Validation engine orchestrator for RHCSA Simulator v4.0.0
Coordinates all validators and aggregates results.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class ValidationCheck:
    """Single validation check result."""
    name: str
    passed: bool
    points: int
    message: str
    max_points: Optional[int] = None
    details: Optional[str] = None
    persistence_passed: Optional[bool] = None

    def __post_init__(self):
        if self.max_points is None:
            self.max_points = self.points

    def to_dict(self):
        return {
            'name': self.name,
            'passed': self.passed,
            'points': self.points,
            'max_points': self.max_points,
            'message': self.message,
            'details': self.details,
            'persistence_passed': self.persistence_passed,
        }


@dataclass
class ValidationResult:
    """Result of validating a single task."""
    task_id: str
    passed: bool
    score: int
    max_score: int
    checks: List[ValidationCheck] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def percentage(self):
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'passed': self.passed,
            'score': self.score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'checks': [check.to_dict() for check in self.checks],
            'error_message': self.error_message,
        }

    def get_summary(self):
        status = "PASS" if self.passed else "FAIL"
        return f"Score: {self.score}/{self.max_score} ({self.percentage:.0f}%) - {status}"


@dataclass
class RebootResult:
    """Result of reboot simulation."""
    boot_success: bool
    boot_blockers: List[str] = field(default_factory=list)
    persistence_results: Dict[str, ValidationResult] = field(default_factory=dict)
    tasks_lost_points: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'boot_success': self.boot_success,
            'boot_blockers': self.boot_blockers,
            'persistence_results': {
                tid: r.to_dict() for tid, r in self.persistence_results.items()
            },
            'tasks_lost_points': self.tasks_lost_points,
        }


class ValidationEngine:
    """Validation engine orchestrator."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_task(self, task):
        try:
            self.logger.info(f"Validating task: {task.id}")
            result = task.validate()
            if not isinstance(result, ValidationResult):
                self.logger.error(f"Task {task.id} returned invalid result type")
                return ValidationResult(
                    task_id=task.id, passed=False, score=0,
                    max_score=task.points,
                    error_message="Task validation returned invalid result type"
                )
            return result
        except Exception as e:
            self.logger.exception(f"Error validating task {task.id}")
            return ValidationResult(
                task_id=task.id, passed=False, score=0,
                max_score=getattr(task, 'points', 0),
                error_message=f"Validation error: {str(e)}"
            )

    def validate_persistence(self, task):
        """Validate that a task's results survive reboot."""
        try:
            self.logger.info(f"Validating persistence for task: {task.id}")
            result = task.validate_persistence()
            if not isinstance(result, ValidationResult):
                return ValidationResult(
                    task_id=task.id, passed=False, score=0,
                    max_score=task.points,
                    error_message="Persistence validation returned invalid result type"
                )
            return result
        except Exception as e:
            self.logger.exception(f"Error validating persistence for {task.id}")
            return ValidationResult(
                task_id=task.id, passed=False, score=0,
                max_score=getattr(task, 'points', 0),
                error_message=f"Persistence validation error: {str(e)}"
            )

    def validate_multiple_tasks(self, tasks, show_progress=True):
        results = []
        total = len(tasks)
        for i, task in enumerate(tasks, 1):
            if show_progress:
                from utils.formatters import print_progress_bar
                print_progress_bar(i - 1, total, prefix="Validating tasks")
            result = self.validate_task(task)
            results.append(result)
        if show_progress:
            from utils.formatters import print_progress_bar
            print_progress_bar(total, total, prefix="Validating tasks")
            print()
        return results

    def calculate_total_score(self, results):
        total_score = sum(r.score for r in results)
        max_score = sum(r.max_score for r in results)
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        return total_score, max_score, percentage

    def get_category_breakdown(self, task_results):
        breakdown = {}
        for task, result in task_results:
            category = task.category
            if category not in breakdown:
                breakdown[category] = {
                    'total_points': 0, 'earned_points': 0,
                    'tasks': 0, 'passed': 0,
                }
            breakdown[category]['total_points'] += result.max_score
            breakdown[category]['earned_points'] += result.score
            breakdown[category]['tasks'] += 1
            if result.passed:
                breakdown[category]['passed'] += 1
        for category in breakdown:
            total = breakdown[category]['total_points']
            earned = breakdown[category]['earned_points']
            breakdown[category]['percentage'] = (earned / total * 100) if total > 0 else 0
        return breakdown

    def get_domain_breakdown(self, task_results):
        """Get score breakdown by exam domain."""
        breakdown = {}
        for task, result in task_results:
            domain = getattr(task, 'exam_domain', 0)
            domain_name = settings.EXAM_DOMAINS.get(domain, "Unknown")
            if domain not in breakdown:
                breakdown[domain] = {
                    'name': domain_name,
                    'total_points': 0, 'earned_points': 0,
                    'tasks': 0, 'passed': 0,
                }
            breakdown[domain]['total_points'] += result.max_score
            breakdown[domain]['earned_points'] += result.score
            breakdown[domain]['tasks'] += 1
            if result.passed:
                breakdown[domain]['passed'] += 1
        for domain in breakdown:
            total = breakdown[domain]['total_points']
            earned = breakdown[domain]['earned_points']
            breakdown[domain]['percentage'] = (earned / total * 100) if total > 0 else 0
        return breakdown


# Import settings at module level for get_domain_breakdown
from config import settings

# Global validator instance
_validator = None


def get_validator():
    global _validator
    if _validator is None:
        _validator = ValidationEngine()
    return _validator
