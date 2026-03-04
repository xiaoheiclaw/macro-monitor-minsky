"""
Orchestrator Module
==================

System orchestration components.

Modules:
    rules: Rule engine for state determination
    risk_budget: Risk budget calculator
    state_machine: v2 state determination + portfolio action
    data_updater: Data update logic
    cli_formatter: CLI dashboard formatting
    explanation: Explanations, recommendations, triggers
"""

from orchestrator.rules import RuleEngine
from orchestrator.risk_budget import RiskBudgetCalculator
from orchestrator.state_machine import StateMachine
from orchestrator.data_updater import DataUpdater
from orchestrator.cli_formatter import CLIFormatter, make_bar
from orchestrator.explanation import ExplanationBuilder

__all__ = [
    'RuleEngine',
    'RiskBudgetCalculator',
    'StateMachine',
    'DataUpdater',
    'CLIFormatter',
    'ExplanationBuilder',
    'make_bar',
]
