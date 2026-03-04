"""
State Machine v2
================

System state determination via rule engine + risk budget,
and the v2 portfolio action computation.

Usage:
    from orchestrator.state_machine import StateMachine

    sm = StateMachine()
    result = sm.compute_portfolio_action(structure, crack, trend)
"""

from datetime import datetime
from typing import Dict

from orchestrator.rules import RuleEngine
from orchestrator.risk_budget import RiskBudgetCalculator
from orchestrator.explanation import ExplanationBuilder


class StateMachine:
    """
    v2 state machine: rule engine + layered risk budget + explanation.

    Replaces the old _determine_system_state() with a declarative,
    auditable approach.
    """

    def __init__(self):
        self._rule_engine = RuleEngine()
        self._risk_calc = RiskBudgetCalculator()
        self._explanation = ExplanationBuilder()

    # -- delegate helpers (kept for backward compat in thin wrapper) ----------

    def get_fuel_state(self, fuel_score: float) -> str:
        """Map FuelScore to discrete state."""
        return self._rule_engine.get_fuel_state(fuel_score)

    def apply_rules(self, fuel_state, crack_state, trend_state, trend_quality):
        """Delegate to RuleEngine."""
        return self._rule_engine.apply_rules(fuel_state, crack_state, trend_state, trend_quality)

    def compute_risk_budget(self, fuel_score, system_state, crack_state, trend_state, trend_quality) -> dict:
        """Delegate to RiskBudgetCalculator."""
        return self._risk_calc.compute(fuel_score, system_state, crack_state, trend_state, trend_quality)

    # -- main entry point ----------------------------------------------------

    def compute_portfolio_action(
        self,
        structure: dict,
        crack: dict,
        trend: dict,
        use_hysteresis: bool = False,
    ) -> dict:
        """
        Compute v2 portfolio action output.

        Features:
        1. 8-rule priority chain (auditable)
        2. Layered risk budget (base × state × crack × trend)
        3. Audit-friendly explanation output

        Args:
            structure: Structure layer output
            crack: Crack layer output
            trend: Trend layer output
            use_hysteresis: Enable debounce logic (not yet implemented)

        Returns:
            dict with system_state, risk_budget, triggered_rule,
            layer_snapshot, action, escalation_triggers, plus
            backward-compatible fields (confidence, reason, structure, crack, trend).
        """
        # State mapping
        fuel_state = self._rule_engine.get_fuel_state(structure['fuel_score'])
        crack_state = crack['crack_state']
        trend_state = trend['trend_state']
        trend_quality = trend['data_quality'].get('quality_level', 'NONE')

        # Rule engine
        system_state, action, triggered_rule = self._rule_engine.apply_rules(
            fuel_state, crack_state, trend_state, trend_quality
        )

        # Layered risk budget
        risk_budget = self._risk_calc.compute(
            structure['fuel_score'], system_state,
            crack_state, trend_state, trend_quality
        )

        # Explanation
        explanation = self._explanation.build(
            structure, crack, trend,
            system_state, action, triggered_rule, risk_budget
        )

        # Backward-compatible fields
        confidence = (
            'HIGH' if trend_quality == 'STRONG'
            else 'MEDIUM' if trend_quality == 'OK'
            else 'LOW'
        )

        return {
            **explanation,
            'structure': structure,
            'crack': crack,
            'trend': trend,
            'confidence': confidence,
            'reason': [triggered_rule['name']],
        }
