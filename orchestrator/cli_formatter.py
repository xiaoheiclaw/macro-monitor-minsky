"""
CLI Formatter
=============

CLI dashboard formatting for the indicator system.

Usage:
    from orchestrator.cli_formatter import CLIFormatter

    formatter = CLIFormatter()
    formatter.print_dashboard_v2(result)
"""

from datetime import datetime
from typing import Dict

# Display name mappings
MODULE_NAMES = {
    'A': 'Volatility',
    'B': 'Funding',
    'C': 'Credit',
    'D': 'Flow',
}


def make_bar(value: float, max_val: float, width: int = 10) -> str:
    """Generate a text progress bar."""
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


class CLIFormatter:
    """CLI dashboard formatting."""

    @staticmethod
    def print_dashboard_v2(result: dict) -> None:
        """
        Print the v2 rule-engine dashboard to stdout.

        Args:
            result: Output from StateMachine.compute_portfolio_action()
        """
        width = 78

        print("\n" + "=" * width)
        print("                    INDICATOR SYSTEM DASHBOARD v2.0")
        print(f"                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * width)

        # System Status Box
        state = result['system_state']
        action = result['action']['posture']
        rb = result['risk_budget']
        rule = result['triggered_rule']

        state_colors = {
            'NORMAL': '\033[92m',     # Green
            'CAUTIOUS': '\033[93m',   # Yellow
            'DEFENSIVE': '\033[91m',  # Red
            'CRISIS': '\033[95m',     # Magenta
        }
        reset = '\033[0m'
        color = state_colors.get(state, '')

        print(f"\n┌{'─' * (width - 2)}┐")
        print(f"│  SYSTEM STATUS: {color}{state:12s}{reset}    Action: {action:12s}              │")
        print(f"│  Risk Budget: {rb['final_risk_budget']:.2f}              Confidence: {result['confidence']:8s}          │")
        print(f"├{'─' * (width - 2)}┤")
        print(f"│  Rule: [{rule['rule_id']}] {rule['name'][:55]:<55s} │")
        print(f"└{'─' * (width - 2)}┘")

        # Risk Budget Breakdown
        layer = result['layer_snapshot']
        print(f"\n┌─── RISK BUDGET BREAKDOWN {'─' * (width - 28)}┐")
        print(f"│  Base (from Fuel):    {rb['base_from_fuel']:.3f}                                      │")
        print(f"│  × State Multiplier:  {rb['state_multiplier']:.2f}  ({state})                           │")
        print(f"│  × Crack Penalty:     {rb['crack_penalty']:.2f}  ({layer['Crack']['state']})                      │")
        print(f"│  × Trend Penalty:     {rb['trend_penalty']:.2f}  ({layer['Trend']['state']})                       │")
        print(f"│  ─────────────────────────────────────────────────────────────────────── │")
        print(f"│  = Final Risk Budget: {rb['final_risk_budget']:.3f}                                      │")
        print(f"└{'─' * (width - 2)}┘")

        # Fuel
        print(f"\n┌─── FUEL (Structure Layer) {'─' * (width - 29)}┐")
        print(f"│  Score: {layer['Fuel']['score']:.1f} / 100          State: {layer['Fuel']['state']:10s}               │")
        print(f"│  Top Contributors:                                                       │")
        for c in layer['Fuel']['top_contributors'][:3]:
            bar = make_bar(c.get('value', 0), 100, 10)
            print(f"│    {c['name'][:15]:<15s}: {c.get('value', 0):5.1f}  {bar}  w={c['weight']:.1%}       │")
        print(f"└{'─' * (width - 2)}┘")

        # Crack
        print(f"\n┌─── CRACK (Margin Layer) {'─' * (width - 27)}┐")
        print(f"│  Score: {layer['Crack']['score_sigma']:.2f}σ              State: {layer['Crack']['state']:15s}          │")
        print(f"│  Top Contributors:                                                       │")
        for c in layer['Crack']['top_contributors'][:3]:
            signal = c.get('signal', 0)
            bar = make_bar(abs(signal), 2, 10)
            print(f"│    {c.get('name', c['factor'])[:15]:<15s}: ΔZ={signal:+.2f}σ {bar}  w={c['weight']:.1%}    │")
        print(f"└{'─' * (width - 2)}┘")

        # Trend
        dq = layer['Trend']['data_quality']
        print(f"\n┌─── TREND (Market Layer) {'─' * (width - 27)}┐")
        print(f"│  Heat: {layer['Trend']['heat_score']:.3f}               State: {layer['Trend']['state']:15s}          │")
        print(f"│  Quality: {dq.get('quality_level', 'N/A'):8s}  Coverage: {dq.get('coverage_modules', 0)}/4 modules              │")
        if layer['Trend']['top_modules']:
            print(f"│  Top Modules:                                                            │")
            for m in layer['Trend']['top_modules'][:2]:
                bar = make_bar(m['heat'], 1, 10)
                print(f"│    {m['name'][:15]:<15s}: {m['heat']:.3f}  {bar}                           │")
        print(f"└{'─' * (width - 2)}┘")

        # Recommendations
        print(f"\n┌─── RECOMMENDATIONS {'─' * (width - 22)}┐")
        for rec in result['action']['recommendation'][:4]:
            print(f"│  • {rec[:70]:<70s} │")
        print(f"└{'─' * (width - 2)}┘")

        # Escalation Triggers
        triggers = result['escalation_triggers']
        if any([triggers['to_crisis_if'], triggers['to_defensive_if'], triggers['downgrade_rules']]):
            print(f"\n┌─── ESCALATION TRIGGERS {'─' * (width - 26)}┐")
            if triggers['to_crisis_if']:
                print(f"│  To CRISIS if:                                                          │")
                for t in triggers['to_crisis_if'][:2]:
                    print(f"│    - {t[:68]:<68s} │")
            if triggers['to_defensive_if']:
                print(f"│  To DEFENSIVE if:                                                       │")
                for t in triggers['to_defensive_if'][:2]:
                    print(f"│    - {t[:68]:<68s} │")
            if triggers['downgrade_rules']:
                print(f"│  Downgrade if:                                                          │")
                for t in triggers['downgrade_rules'][:2]:
                    print(f"│    - {t[:68]:<68s} │")
            print(f"└{'─' * (width - 2)}┘")

        print()
