"""
System Orchestrator - 三层系统整合器
=====================================

整合 Structure/Crack/Trend 三层输出，实现：
1. 数据更新功能
2. 固定格式的 Portfolio Action Output (符合 0.3 System Contract)
3. CLI Dashboard 输出

Usage:
    python system_orchestrator.py              # 查看当前状态
    python system_orchestrator.py --update     # 更新数据并查看
    python system_orchestrator.py --json out.json  # 导出 JSON
    python system_orchestrator.py --update-only    # 仅更新数据
"""

import os
import sys
import json
import argparse
import subprocess
import warnings
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

# === Path Setup ===
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Add paths only if not already present
_paths_to_add = [
    PROJECT_ROOT,
    os.path.join(PROJECT_ROOT, 'structure'),
    os.path.join(PROJECT_ROOT, 'structure', 'aggregation', 'ic_return'),
    os.path.join(PROJECT_ROOT, 'crack'),
    os.path.join(PROJECT_ROOT, 'trend'),
]
for _path in _paths_to_add:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# === Constants ===
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


class SystemOrchestrator:
    """三层系统整合器"""

    def __init__(self, use_lagged: bool = True, verbose: bool = True):
        """
        初始化 System Orchestrator

        Args:
            use_lagged: 是否使用滞后数据 (推荐 True)
            verbose: 是否打印详细信息
        """
        self.use_lagged = use_lagged
        self.verbose = verbose
        self.project_root = PROJECT_ROOT

        # 缓存
        self._structure_output = None
        self._crack_output = None
        self._trend_output = None

    # =========================================================================
    # 数据更新
    # =========================================================================

    def update_all_data(self, force: bool = False) -> dict:
        """
        更新所有三层数据

        Args:
            force: 是否强制重新下载

        Returns:
            dict: 更新状态
        """
        results = {}

        print("\n" + "=" * 60)
        print("UPDATING ALL DATA")
        print("=" * 60)

        # 1. Structure 层数据
        print("\n[1/2] Updating Structure layer data...")
        results['structure'] = self.update_structure_data(force=force)

        # 2. Trend 层数据
        print("\n[2/2] Updating Trend layer data...")
        results['trend'] = self.update_trend_data()

        print("\n" + "=" * 60)
        print("UPDATE COMPLETE")
        print("=" * 60)

        return results

    def update_structure_data(self, force: bool = False) -> dict:
        """更新 Structure 层数据 (FRED API)"""
        data_loader_path = os.path.join(
            self.project_root, 'structure', 'data_loader.py'
        )

        if not os.path.exists(data_loader_path):
            return {'status': 'error', 'message': 'data_loader.py not found'}

        try:
            cmd = [sys.executable, data_loader_path]
            if force:
                cmd.append('--refresh')

            result = subprocess.run(
                cmd,
                cwd=os.path.join(self.project_root, 'structure'),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return {'status': 'success', 'message': 'Structure data updated'}
            else:
                return {'status': 'error', 'message': result.stderr[:500]}

        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': 'Timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_trend_data(self) -> dict:
        """更新 Trend 层数据 (Yahoo Finance/FRED)"""
        cache_script = os.path.join(
            self.project_root, 'trend', 'data', 'cache_all_factors.py'
        )

        if not os.path.exists(cache_script):
            return {'status': 'error', 'message': 'cache_all_factors.py not found'}

        try:
            result = subprocess.run(
                [sys.executable, cache_script],
                cwd=os.path.join(self.project_root, 'trend', 'data'),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return {'status': 'success', 'message': 'Trend data updated'}
            else:
                return {'status': 'error', 'message': result.stderr[:500]}

        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': 'Timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    # =========================================================================
    # Structure 层计算
    # =========================================================================

    def compute_structure_output(self) -> dict:
        """
        计算 Structure 层输出 (符合 0.2A schema)

        Returns:
            dict: {
                'date': str,
                'fuel_score': float (0-100),
                'fuel_signal': str,
                'fuel_components': dict,
                'risk_budget': float (0.35-1.15),
                'notes': str,
            }
        """
        if self._structure_output is not None:
            return self._structure_output

        try:
            from data.loader import DataLoader
            from utils.transforms import apply_transforms
            from config import FUEL_WEIGHTS_IC

            # 加载因子
            loader = DataLoader()
            factor_df = loader.load_structure_factors(use_lagged=self.use_lagged)
            if factor_df is None or len(factor_df) == 0:
                return self._empty_structure_output()

            # 应用 transform
            fuel_df = apply_transforms(factor_df, verbose=False)

            # 计算权重 (简化版本，使用预设权重)
            weights = {
                'V1': 0.122,
                'V4': 0.046,
                'V5': 0.313,
                'V7': 0.142,
                'V8': 0.377,
            }

            # 策略：对每个因子取其最新可用数据
            # 这样可以利用所有可用的因子数据，不会因为部分因子缺失而丢失信息
            fuel_score = 0.0
            components = {}
            total_weight = 0.0
            latest_dates = {}

            for factor, weight in weights.items():
                col = f'{factor}_fuel'
                if col not in fuel_df.columns:
                    continue

                # 找该因子的最新非空值
                factor_data = fuel_df[col].dropna()
                if len(factor_data) == 0:
                    continue

                latest_idx = factor_data.index.max()
                value = factor_data.loc[latest_idx]
                contribution = weight * value
                fuel_score += contribution
                total_weight += weight
                latest_dates[factor] = latest_idx

                components[factor] = {
                    'value': float(value),
                    'weight': weight,
                    'contribution': float(contribution),
                    'name': FACTOR_NAMES.get(factor, factor),
                    'date': latest_idx.strftime('%Y-%m-%d') if hasattr(latest_idx, 'strftime') else str(latest_idx),
                }

            if total_weight == 0:
                return self._empty_structure_output()

            # 使用所有因子中最新的日期作为报告日期
            report_date = max(latest_dates.values()) if latest_dates else datetime.now()

            if total_weight > 0:
                fuel_score = fuel_score / total_weight

            # 确定 signal
            fuel_signal = self._get_fuel_signal(fuel_score)

            # 计算 risk_budget
            risk_budget = np.clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)

            # 找主导因子
            dominant = max(components.items(), key=lambda x: x[1]['contribution']) if components else (None, {})
            notes = f"{FACTOR_NAMES.get(dominant[0], dominant[0])} 主导" if dominant[0] else "无数据"

            self._structure_output = {
                'date': report_date.strftime('%Y-%m-%d') if hasattr(report_date, 'strftime') else str(report_date),
                'fuel_score': float(fuel_score),
                'fuel_signal': fuel_signal,
                'fuel_components': components,
                'risk_budget': float(risk_budget),
                'notes': notes,
            }

            return self._structure_output

        except Exception as e:
            if self.verbose:
                print(f"  [Structure] Error: {e}")
            return self._empty_structure_output()

    def _empty_structure_output(self) -> dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'fuel_score': 50.0,
            'fuel_signal': 'NEUTRAL',
            'fuel_components': {},
            'risk_budget': 0.75,
            'notes': 'No data',
        }

    def _get_fuel_signal(self, fuel_score: float) -> str:
        if fuel_score >= 80:
            return 'EXTREME_HIGH'
        elif fuel_score >= 60:
            return 'HIGH'
        elif fuel_score >= 40:
            return 'NEUTRAL'
        elif fuel_score >= 20:
            return 'LOW'
        else:
            return 'EXTREME_LOW'

    # =========================================================================
    # Crack 层计算
    # =========================================================================

    def compute_crack_output(self) -> dict:
        """
        计算 Crack 层输出 (符合 0.2B schema)

        Returns:
            dict: {
                'date': str,
                'crack_score': float (σ),
                'crack_state': str,
                'crack_components': dict,
                'dominant_crack': str,
            }
        """
        if self._crack_output is not None:
            return self._crack_output

        try:
            from core.crack_score import CrackScore

            # 使用新的 CrackScore 模块
            crack = CrackScore()
            result = crack.compute()

            # 转换为 SystemOrchestrator 格式
            components = {}
            dominant = None
            max_contrib = 0

            for factor, info in result.get('factor_breakdown', {}).items():
                # CrackScore returns 'delta_z', map to 'signal' for dashboard
                signal = info.get('delta_z', info.get('signal', 0))
                weight = info.get('weight', 0)
                contribution = info.get('contribution', max(0, signal) * weight)
                components[factor] = {
                    'signal': float(signal),
                    'weight': float(weight),
                    'contribution': float(contribution),
                    'name': FACTOR_NAMES.get(factor, info.get('label', factor)),
                }
                if contribution > max_contrib:
                    max_contrib = contribution
                    dominant = factor

            self._crack_output = {
                'date': str(result.get('date', datetime.now().strftime('%Y-%m-%d'))),
                'crack_score': float(result.get('crack_score', 0)),
                'crack_state': result.get('state', 'STABLE'),
                'crack_components': components,
                'dominant_crack': dominant,
            }

            return self._crack_output

        except Exception as e:
            if self.verbose:
                print(f"  [Crack] Error: {e}")
            return self._empty_crack_output()

    def _empty_crack_output(self) -> dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'crack_score': 0.0,
            'crack_state': 'STABLE',
            'crack_components': {},
            'dominant_crack': None,
        }

    # =========================================================================
    # Trend 层计算
    # =========================================================================

    def compute_trend_output(self) -> dict:
        """
        计算 Trend 层输出 (符合 0.2C schema)

        Returns:
            dict: {
                'date': str,
                'trend_heat': float (0-1),
                'trend_state': str,
                'data_quality': dict,
                'module_heat': dict,
                'factor_intensity': dict,
                'dominant_module': str,
            }
        """
        if self._trend_output is not None:
            return self._trend_output

        try:
            from trend_score.trend_score import TrendScore

            ts = TrendScore()
            result = ts.compute_latest()

            # 提取模块热度
            module_heat = {}
            for mod_name, mod_state in result.get('module_states', {}).items():
                module_heat[mod_name] = float(mod_state.get('heat_score', 0))

            # 数据质量
            data_quality = result.get('data_quality', {
                'coverage_modules': 0,
                'quality_level': 'NONE',
                'confidence': 0.0,
                'is_trustworthy': False,
            })

            self._trend_output = {
                'date': result['date'].strftime('%Y-%m-%d') if hasattr(result.get('date'), 'strftime') else str(result.get('date', '')),
                'trend_heat': float(result.get('trend_heat_score', 0) or 0),
                'trend_state': result.get('trend_state', 'INSUFFICIENT_DATA'),
                'data_quality': data_quality,
                'module_heat': module_heat,
                'factor_intensity': {},  # TODO: 添加因子级别 intensity
                'dominant_module': result.get('trigger_flags', {}).get('dominant_module'),
            }

            return self._trend_output

        except Exception as e:
            if self.verbose:
                print(f"  [Trend] Error: {e}")
            return self._empty_trend_output()

    def _empty_trend_output(self) -> dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trend_heat': 0.0,
            'trend_state': 'INSUFFICIENT_DATA',
            'data_quality': {
                'coverage_modules': 0,
                'quality_level': 'NONE',
                'confidence': 0.0,
                'is_trustworthy': False,
            },
            'module_heat': {},
            'factor_intensity': {},
            'dominant_module': None,
        }

    # =========================================================================
    # Portfolio Action Output
    # =========================================================================

    def compute_portfolio_action(self) -> dict:
        """
        计算最终系统输出 (符合 0.3 System Contract)

        Returns:
            dict: {
                'date': str,
                'system_state': NORMAL/CAUTIOUS/DEFENSIVE/CRISIS,
                'action': HOLD/DE-RISK/HEDGE/EXIT,
                'risk_budget': float,
                'confidence': LOW/MEDIUM/HIGH,
                'reason': list[str],
                'structure': dict,
                'crack': dict,
                'trend': dict,
            }
        """
        # 计算三层输出
        structure = self.compute_structure_output()
        crack = self.compute_crack_output()
        trend = self.compute_trend_output()

        # Risk Budget 公式
        fuel_score = structure['fuel_score']
        risk_budget = np.clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)

        # Quality Gate
        trend_quality = trend['data_quality'].get('quality_level', 'NONE')
        if trend_quality in ['NONE', 'WEAK']:
            confidence = 'LOW'
        elif trend_quality == 'STRONG':
            confidence = 'HIGH'
        else:
            confidence = 'MEDIUM'

        # 状态机判定
        system_state, action, reasons = self._determine_system_state(
            structure, crack, trend, trend_quality
        )

        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'system_state': system_state,
            'action': action,
            'risk_budget': float(risk_budget),
            'confidence': confidence,
            'reason': reasons,
            'structure': structure,
            'crack': crack,
            'trend': trend,
        }

    def _determine_system_state(
        self,
        structure: dict,
        crack: dict,
        trend: dict,
        trend_quality: str
    ) -> Tuple[str, str, List[str]]:
        """
        根据 4.3 决策框架判定系统状态

        升级条件:
        1. Trend quality OK/STRONG (quality gate)
        2. Crack 至少 EARLY_CRACK
        3. Structure Fuel 高位
        """
        reasons = []

        fuel_score = structure['fuel_score']
        crack_state = crack['crack_state']
        trend_state = trend['trend_state']

        # Quality Gate: Trend 必须 OK/STRONG 才能完全升级
        if trend_quality in ['NONE', 'WEAK']:
            reasons.append(f'Trend quality {trend_quality}: 仅作局部参考')
            # 仅使用 Structure + Crack
            if crack_state == 'BREAKING' and fuel_score > 70:
                reasons.append(f'Crack BREAKING + FuelScore {fuel_score:.0f}')
                return 'DEFENSIVE', 'HEDGE', reasons
            elif crack_state in ['WIDENING_CRACK', 'BREAKING'] and fuel_score > 60:
                reasons.append(f'Crack {crack_state} + FuelScore {fuel_score:.0f}')
                return 'CAUTIOUS', 'DE-RISK', reasons
            else:
                reasons.append('无重大风险信号 (Trend 数据不足)')
                return 'NORMAL', 'HOLD', reasons

        # Full escalation (Trend OK/STRONG)
        if trend_state == 'CRITICAL' and crack_state in ['WIDENING_CRACK', 'BREAKING']:
            reasons.append('CRISIS MODE: Trend CRITICAL + Crack 裂缝')
            return 'CRISIS', 'EXIT', reasons

        elif trend_state in ['ALERT', 'CRITICAL'] and fuel_score > 70:
            reasons.append(f'DEFENSIVE: Trend {trend_state} + FuelScore {fuel_score:.0f}')
            return 'DEFENSIVE', 'HEDGE', reasons

        elif fuel_score > 80 and crack_state == 'EARLY_CRACK':
            reasons.append(f'CAUTIOUS: FuelScore {fuel_score:.0f} + Crack {crack_state}')
            return 'CAUTIOUS', 'DE-RISK', reasons

        else:
            reasons.append('NORMAL: 无重大风险信号')
            return 'NORMAL', 'HOLD', reasons

    # =========================================================================
    # Rule Engine v2.0 - 规则引擎升级
    # =========================================================================

    def _get_fuel_state(self, fuel_score: float) -> str:
        """将 FuelScore 映射为离散状态"""
        from config import FUEL_STATE_THRESHOLDS
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

        # Check each condition type
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

    def _apply_rules(
        self,
        fuel_state: str,
        crack_state: str,
        trend_state: str,
        trend_quality: str
    ) -> Tuple[str, str, dict]:
        """
        规则引擎核心：声明式优先级规则

        优先级: Crisis > Defensive > Cautious > Normal

        Returns:
            Tuple[system_state, action, triggered_rule]
        """
        from config import PRIORITY_RULES, FALLBACK_RULES, DEFAULT_RULE

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

    def _compute_risk_budget_v2(
        self,
        fuel_score: float,
        system_state: str,
        crack_state: str,
        trend_state: str,
        trend_quality: str
    ) -> dict:
        """
        分层 Risk Budget 计算

        公式: final = base × state_mult × crack_penalty × trend_penalty

        - base: 由 Fuel 决定的长期上限
        - state_mult: 系统状态对应的削减系数
        - crack_penalty: Crack 状态的额外惩罚
        - trend_penalty: Trend 状态的惩罚 (仅 OK/STRONG 时启用)
        """
        from config import STATE_MULTIPLIERS, CRACK_PENALTIES, TREND_PENALTIES

        # Base (由 Fuel 决定长期上限)
        base = np.clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)

        # State multiplier
        state_mult = STATE_MULTIPLIERS.get(system_state, 1.0)

        # Crack penalty
        crack_penalty = CRACK_PENALTIES.get(crack_state, 1.0)

        # Trend penalty (仅 OK/STRONG 时启用)
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

    def _get_top_contributors(self, layer_output: dict, layer_type: str) -> List[dict]:
        """获取某一层的 top 贡献因子"""
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

        # 按贡献排序
        contributors.sort(key=lambda x: abs(x.get('contribution', 0)), reverse=True)
        return contributors

    def _get_recommendations(
        self,
        system_state: str,
        risk_budget: dict,
        trend_state: str = 'CALM',
        crack_state: str = 'STABLE'
    ) -> List[str]:
        """根据系统状态和当前层状态生成动态建议"""
        final_rb = risk_budget['final_risk_budget']
        recommendations = []

        if system_state == 'CRISIS':
            recommendations = [
                f'立即降低总敞口至 {final_rb:.0%} 以下',
                '激活尾部对冲策略',
                '避免任何新增杠杆',
                '每日监控市场压力指标',
            ]
        elif system_state == 'DEFENSIVE':
            recommendations = [
                f'将总敞口控制在 {final_rb:.0%} 以下',
                '维持尾部对冲',
                '避免新增杠杆',
                '密切关注 Crack 和 Trend 变化',
            ]
        elif system_state == 'CAUTIOUS':
            recommendations = [
                f'建议敞口不超过 {final_rb:.0%}',
                '考虑增加对冲保护',
            ]
            # 根据当前 Trend 状态动态调整建议
            if trend_state == 'CALM':
                recommendations.append('Trend 已处于 CALM，可考虑观察 Crack 改善后逐步增仓')
            else:
                recommendations.append(f'等待 Trend 回到 CALM 再增仓 (当前: {trend_state})')
        else:  # NORMAL
            recommendations = [
                f'可承受敞口上限 {final_rb:.0%}',
                '正常运营，保持监控',
            ]

        return recommendations

    def _get_escalation_triggers(self, current_state: str) -> dict:
        """获取当前状态的升级/降级触发条件"""
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

    def _build_explanation_output(
        self,
        structure: dict,
        crack: dict,
        trend: dict,
        system_state: str,
        action: str,
        triggered_rule: dict,
        risk_budget: dict
    ) -> dict:
        """生成审计友好的解释输出"""

        # Top contributors
        fuel_contributors = self._get_top_contributors(structure, 'fuel')
        crack_contributors = self._get_top_contributors(crack, 'crack')

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

        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'system_state': system_state,
            'risk_budget': risk_budget,
            'triggered_rule': triggered_rule,
            'layer_snapshot': {
                'Fuel': {
                    'score': structure.get('fuel_score', 0),
                    'state': self._get_fuel_state(structure.get('fuel_score', 0)),
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
                'recommendation': self._get_recommendations(
                    system_state,
                    risk_budget,
                    trend_state=trend.get('trend_state', 'CALM'),
                    crack_state=crack.get('crack_state', 'STABLE')
                ),
            },
            'escalation_triggers': self._get_escalation_triggers(system_state),
        }

    def compute_portfolio_action_v2(self, use_hysteresis: bool = False) -> dict:
        """
        v2 规则引擎版本的系统输出

        升级特性:
        1. 8条优先级规则链 (可追溯)
        2. 分层 Risk Budget (base × state × crack × trend)
        3. 审计友好的解释输出

        Args:
            use_hysteresis: 是否启用防抖逻辑 (需要历史状态，暂未实现)

        Returns:
            dict: 包含 system_state, risk_budget, triggered_rule, layer_snapshot 等
        """
        # 计算三层
        structure = self.compute_structure_output()
        crack = self.compute_crack_output()
        trend = self.compute_trend_output()

        # 状态映射
        fuel_state = self._get_fuel_state(structure['fuel_score'])
        crack_state = crack['crack_state']
        trend_state = trend['trend_state']
        trend_quality = trend['data_quality'].get('quality_level', 'NONE')

        # 规则引擎判定
        system_state, action, triggered_rule = self._apply_rules(
            fuel_state, crack_state, trend_state, trend_quality
        )

        # 分层 Risk Budget
        risk_budget = self._compute_risk_budget_v2(
            structure['fuel_score'], system_state,
            crack_state, trend_state, trend_quality
        )

        # 解释输出
        explanation = self._build_explanation_output(
            structure, crack, trend,
            system_state, action, triggered_rule, risk_budget
        )

        # 兼容旧格式字段
        return {
            **explanation,
            'structure': structure,
            'crack': crack,
            'trend': trend,
            # 旧字段兼容
            'confidence': 'HIGH' if trend_quality == 'STRONG' else
                          'MEDIUM' if trend_quality == 'OK' else 'LOW',
            'reason': [triggered_rule['name']],
        }

    def print_dashboard_v2(self):
        """打印 v2 规则引擎版本的 CLI Dashboard"""
        result = self.compute_portfolio_action_v2()

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
        print(f"\n┌─── RISK BUDGET BREAKDOWN {'─' * (width - 28)}┐")
        print(f"│  Base (from Fuel):    {rb['base_from_fuel']:.3f}                                      │")
        print(f"│  × State Multiplier:  {rb['state_multiplier']:.2f}  ({state})                           │")
        print(f"│  × Crack Penalty:     {rb['crack_penalty']:.2f}  ({result['layer_snapshot']['Crack']['state']})                      │")
        print(f"│  × Trend Penalty:     {rb['trend_penalty']:.2f}  ({result['layer_snapshot']['Trend']['state']})                       │")
        print(f"│  ─────────────────────────────────────────────────────────────────────── │")
        print(f"│  = Final Risk Budget: {rb['final_risk_budget']:.3f}                                      │")
        print(f"└{'─' * (width - 2)}┘")

        # Layer Snapshot
        layer = result['layer_snapshot']

        # Fuel
        print(f"\n┌─── FUEL (Structure Layer) {'─' * (width - 29)}┐")
        print(f"│  Score: {layer['Fuel']['score']:.1f} / 100          State: {layer['Fuel']['state']:10s}               │")
        print(f"│  Top Contributors:                                                       │")
        for c in layer['Fuel']['top_contributors'][:3]:
            bar = self._make_bar(c.get('value', 0), 100, 10)
            print(f"│    {c['name'][:15]:<15s}: {c.get('value', 0):5.1f}  {bar}  w={c['weight']:.1%}       │")
        print(f"└{'─' * (width - 2)}┘")

        # Crack
        print(f"\n┌─── CRACK (Margin Layer) {'─' * (width - 27)}┐")
        print(f"│  Score: {layer['Crack']['score_sigma']:.2f}σ              State: {layer['Crack']['state']:15s}          │")
        print(f"│  Top Contributors:                                                       │")
        for c in layer['Crack']['top_contributors'][:3]:
            signal = c.get('signal', 0)
            bar = self._make_bar(abs(signal), 2, 10)
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
                bar = self._make_bar(m['heat'], 1, 10)
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

    # =========================================================================
    # 历史数据
    # =========================================================================

    def compute_history(
        self,
        start_date: str = '2004-01-01',
        end_date: str = None
    ) -> pd.DataFrame:
        """
        计算历史数据用于图表展示

        Returns:
            DataFrame with columns: date, fuel_score, crack_score, trend_heat, system_state
        """
        results = []

        try:
            # Trend 历史
            from trend_score.trend_score import TrendScore
            ts = TrendScore()
            trend_history = ts.compute_history(start_date=start_date, end_date=end_date, freq='D')

            for idx, row in trend_history.iterrows():
                results.append({
                    'date': idx,
                    'trend_heat': row.get('trend_heat_score', np.nan),
                    'trend_state': row.get('trend_state', 'UNKNOWN'),
                })

            df = pd.DataFrame(results)
            df.set_index('date', inplace=True)
            return df

        except Exception as e:
            if self.verbose:
                print(f"  [History] Error: {e}")
            return pd.DataFrame()

    # =========================================================================
    # Dashboard 输出
    # =========================================================================

    def print_dashboard(self):
        """打印 CLI Dashboard"""
        result = self.compute_portfolio_action()

        width = 78

        print("\n" + "=" * width)
        print("                    INDICATOR SYSTEM DASHBOARD")
        print(f"                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * width)

        # 系统状态
        print()
        print("┌" + "─" * (width - 2) + "┐")
        state_line = f"  SYSTEM STATUS: {result['system_state']:<20} Action: {result['action']:<15}"
        print(f"│{state_line:<{width-2}}│")
        budget_line = f"  Risk Budget: {result['risk_budget']:.2f}                        Confidence: {result['confidence']:<10}"
        print(f"│{budget_line:<{width-2}}│")
        print("├" + "─" * (width - 2) + "┤")
        reason_line = f"  Reason: {'; '.join(result['reason'][:2])}"
        print(f"│{reason_line[:width-2]:<{width-2}}│")
        print("└" + "─" * (width - 2) + "┘")

        # Structure 层
        structure = result['structure']
        print()
        print("┌─── STRUCTURE (FuelScore) " + "─" * (width - 28) + "┐")
        fuel_line = f"  FuelScore: {structure['fuel_score']:.1f} / 100                     Signal: {structure['fuel_signal']:<15}"
        print(f"│{fuel_line:<{width-2}}│")
        budget_line = f"  Risk Budget: {structure['risk_budget']:.2f}                        Date: {structure['date']}"
        print(f"│{budget_line:<{width-2}}│")
        print(f"│  {'─' * (width - 6)} │")
        print(f"│  {'Components:':<{width-4}}│")

        for factor, info in sorted(structure['fuel_components'].items(), key=lambda x: -x[1]['weight']):
            bar = self._make_bar(info['value'], 100, 10)
            line = f"    {factor} ({info['name'][:12]:<12}): {info['value']:5.1f}  {bar}  {info['weight']*100:4.1f}%"
            print(f"│{line:<{width-2}}│")

        print("└" + "─" * (width - 2) + "┘")

        # Crack 层
        crack = result['crack']
        print()
        print("┌─── CRACK (CrackScore) " + "─" * (width - 25) + "┐")
        crack_line = f"  CrackScore: {crack['crack_score']:.2f} σ                        State: {crack['crack_state']:<15}"
        print(f"│{crack_line:<{width-2}}│")
        dom_line = f"  Dominant: {crack['dominant_crack'] or 'N/A':<20}          Date: {crack['date']}"
        print(f"│{dom_line:<{width-2}}│")
        print(f"│  {'─' * (width - 6)} │")
        print(f"│  {'Components:':<{width-4}}│")

        for factor, info in sorted(crack['crack_components'].items(), key=lambda x: -x[1]['weight']):
            bar = self._make_bar(max(0, info['signal']), 2.0, 10)
            line = f"    {factor} ({info['name'][:12]:<12}): {info['signal']:+5.2f}σ {bar}  {info['weight']*100:4.1f}%"
            print(f"│{line:<{width-2}}│")

        print("└" + "─" * (width - 2) + "┘")

        # Trend 层
        trend = result['trend']
        print()
        print("┌─── TREND (TrendScore) " + "─" * (width - 25) + "┐")
        trend_line = f"  TrendScore: {trend['trend_heat']:.2f}                           State: {trend['trend_state']:<15}"
        print(f"│{trend_line:<{width-2}}│")
        quality = trend['data_quality']
        qual_line = f"  Quality: {quality.get('quality_level', 'NONE')} ({quality.get('coverage_modules', 0)}/4 modules)        Date: {trend['date']}"
        print(f"│{qual_line:<{width-2}}│")
        print(f"│  {'─' * (width - 6)} │")
        print(f"│  {'Modules:':<{width-4}}│")

        for mod, heat in sorted(trend['module_heat'].items()):
            bar = self._make_bar(heat, 1.0, 10)
            mod_name = MODULE_NAMES.get(mod, mod)
            # 确定模块状态
            mod_state = 'CALM' if heat < 0.3 else 'WATCH' if heat < 0.6 else 'ALERT' if heat < 0.8 else 'CRITICAL'
            line = f"    {mod} ({mod_name:<10}): {heat:.2f}  {bar}  {mod_state}"
            print(f"│{line:<{width-2}}│")

        print("└" + "─" * (width - 2) + "┘")

        print()
        print("=" * width)

    def _make_bar(self, value: float, max_val: float, width: int = 10) -> str:
        """生成进度条"""
        ratio = min(1.0, max(0.0, value / max_val))
        filled = int(ratio * width)
        return "[" + "█" * filled + "░" * (width - filled) + "]"

    # =========================================================================
    # JSON 导出
    # =========================================================================

    def export_json(self, filepath: str):
        """导出 JSON 格式报告"""
        result = self.compute_portfolio_action()

        # 转换 numpy 类型
        def convert(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.Timestamp):
                return obj.strftime('%Y-%m-%d')
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj

        result = convert(result)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Exported to: {filepath}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Indicator System Orchestrator')
    parser.add_argument('--update', action='store_true', help='Update data before showing dashboard')
    parser.add_argument('--update-only', action='store_true', help='Only update data, do not show dashboard')
    parser.add_argument('--json', type=str, help='Export to JSON file')
    parser.add_argument('--raw', action='store_true', help='Use raw data instead of lagged')

    args = parser.parse_args()

    orch = SystemOrchestrator(use_lagged=not args.raw)

    if args.update or args.update_only:
        orch.update_all_data()

    if args.update_only:
        return

    if args.json:
        orch.export_json(args.json)
    else:
        orch.print_dashboard()


if __name__ == '__main__':
    main()
