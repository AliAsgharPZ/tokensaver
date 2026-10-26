from types import ModuleType

import pytest

from tokensaver.optimizer.base import apply_edits


def run_rule(rule: ModuleType, text: str) -> str:
    """Apply every edit a rule suggests and return the new text."""
    edits = [edit for s in rule.find(text) for edit in s.edits]
    return apply_edits(text, edits)


@pytest.fixture
def apply_rule():
    return run_rule
