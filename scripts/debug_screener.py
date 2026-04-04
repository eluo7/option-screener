#!/usr/bin/env python3
"""
调试脚本：查看TQQQ期权数据，了解哪个条件过滤掉了所有期权
"""

import subprocess
import sys
from datetime import datetime, timedelta
from typing import List, Dict
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
    risk_free_rate: float = 0.0368

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
        """基于 Black-Scholes 模型的不被行权概率"""
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
            d2 = (log(S / K) + (r - sigma**2 / 2) * T) / (sigma * sqrt(T))
            if self.option_type == 'PUT':
                prob = norm.cdf(-d2)
            else:
                prob = norm.cdf(d2)
            prob_pct = prob * 100
            return f"{prob_pct:.1f}%"
        except:
            return "<50%"

class DebugOptionScreener:
    def __init__(self, criteria: Dict):
        self.criteria = criteria
        self.risk_free_rate = criteria.get('risk_free_rate', 0.0368)

    def get_stock_price(self, symbol: str) -> float:
        """获取股票价格"""
        cmd = ['longbridge', 'quote', symbol]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stdout.strip()
            # 解析输出获取价格
            lines = output.split('\n')
            for line in lines:
                if 'Last price' in line or 'last_price' in line:
                    price = float(line.split()[-1].replace(',', '').replace('$', ''))
                    return price
            return 0.0
        except:
            return 0.0

    def get_option_chain(self, symbol: str, expiry_date: str) -> List[Dict]:
        """获取期权链数据"""
        cmd = ['longbridge', 'quote', 'option-chain', '--expiry', expiry_date, symbol]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # 输出是表格格式，需要解析
            return self._parse_option_chain_output(result.stdout)
        except:
            return []

    def _parse_option_chain_output(self, output: str) -> List[Dict]:
        """解析longbridge输出的期权链"""
        options = []
        lines = output.split('\n')

        # 找到表格开始位置
        data_start = False
        headers = []

        for line in lines:
            if '|' in line and 'Strike' in line:
                headers = [h.strip() for h in line.split('|')[1:-1]]
                data_start = True
                continue

            if data_start and '|' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 7:
                    try:
                        option = {
                            'strike': float(parts[0].replace('$', '')),
                            'call_last': float(parts[1].replace('$', '')) if parts[1] != '-' else 0,
                            'call_iv': float(parts[2].replace('%', '')) if parts[2] != '-' else 0,
                            'call_vol': int(parts[3].replace(',', '')) if parts[3] != '-' else 0,
                            'put_last': float(parts[4].replace('$', '')) if parts[4] != '-' else 0,
                            'put_iv': float(parts[5].replace('%', '')) if parts[5] != '-' else 0,
                            'put_vol': int(parts[6].replace(',', '')) if parts[6] != '-' else 0,
                        }
                        options.append(option)
                    except:
                        continue

        return options

    def calculate_days_to_expiry(self, expiry_date: str) -> int:
        """计算距离到期的天数"""
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days = (expiry - today).days
        return max(0, days)

    def check_filters(self, contract: OptionContract, option_type: str) -> List[str]:
        """检查期权不符合哪些条件"""
        failures = []

        if contract.iv < self.criteria['iv_min']:
            failures.append(f"IV太低 ({contract.iv:.1f}% < {self.criteria['iv_min']}%)")

        if contract.volume < self.criteria['volume_min']:
            failures.append(f"成交量太低 ({contract.volume} < {self.criteria['volume_min']})")

        if contract.days_to_expiry > self.criteria['days_max']:
            failures.append(f"到期天数太长 ({contract.days_to_expiry} > {self.criteria['days_max']})")

        if contract.days_to_expiry < self.criteria['days_min']:
            failures.append(f"到期天数太短 ({contract.days_to_expiry} < {self.criteria['days_min']})")

        if contract.roi < self.criteria['roi_min']:
            failures.append(f"ROI太低 ({contract.roi:.2f}% < {self.criteria['roi_min']}%)")

        if contract.annualized_roi < self.criteria['annualized_roi_min']:
            failures.append(f"年化ROI太低 ({contract.annualized_roi:.1f}% < {self.criteria['annualized_roi_min']}%)")

        if not contract.is_otm:
            failures.append(f"不是OTM期权")

        prob_str = contract.probability_not_exercised
        if '<' in prob_str:
            prob_value = 0.0
        else:
            prob_value = float(prob_str.rstrip('%'))

        if option_type == 'PUT':
            if prob_value < self.criteria['put_probability_min']:
                failures.append(f"不被行权概率太低 ({prob_str} < {self.criteria['put_probability_min']}%)")

        return failures

    def debug_puts(self, symbol: str, expiry_date: str, stock_price: float) -> None:
        """调试PUT期权"""
        chain_data = self.get_option_chain(symbol, expiry_date)
        days = self.calculate_days_to_expiry(expiry_date)

        print(f"\n📅 {expiry_date} ({days}天到期) - PUT期权分析")
        print("=" * 120)

        otm_count = 0
        passed_count = 0

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

                if not contract.is_otm:
                    continue

                otm_count += 1

                failures = self.check_filters(contract, 'PUT')

                if not failures:
                    passed_count += 1
                    status = "✅ 通过"
                else:
                    status = f"❌ {', '.join(failures[:2])}"

                print(f"{status} | 行权价 ${strike:6.2f} | 权利金 ${put_price:5.2f} | "
                      f"IV {put_iv:5.1f}% | 成交量 {put_vol:4d} | "
                      f"OTM {contract.otm_pct:4.1f}% | ROI {contract.roi:4.2f}% | "
                      f"年化 {contract.annualized_roi:5.1f}% | 概率 {contract.probability_not_exercised:>6}")

                if otm_count >= 10:  # 只显示前10个
                    break

            except (ValueError, KeyError) as e:
                continue

        if otm_count == 0:
            print("   没有找到OTM PUT期权")
        else:
            print(f"\n总计: {otm_count}个OTM PUT期权, {passed_count}个通过筛选")

def main():
    # 默认筛选标准
    criteria = {
        'iv_min': 30.0,
        'volume_min': 500,
        'roi_min': 2.0,
        'annualized_roi_min': 30.0,
        'days_min': 0,
        'days_max': 45,
        'put_probability_min': 60.0,
        'call_probability_min': 70.0,
        'risk_free_rate': 0.0368
    }

    symbol = 'TQQQ.US'
    screener = DebugOptionScreener(criteria)

    print(f"🔍 调试分析 {symbol}")
    print("=" * 120)
    print(f"筛选标准: IV≥{criteria['iv_min']}%, 成交量≥{criteria['volume_min']}, "
          f"ROI≥{criteria['roi_min']}%, 年化ROI≥{criteria['annualized_roi_min']}%, "
          f"不被行权概率≥{criteria['put_probability_min']}%")

    # 获取当前价格
    stock_price = screener.get_stock_price(symbol)
    print(f"当前价格: ${stock_price:.2f}\n")

    if not stock_price:
        print("❌ 无法获取价格")
        return

    # 检查多个到期日
    today = datetime.now()
    for days in [5, 12, 19, 26]:
        expiry_date = (today + timedelta(days=days)).strftime('%Y-%m-%d')
        screener.debug_puts(symbol, expiry_date, stock_price)

if __name__ == '__main__':
    main()
