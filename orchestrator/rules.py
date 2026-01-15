"""
Rule Engine v2.0
================

Declarative rule engine for system state determination.

Usage:
    from orchestrator.rules import RuleEngine

    engine = RuleEngine()
    state, action, rule_info = engine.apply_rules(fuel_state, crack_state, trend_state, trend_quality)
"""

from typing import Tuple

from config import (
    FUEL_STATE_THRESHOLDS,
    PRIORITY_RULES,
    FALLBACK_RULES,
    DEFAULT_RULE,
)


class RuleEngine:
    """Declarative rule engine for system state determination."""

    def get_fuel_state(self, fuel_score: float) -> str:
        """Map FuelScore to discrete state."""
        if fuel_score < FUEL_STATE_THRESHOLDS['LOW']:
            return 'LOW'
        elif fuel_score < FUEL_STATE_THRESHOLDS['NEUTRAL']:
            return 'NEUTRAL'
        elif fuel_score < FUEL_STATE_THRESHOLDS['HIGH']:
            return 'HIGH'
        else:
            return 'EXTREME'

    def _match_rule(
        self,
        rule: dict,
        fuel_state: str,
        crack_state: str,
        trend_state: str,
        trend_quality: str
    ) -> bool:
        """Check if a rule's conditions match the current states."""
        conditions = rule.get('conditions', {})

        if 'fuel_states' in conditions and fuel_state not in conditions['fuel_states']:
            return False
        if 'crack_states' in conditions and crack_state not in conditions['crack_states']:
            return False
        if 'trend_states' in conditions and trend_state not in conditions['trend_states']:
            return False
        if 'trend_qualities' in conditions and trend_quality not in conditions['trend_qualities']:
            return False

        return True

    def _build_rationale(
        self,
        rule: dict,
        fuel_state: str,
        crack_state: str,
        trend_state: str
    ) -> str:
        """Build human-readable rationale for triggered rule."""
        rule_id = rule['id']
        rationale_templates = {
            'R1': f'市场极度承压(Trend={trend_state}) + 结构裂缝扩大(Crack={crack_state})',
            'R2': f'结构已崩裂(Crack={crack_state})，Trend确认压力(Trend={trend_state})',
            'R3': f'结构裂缝扩大(Crack={crack_state}) + 市场转坏(Trend={trend_state})',
            'R4': f'高燃料存量(Fuel={fuel_state}) + 市场点火(Trend={trend_state})',
            'R5': f'高燃料存量(Fuel={fuel_state})，但未点火(Crack={crack_state})',
            'R6': f'结构出现早期裂纹(Crack={crack_state})，需要关注',
            'R7': f'低燃料(Fuel={fuel_state}) + 稳定结构(Crack={crack_state}) + 平静市场(Trend={trend_state})',
            'R8a': 'Trend数据不足，但Crack已崩裂',
            'R8b': 'Trend数据不足，但Crack裂缝扩大',
            'R8c': 'Trend数据不足，Crack出现早期裂纹',
            'R8d': 'Trend数据不足，但Fuel极高',
            'R8e': 'Trend数据不足，但Fuel较高',
            'R8f': 'Trend数据不足，Fuel/Crack正常',
            'R0': f'Fuel={fuel_state}, Crack={crack_state}, Trend={trend_state}',
        }
        return rationale_templates.get(rule_id, f'Rule {rule_id} triggered')

    def apply_rules(
        self,
        fuel_state: str,
        crack_state: str,
        trend_state: str,
        trend_quality: str
    ) -> Tuple[str, str, dict]:
        """
        Apply declarative priority rules.

        Priority: Crisis > Defensive > Cautious > Normal

        Args:
            fuel_state: LOW/NEUTRAL/HIGH/EXTREME
            crack_state: STABLE/EARLY_CRACK/WIDENING_CRACK/BREAKING
            trend_state: CALM/WATCH/ALERT/CRITICAL
            trend_quality: NONE/WEAK/OK/STRONG

        Returns:
            Tuple[system_state, action, triggered_rule_info]
        """
        # Check fallback first if trend quality is poor
        if trend_quality in ['WEAK', 'NONE']:
            for rule in FALLBACK_RULES:
                if self._match_rule(rule, fuel_state, crack_state, trend_state, trend_quality):
                    return rule['state'], rule['action'], {
                        'rule_id': rule['id'],
                        'name': rule['name'],
                        'rationale': self._build_rationale(rule, fuel_state, crack_state, trend_state),
                    }
            # Fallback default
            return 'NORMAL', 'HOLD', {
                'rule_id': 'R8f',
                'name': 'Fallback: Normal',
                'rationale': self._build_rationale({'id': 'R8f'}, fuel_state, crack_state, trend_state),
            }

        # Check priority rules in order
        for rule in PRIORITY_RULES:
            if self._match_rule(rule, fuel_state, crack_state, trend_state, trend_quality):
                return rule['state'], rule['action'], {
                    'rule_id': rule['id'],
                    'name': rule['name'],
                    'rationale': self._build_rationale(rule, fuel_state, crack_state, trend_state),
                }

        # Default rule
        return DEFAULT_RULE['state'], DEFAULT_RULE['action'], {
            'rule_id': DEFAULT_RULE['id'],
            'name': DEFAULT_RULE['name'],
            'rationale': self._build_rationale(DEFAULT_RULE, fuel_state, crack_state, trend_state),
        }
