"""
Risk Budget Calculator
=====================

Layered risk budget calculation.

Usage:
    from orchestrator.risk_budget import RiskBudgetCalculator

    calc = RiskBudgetCalculator()
    budget = calc.compute(fuel_score, system_state, crack_state, trend_state, trend_quality)
"""

import numpy as np

from config import STATE_MULTIPLIERS, CRACK_PENALTIES, TREND_PENALTIES


class RiskBudgetCalculator:
    """Layered risk budget calculator."""

    def compute(
        self,
        fuel_score: float,
        system_state: str,
        crack_state: str,
        trend_state: str,
        trend_quality: str
    ) -> dict:
        """
        Compute layered risk budget.

        Formula: final = base × state_mult × crack_penalty × trend_penalty

        Args:
            fuel_score: 0-100 FuelScore
            system_state: NORMAL/CAUTIOUS/DEFENSIVE/CRISIS
            crack_state: STABLE/EARLY_CRACK/WIDENING_CRACK/BREAKING
            trend_state: CALM/WATCH/ALERT/CRITICAL
            trend_quality: NONE/WEAK/OK/STRONG

        Returns:
            dict with budget breakdown
        """
        # Base (determined by Fuel)
        base = np.clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)

        # State multiplier
        state_mult = STATE_MULTIPLIERS.get(system_state, 1.0)

        # Crack penalty
        crack_penalty = CRACK_PENALTIES.get(crack_state, 1.0)

        # Trend penalty (only when trend quality is OK/STRONG)
        if trend_quality in ['OK', 'STRONG']:
            trend_penalty = TREND_PENALTIES.get(trend_state, 1.0)
        else:
            trend_penalty = 1.0

        # Final
        final = np.clip(base * state_mult * crack_penalty * trend_penalty, 0.0, 1.15)

        return {
            'base_from_fuel': round(base, 3),
            'state_multiplier': state_mult,
            'crack_penalty': crack_penalty,
            'trend_penalty': trend_penalty,
            'final_risk_budget': round(final, 3),
        }

    def compute_simple(self, fuel_score: float) -> float:
        """
        Simple risk budget calculation (v1 formula).

        Formula: clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)
        """
        return float(np.clip(1.1 - 0.007 * fuel_score, 0.35, 1.15))
