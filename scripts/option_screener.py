#!/usr/bin/env python3
"""
Wheel Strategy 期权自动化筛选脚本
根据量化标准自动扫描符合条件的期权合约
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from math import log, sqrt, exp
from scipy.stats import norm


@dataclass
class OptionContract:
    """期权合约数据结构"""
    symbol: str
    strike: float
    expiry_date: str
    option_type: str  # 'PUT' or 'CALL'
    price: float
    iv: float
    volume: int
    stock_price: float
    days_to_expiry: int
    risk_free_rate: float = 0.0368  # 无风险利率，默认 3.68%

    @property
    def otm_pct(self) -> float:
        """计算OTM百分比"""
        if self.option_type == 'PUT':
            return (self.stock_price - self.strike) / self.stock_price * 100
        else:  # CALL
            return (self.strike - self.stock_price) / self.stock_price * 100

    @property
    def is_otm(self) -> bool:
        """判断是否为虚值期权"""
        if self.option_type == 'PUT':
            return self.strike < self.stock_price
        else:  # CALL
            return self.strike > self.stock_price

    @property
    def roi(self) -> float:
        """计算单合约ROI"""
        return self.price / self.strike * 100

    @property
    def annualized_roi(self) -> float:
        """计算年化ROI"""
        if self.days_to_expiry <= 0:
            return 0
        return self.roi / (self.days_to_expiry / 365)

    @property
    def probability_not_exercised(self) -> str:
        """基于 Black-Scholes 模型的不被行权概率

        使用标准的期权定价模型计算：
        - PUT 不被行权概率 = N(d2)（股价保持在行权价之上的概率）
        - CALL 不被行权概率 = N(-d2)（股价保持在行权价之下的概率）

        d2 = [ln(S/K) + (r - σ²/2)T] / (σ√T)

        其中：
        - S: 标的资产价格
        - K: 行权价
        - r: 无风险利率
        - σ: 波动率（IV）
        - T: 到期时间（年）
        """
        if not self.is_otm:
            return "<50%"

        S = self.stock_price
        K = self.strike
        T = self.days_to_expiry / 365.0
        sigma = self.iv / 100.0
        r = self.risk_free_rate

        if T <= 0 or sigma <= 0:
            return "<50%"

        try:
            # 计算 d2
            d2 = (log(S / K) + (r - sigma**2 / 2) * T) / (sigma * sqrt(T))

            # 计算不被行权概率
            if self.option_type == 'PUT':
                prob = norm.cdf(d2)   # PUT 不被行权概率（股价 > 行权价）
            else:
                prob = norm.cdf(-d2)  # CALL 不被行权概率（股价 < 行权价）

            # 转换为百分比，保留1位小数
            prob_pct = prob * 100
            return f"{prob_pct:.1f}%"
        except (ValueError, ZeroDivisionError):
            return "<50%"


class OptionScreener:
    """期权筛选器"""

    def __init__(self, risk_free_rate: float = 0.0368):
        """
        Args:
            risk_free_rate: 无风险利率（年化），默认 3.68%
        """
        self.risk_free_rate = risk_free_rate

        # 筛选标准
        self.criteria = {
            'iv_min': 30.0,  # IV最小值 (%)
            'volume_min': 500,  # 最小成交量（张）
            'days_max': 45,  # 最大到期天数
            'days_min': 0,  # 最小到期天数
            'roi_min': 2.0,  # 最小单合约ROI (%)
            'annualized_roi_min': 30.0,  # 最小年化ROI (%)
            'put_probability_min': 60.0,  # PUT不被行权最小概率
            'call_probability_min': 70.0,  # CALL不被行权最小概率
        }

    def get_stock_price(self, symbol: str) -> Optional[float]:
        """获取股票当前价格"""
        try:
            result = subprocess.run(
                ['longbridge', 'quote', symbol, '--format', 'json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    return float(data[0].get('last', 0))
        except Exception as e:
            print(f"⚠️  获取{symbol}价格失败: {e}", file=sys.stderr)
        return None

    def get_option_chain(self, symbol: str, expiry_date: str) -> List[Dict]:
        """获取期权链数据"""
        try:
            result = subprocess.run(
                ['longbridge', 'option', 'chain', symbol,
                 '--date', expiry_date, '--format', 'json'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                return data if data else []
        except Exception as e:
            print(f"⚠️  获取{symbol}期权链失败: {e}", file=sys.stderr)
        return []

    def calculate_days_to_expiry(self, expiry_date: str) -> int:
        """计算距到期天数"""
        try:
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
            today = datetime.now()
            return (expiry - today).days
        except:
            return 0

    def screen_puts(self, symbol: str, expiry_date: str,
                   stock_price: float) -> List[OptionContract]:
        """筛选PUT期权"""
        options = []
        chain_data = self.get_option_chain(symbol, expiry_date)

        days = self.calculate_days_to_expiry(expiry_date)

        for item in chain_data:
            try:
                strike = float(item.get('strike', 0))
                put_price = float(item.get('put_last', 0))
                put_iv = float(item.get('put_iv', 0)) * 100
                put_vol = int(item.get('put_vol', 0))

                if strike <= 0 or put_price <= 0 or put_vol <= 0:
                    continue

                contract = OptionContract(
                    symbol=symbol,
                    strike=strike,
                    expiry_date=expiry_date,
                    option_type='PUT',
                    price=put_price,
                    iv=put_iv,
                    volume=put_vol,
                    stock_price=stock_price,
                    days_to_expiry=days,
                    risk_free_rate=self.risk_free_rate
                )

                # 应用筛选条件
                if self._meets_criteria(contract, option_type='PUT'):
                    options.append(contract)

            except (ValueError, KeyError) as e:
                continue

        # 按年化ROI排序
        options.sort(key=lambda x: x.annualized_roi, reverse=True)
        return options

    def screen_calls(self, symbol: str, expiry_date: str,
                    stock_price: float) -> List[OptionContract]:
        """筛选CALL期权"""
        options = []
        chain_data = self.get_option_chain(symbol, expiry_date)

        days = self.calculate_days_to_expiry(expiry_date)

        for item in chain_data:
            try:
                strike = float(item.get('strike', 0))
                call_price = float(item.get('call_last', 0))
                call_iv = float(item.get('call_iv', 0)) * 100
                call_vol = int(item.get('call_vol', 0))

                if strike <= 0 or call_price <= 0 or call_vol <= 0:
                    continue

                contract = OptionContract(
                    symbol=symbol,
                    strike=strike,
                    expiry_date=expiry_date,
                    option_type='CALL',
                    price=call_price,
                    iv=call_iv,
                    volume=call_vol,
                    stock_price=stock_price,
                    days_to_expiry=days,
                    risk_free_rate=self.risk_free_rate
                )

                # 应用筛选条件
                if self._meets_criteria(contract, option_type='CALL'):
                    options.append(contract)

            except (ValueError, KeyError) as e:
                continue

        # 按年化ROI排序
        options.sort(key=lambda x: x.annualized_roi, reverse=True)
        return options

    def _meets_criteria(self, contract: OptionContract, option_type: str) -> bool:
        """检查期权是否符合筛选条件"""
        # 通用条件
        if contract.iv < self.criteria['iv_min']:
            return False
        if contract.volume < self.criteria['volume_min']:
            return False
        if contract.days_to_expiry > self.criteria['days_max']:
            return False
        if contract.days_to_expiry < self.criteria['days_min']:
            return False
        if contract.roi < self.criteria['roi_min']:
            return False
        if contract.annualized_roi < self.criteria['annualized_roi_min']:
            return False
        if not contract.is_otm:
            return False

        # 策略专属条件
        prob_str = contract.probability_not_exercised
        # 处理概率格式："59.5%" 或 "<50%"
        if '<' in prob_str:
            prob_value = 0.0
        else:
            # 移除 % 符号并转换为浮点数
            prob_value = float(prob_str.rstrip('%'))

        if option_type == 'PUT':
            if prob_value < self.criteria['put_probability_min']:
                return False
        elif option_type == 'CALL':
            if prob_value < self.criteria['call_probability_min']:
                return False

        return True

    def screen_symbol(self, symbol: str, expiry_date: str,
                     option_types: List[str] = None) -> Dict[str, List[OptionContract]]:
        """筛选单个标的的所有期权类型"""
        if option_types is None:
            option_types = ['PUT', 'CALL']

        print(f"🔍 正在扫描 {symbol}...", file=sys.stderr)

        stock_price = self.get_stock_price(symbol)
        if not stock_price:
            print(f"❌ 无法获取{symbol}价格，跳过", file=sys.stderr)
            return {}

        print(f"   当前价格: ${stock_price:.2f}", file=sys.stderr)

        results = {}

        if 'PUT' in option_types:
            puts = self.screen_puts(symbol, expiry_date, stock_price)
            if puts:
                results['PUT'] = puts
                print(f"   ✓ 找到 {len(puts)} 个符合条件的PUT期权", file=sys.stderr)

        if 'CALL' in option_types:
            calls = self.screen_calls(symbol, expiry_date, stock_price)
            if calls:
                results['CALL'] = calls
                print(f"   ✓ 找到 {len(calls)} 个符合条件的CALL期权", file=sys.stderr)

        return results

    def get_available_expiry_dates(self, symbol: str,
                                    days_min: int = 0,
                                    days_max: int = 45) -> List[str]:
        """获取指定标的所有可用到期日（在days_min到days_max范围内）

        注意：由于 longbridge CLI 的 bug，不带 --date 参数时无法正确返回到期日列表，
        因此需要逐个日期测试以找出实际有期权数据的日期。
        """
        available_dates = []

        today = datetime.now()
        for days in range(days_min, days_max + 1):
            candidate_date = today + timedelta(days=days)
            date_str = candidate_date.strftime('%Y-%m-%d')

            # 测试这个日期是否有期权数据
            try:
                result = subprocess.run(
                    ['longbridge', 'option', 'chain', symbol,
                     '--date', date_str, '--format', 'json'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    data = json.loads(result.stdout)
                    if data and len(data) > 0:
                        # 确保有实际的期权合约
                        has_valid_options = any(
                            float(item.get('put_last', 0)) > 0 or
                            float(item.get('call_last', 0)) > 0
                            for item in data
                        )
                        if has_valid_options:
                            available_dates.append(date_str)
            except Exception as e:
                # 记录错误但继续处理其他日期
                print(f"   ⚠️  检查 {date_str} 时出错: {e}", file=sys.stderr)
                continue

        return sorted(available_dates)

    def screen_symbol_all_dates(self, symbol: str,
                                 option_types: List[str] = None) -> Dict[str, List[OptionContract]]:
        """扫描单个标的所有可用到期日的期权"""
        if option_types is None:
            option_types = ['PUT']

        print(f"🔍 正在扫描 {symbol} 的所有到期日...", file=sys.stderr)

        stock_price = self.get_stock_price(symbol)
        if not stock_price:
            print(f"❌ 无法获取{symbol}价格，跳过", file=sys.stderr)
            return {}

        print(f"   当前价格: ${stock_price:.2f}", file=sys.stderr)

        # 获取所有可用到期日
        expiry_dates = self.get_available_expiry_dates(
            symbol,
            days_min=self.criteria['days_min'],
            days_max=self.criteria['days_max']
        )

        if not expiry_dates:
            print(f"   ⚠️  未找到可用到期日", file=sys.stderr)
            return {}

        print(f"   📅 找到 {len(expiry_dates)} 个到期日: {', '.join(expiry_dates)}", file=sys.stderr)

        all_options = {'PUT': [], 'CALL': []}

        # 扫描每个到期日
        for expiry_date in expiry_dates:
            days = self.calculate_days_to_expiry(expiry_date)
            print(f"      → {expiry_date} ({days}天)", file=sys.stderr)

            if 'PUT' in option_types:
                puts = self.screen_puts(symbol, expiry_date, stock_price)
                all_options['PUT'].extend(puts)

            if 'CALL' in option_types:
                calls = self.screen_calls(symbol, expiry_date, stock_price)
                all_options['CALL'].extend(calls)

        # 按年化ROI排序
        all_options['PUT'].sort(key=lambda x: x.annualized_roi, reverse=True)
        all_options['CALL'].sort(key=lambda x: x.annualized_roi, reverse=True)

        # 只返回有结果的类型
        results = {}
        if all_options['PUT']:
            results['PUT'] = all_options['PUT']
            print(f"   ✓ PUT期权总计: {len(all_options['PUT'])} 个", file=sys.stderr)
        if all_options['CALL']:
            results['CALL'] = all_options['CALL']
            print(f"   ✓ CALL期权总计: {len(all_options['CALL'])} 个", file=sys.stderr)

        return results

    def screen_multiple(self, symbols: List[str], expiry_date: str,
                       option_types: List[str] = None) -> Dict[str, Dict[str, List[OptionContract]]]:
        """筛选多个标的（单一到期日）"""
        all_results = {}

        for symbol in symbols:
            results = self.screen_symbol(symbol, expiry_date, option_types)
            if results:
                all_results[symbol] = results

        return all_results

    def screen_multiple_all_dates(self, symbols: List[str],
                                   option_types: List[str] = None) -> Dict[str, Dict[str, List[OptionContract]]]:
        """筛选多个标的（所有可用到期日）"""
        all_results = {}

        for symbol in symbols:
            results = self.screen_symbol_all_dates(symbol, option_types)
            if results:
                all_results[symbol] = results

        return all_results


def print_results(results: Dict[str, Dict[str, List[OptionContract]]],
                 screener: OptionScreener):
    """打印筛选结果"""

    print("\n" + "="*80)
    print("🎯 Wheel Strategy 期权筛选结果".center(80))
    print("="*80)
    print(f"📅 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 筛选标准:")
    print(f"   • IV ≥ {screener.criteria['iv_min']}%")
    print(f"   • 成交量 ≥ {screener.criteria['volume_min']}张")
    print(f"   • 到期天数: {screener.criteria['days_min']}-{screener.criteria['days_max']}天")
    print(f"   • 单合约ROI ≥ {screener.criteria['roi_min']}%")
    print(f"   • 年化ROI ≥ {screener.criteria['annualized_roi_min']}%")
    print(f"   • PUT不被行权概率 ≥ {screener.criteria['put_probability_min']}%")
    print(f"   • CALL不被行权概率 ≥ {screener.criteria['call_probability_min']}%")
    print(f"   • 无风险利率: {screener.risk_free_rate * 100:.2f}%")
    print("="*80 + "\n")

    if not results:
        print("❌ 未找到符合条件的期权")
        return

    total_count = 0

    for symbol, symbol_data in results.items():
        for option_type, contracts in symbol_data.items():
            if not contracts:
                continue

            total_count += len(contracts)

            print(f"┌{'─'*98}┐")
            print(f"│ {symbol} {option_type} 期权 ({len(contracts)}个)".ljust(99) + '│')
            print(f"├{'─'*98}┤")
            print(f"│ {'行权价':^8} │ {'价格':^8} │ {'IV':^6} │ {'成交量':^8} │ {'到期日':^12} │ {'天数':^6} │ {'OTM%':^6} │ {'ROI':^8} │ {'年化ROI':^8} │ {'概率':^10} │")
            print(f"├{'─'*98}┤")

            for contract in contracts[:10]:  # 只显示前10个
                print(f"│ "
                      f"${contract.strike:6.2f} │ "
                      f"${contract.price:6.2f} │ "
                      f"{contract.iv:5.1f}% │ "
                      f"{contract.volume:7,} │ "
                      f"{contract.expiry_date:^12} │ "
                      f"{contract.days_to_expiry:^6} │ "
                      f"{contract.otm_pct:5.1f}% │ "
                      f"{contract.roi:6.2f}% │ "
                      f"{contract.annualized_roi:6.1f}% │ "
                      f"{contract.probability_not_exercised:^10} │")

            if len(contracts) > 10:
                print(f"│ ... 还有 {len(contracts) - 10} 个期权未显示".ljust(99) + '│')

            print(f"└{'─'*98}┘")
            print()

    print("="*80)
    print(f"✅ 共找到 {total_count} 个符合条件的期权合约")
    print("="*80)


def load_watchlist(script_dir: str = None) -> List[str]:
    """从 watchlist.txt 加载股票列表"""
    if script_dir is None:
        # SKILL 根目录是 scripts/ 的父目录
        script_dir = Path(__file__).resolve().parent.parent

    watchlist_path = Path(script_dir) / 'assets' / 'watchlist.txt'

    if not watchlist_path.exists():
        print(f"⚠️  watchlist.txt 不存在于 {watchlist_path}", file=sys.stderr)
        return []

    symbols = []
    with open(watchlist_path, 'r') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith('#'):
                continue
            symbols.append(line)

    return symbols


def main():
    """主函数"""
    # 默认股票列表
    default_symbols = [
        'NVDA.US',
        'AAPL.US',
        'SPY.US',
        'QQQ.US',
        'MSFT.US',
        'GOOGL.US',
        'AMZN.US',
        'META.US',
    ]

    # 默认到期日期（45天后）
    default_expiry = (datetime.now() + timedelta(days=27)).strftime('%Y-%m-%d')

    # 获取 SKILL 根目录（scripts/ 的父目录）
    script_dir = Path(__file__).resolve().parent.parent

    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(
        description='Wheel Strategy 期权自动化筛选脚本'
    )
    parser.add_argument(
        '-s', '--symbols',
        nargs='+',
        default=None,  # 改为 None，后面根据逻辑判断
        help='股票代码列表 (例如: NVDA.US AAPL.US)'
    )
    parser.add_argument(
        '-w', '--from-watchlist',
        action='store_true',
        help='从 watchlist.txt 读取股票列表'
    )
    parser.add_argument(
        '--all-dates',
        action='store_true',
        help='扫描所有可用到期日（在0-45天范围内），而不是单一日期'
    )
    parser.add_argument(
        '-d', '--date',
        default=default_expiry,
        help='期权到期日期 (YYYY-MM-DD，默认: 45天后。使用--all-dates时此参数被忽略)'
    )
    parser.add_argument(
        '-t', '--types',
        nargs='+',
        choices=['PUT', 'CALL'],
        default=['PUT'],
        help='期权类型 (PUT CALL)'
    )
    parser.add_argument(
        '-iv', '--iv-min',
        type=float,
        default=30.0,
        help='最小IV (默认: 30%%)'
    )
    parser.add_argument(
        '-v', '--volume-min',
        type=int,
        default=500,
        help='最小成交量 (默认: 500张)'
    )
    parser.add_argument(
        '-r', '--roi-min',
        type=float,
        default=2.0,
        help='最小单合约ROI (默认: 2%%)'
    )
    parser.add_argument(
        '-a', '--annualized-roi-min',
        type=float,
        default=30.0,
        help='最小年化ROI (默认: 30%%)'
    )
    parser.add_argument(
        '--days-min',
        type=int,
        default=0,
        help='最小到期天数 (默认: 0)'
    )
    parser.add_argument(
        '--days-max',
        type=int,
        default=45,
        help='最大到期天数 (默认: 45)'
    )
    parser.add_argument(
        '--put-prob-min',
        type=float,
        default=60.0,
        help='PUT不被行权最小概率 (默认: 60%%)'
    )
    parser.add_argument(
        '--call-prob-min',
        type=float,
        default=70.0,
        help='CALL不被行权最小概率 (默认: 70%%)'
    )
    parser.add_argument(
        '--risk-free-rate',
        type=float,
        default=3.68,
        help='无风险利率，单位%% (默认: 3.68%%)'
    )

    args = parser.parse_args()

    # 确定股票列表（优先级：命令行指定 > watchlist > 默认列表）
    if args.symbols:
        # 用户通过 -s 明确指定了股票列表
        symbols = args.symbols
        print(f"📋 使用命令行指定的 {len(symbols)} 只股票", file=sys.stderr)
    elif args.from_watchlist:
        # 从 watchlist.txt 读取
        symbols = load_watchlist(script_dir)
        if not symbols:
            print("❌ watchlist.txt 为空或不存在，使用默认股票列表", file=sys.stderr)
            symbols = default_symbols
        else:
            print(f"📋 从 watchlist.txt 加载了 {len(symbols)} 只股票", file=sys.stderr)
    else:
        # 使用默认股票列表
        symbols = default_symbols
        print(f"📋 使用默认的 {len(symbols)} 只股票", file=sys.stderr)

    # 创建筛选器（将百分比转换为小数）
    risk_free_rate_decimal = args.risk_free_rate / 100.0
    screener = OptionScreener(risk_free_rate=risk_free_rate_decimal)

    # 更新筛选标准（所有参数都是可选的，使用传入值或默认值）
    screener.criteria['iv_min'] = args.iv_min
    screener.criteria['volume_min'] = args.volume_min
    screener.criteria['roi_min'] = args.roi_min
    screener.criteria['annualized_roi_min'] = args.annualized_roi_min
    screener.criteria['days_min'] = args.days_min
    screener.criteria['days_max'] = args.days_max
    screener.criteria['put_probability_min'] = args.put_prob_min
    screener.criteria['call_probability_min'] = args.call_prob_min

    # 执行筛选
    if args.all_dates:
        print(f"🔄 全日期扫描模式: 扫描{args.days_min}-{args.days_max}天内的所有到期日", file=sys.stderr)
        results = screener.screen_multiple_all_dates(
            symbols=symbols,
            option_types=args.types
        )
    else:
        print(f"📅 单一日期扫描模式: {args.date}", file=sys.stderr)
        results = screener.screen_multiple(
            symbols=symbols,
            expiry_date=args.date,
            option_types=args.types
        )

    # 打印结果
    print_results(results, screener)


if __name__ == '__main__':
    main()
