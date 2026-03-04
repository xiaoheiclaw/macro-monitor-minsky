"""
Explanation Module
==================

Generates human-readable explanations, recommendations,
escalation triggers, and contributor analysis.

Usage:
    from orchestrator.explanation import ExplanationBuilder

    builder = ExplanationBuilder()
    explanation = builder.build(structure, crack, trend, system_state, action, triggered_rule, risk_budget)
"""

from typing import Dict, List

import numpy as np

from orchestrator.rules import RuleEngine

# Display names
FACTOR_NAMES = {
    'V1': 'ST Debt',
    'V2': 'Uninsured Deposits',
    'V4': 'Interest Coverage',
    'V5': 'TDSP',
    'V7': 'CAPE',
    'V8': 'Margin Debt',
}

MODULE_NAMES = {
    'A': 'Volatility',
    'B': 'Funding',
    'C': 'Credit',
    'D': 'Flow',
}


class ExplanationBuilder:
    """Builds audit-friendly explanation outputs."""

    def __init__(self):
        self._rule_engine = RuleEngine()

    def get_top_contributors(self, layer_output: dict, layer_type: str) -> List[dict]:
        """
        Get top contributing factors from a layer.

        Args:
            layer_output: Layer output dict
            layer_type: 'fuel' or 'crack'

        Returns:
            List of contributor dicts, sorted by abs(contribution) descending
        """
        contributors = []

        if layer_type == 'fuel':
            breakdown = layer_output.get('fuel_components', {})
            for factor, data in breakdown.items():
                if isinstance(data, dict):
                    contributors.append({
                        'factor': factor,
                        'name': data.get('name', factor),
                        'value': data.get('value', 0),
                        'weight': data.get('weight', 0),
                        'contribution': data.get('contribution', 0),
                    })
        elif layer_type == 'crack':
            breakdown = layer_output.get('crack_components', {})
            for factor, data in breakdown.items():
                if isinstance(data, dict):
                    contributors.append({
                        'factor': factor,
                        'name': data.get('name', factor),
                        'signal': data.get('signal', 0),
                        'weight': data.get('weight', 0),
                        'contribution': data.get('contribution', 0),
                    })

        contributors.sort(key=lambda x: abs(x.get('contribution', 0)), reverse=True)
        return contributors

    def get_recommendations(
        self,
        system_state: str,
        risk_budget: dict,
        trend_state: str = 'CALM',
        crack_state: str = 'STABLE',
    ) -> List[str]:
        """Generate dynamic recommendations based on system state."""
        final_rb = risk_budget['final_risk_budget']

        if system_state == 'CRISIS':
            return [
                f'立即降低总敞口至 {final_rb:.0%} 以下',
                '激活尾部对冲策略',
                '避免任何新增杠杆',
                '每日监控市场压力指标',
            ]
        elif system_state == 'DEFENSIVE':
            return [
                f'将总敞口控制在 {final_rb:.0%} 以下',
                '维持尾部对冲',
                '避免新增杠杆',
                '密切关注 Crack 和 Trend 变化',
            ]
        elif system_state == 'CAUTIOUS':
            recs = [
                f'建议敞口不超过 {final_rb:.0%}',
                '考虑增加对冲保护',
            ]
            if trend_state == 'CALM':
                recs.append('Trend 已处于 CALM，可考虑观察 Crack 改善后逐步增仓')
            else:
                recs.append(f'等待 Trend 回到 CALM 再增仓 (当前: {trend_state})')
            return recs
        else:  # NORMAL
            return [
                f'可承受敞口上限 {final_rb:.0%}',
                '正常运营，保持监控',
            ]

    def get_escalation_triggers(self, current_state: str) -> dict:
        """Get upgrade/downgrade trigger conditions for current state."""
        triggers = {
            'to_crisis_if': [],
            'to_defensive_if': [],
            'to_cautious_if': [],
            'downgrade_rules': [],
        }

        if current_state == 'NORMAL':
            triggers['to_cautious_if'] = [
                'FuelState >= HIGH',
                'CrackState >= EARLY_CRACK',
            ]
            triggers['to_defensive_if'] = [
                'TrendState >= ALERT (quality OK/STRONG) + FuelState = EXTREME',
                'CrackState = WIDENING_CRACK + TrendState >= WATCH',
            ]
            triggers['to_crisis_if'] = [
                'TrendState = CRITICAL + CrackState >= WIDENING_CRACK',
                'CrackState = BREAKING + TrendState >= ALERT',
            ]
        elif current_state == 'CAUTIOUS':
            triggers['to_defensive_if'] = [
                'TrendState >= ALERT (quality OK/STRONG) + FuelState = EXTREME',
                'CrackState = WIDENING_CRACK + TrendState >= WATCH',
            ]
            triggers['to_crisis_if'] = [
                'TrendState = CRITICAL + CrackState >= WIDENING_CRACK',
                'CrackState = BREAKING + TrendState >= ALERT',
            ]
            triggers['downgrade_rules'] = [
                'FuelState <= NEUTRAL 且 CrackState = STABLE (连续2个月)',
            ]
        elif current_state == 'DEFENSIVE':
            triggers['to_crisis_if'] = [
                'TrendState = CRITICAL + CrackState >= WIDENING_CRACK',
                'CrackState = BREAKING + TrendState >= ALERT',
            ]
            triggers['downgrade_rules'] = [
                'TrendState <= WATCH (连续10个交易日)',
                'CrackState <= EARLY_CRACK (连续2个月)',
            ]
        elif current_state == 'CRISIS':
            triggers['downgrade_rules'] = [
                'TrendState = CALM (连续20个交易日)',
                'CrackState <= EARLY_CRACK (连续2个月)',
            ]

        return triggers

    def build(
        self,
        structure: dict,
        crack: dict,
        trend: dict,
        system_state: str,
        action: str,
        triggered_rule: dict,
        risk_budget: dict,
    ) -> dict:
        """
        Build full audit-friendly explanation output.

        Returns:
            dict with system_state, risk_budget, triggered_rule,
            layer_snapshot, action, escalation_triggers
        """
        # Top contributors
        fuel_contributors = self.get_top_contributors(structure, 'fuel')
        crack_contributors = self.get_top_contributors(crack, 'crack')

        # Trend top modules
        module_heat = trend.get('module_heat', {})
        trend_modules = []
        for module, heat in module_heat.items():
            if heat is not None and not np.isnan(heat):
                trend_modules.append({
                    'module': module,
                    'name': MODULE_NAMES.get(module, module),
                    'heat': heat,
                })
        trend_modules.sort(key=lambda x: x['heat'], reverse=True)

        from datetime import datetime

        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'system_state': system_state,
            'risk_budget': risk_budget,
            'triggered_rule': triggered_rule,
            'layer_snapshot': {
                'Fuel': {
                    'score': structure.get('fuel_score', 0),
                    'state': self._rule_engine.get_fuel_state(structure.get('fuel_score', 0)),
                    'top_contributors': fuel_contributors[:3],
                },
                'Crack': {
                    'score_sigma': crack.get('crack_score', 0),
                    'state': crack.get('crack_state', 'UNKNOWN'),
                    'top_contributors': crack_contributors[:3],
                },
                'Trend': {
                    'heat_score': trend.get('trend_heat', 0),
                    'state': trend.get('trend_state', 'UNKNOWN'),
                    'data_quality': trend.get('data_quality', {}),
                    'top_modules': trend_modules[:2],
                },
            },
            'action': {
                'posture': action,
                'recommendation': self.get_recommendations(
                    system_state,
                    risk_budget,
                    trend_state=trend.get('trend_state', 'CALM'),
                    crack_state=crack.get('crack_state', 'STABLE'),
                ),
            },
            'escalation_triggers': self.get_escalation_triggers(system_state),
        }
