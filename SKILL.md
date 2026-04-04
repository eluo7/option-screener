---
name: option-screener
description: Help users screen and filter Wheel Strategy options trading opportunities. Automatically scans option chains across multiple expiry dates (0-45 days), applies quantitative criteria (IV≥30%, volume≥500, ROI≥2%, annualized ROI≥30%), and filters for out-of-the-money contracts with favorable exercise probabilities. Use when user asks about selling options, Wheel Strategy, cash-secured puts, covered calls, or screening options for income. Works with any stock/watchlist and supports customizable screening parameters.
compatibility: "Requires Longbridge CLI for options data"
---

# Option Screener - Wheel Strategy 期权筛选工具

自动化筛选和监控 Wheel Strategy 期权交易机会。

## 何时使用此 SKILL

当用户提到以下需求时，使用此 SKILL：

- **期权卖方策略**：卖 PUT（现金担保看跌期权）、卖 CALL（备兑看涨期权）
- **Wheel Strategy**：完整的期权卖方轮转策略
- **期权筛选/扫描**：寻找符合条件的期权合约
- **自选股监控**：扫描 watchlist 中的期权机会
- **高收益期权**：寻找年化收益 30% 以上的期权
- **高 IV 期权**：寻找隐含波动率较高的期权
- **流动性筛选**：确保期权有足够成交量

## 默认筛选标准

所有参数都可以根据用户需求调整：

**期权合约要求：**
- IV（隐含波动率）≥ 30%
- 成交量 ≥ 500 张
- 到期天数：0-45 天
- 必须是 OTM（虚值期权）

**收益要求：**
- 单合约 ROI ≥ 2%
- 年化 ROI ≥ 30%

**不被行权概率：**
- PUT 期权 ≥ 60%
- CALL 期权 ≥ 70%

## 核心功能

### 1. 自动扫描所有到期日

**重要**：默认扫描 0-45 天内**所有可用的到期日**，不只是单一日期。

```bash
# 扫描所有到期日（默认）
python3 scripts/option_screener.py --from-watchlist --all-dates

# 扫描单一日期
python3 scripts/option_screener.py --from-watchlist -d 2026-05-01
```

### 2. 从 watchlist 读取

默认从 `assets/watchlist.txt` 读取自选股列表：

```
# 每行一个股票代码
NVDA.US
AAPL.US
TQQQ.US
SOXL.US
```

### 3. 自定义筛选参数

所有参数都是可选的：

```bash
# 只看高 IV 期权
python3 scripts/option_screener.py --from-watchlist --all-dates -iv 50

# 只看短期期权（10天内）
python3 scripts/option_screener.py --from-watchlist --all-dates --days-max 10

# 要求更高年化收益（40%以上）
python3 scripts/option_screener.py --from-watchlist --all-dates -a 40

# 更保守的概率要求（不被行权概率75%+）
python3 scripts/option_screener.py --from-watchlist --all-dates --put-prob-min 75

# 指定无风险利率（例如：4.2%）
python3 scripts/option_screener.py --from-watchlist --all-dates --risk-free-rate 4.2
```

## 工作流程

### 步骤 1：理解用户需求

确认用户想要：
- 扫描哪些股票？（watchlist / 指定股票）
- 扫描什么类型期权？（PUT / CALL / 两者都要）
- 有特殊要求吗？（高 IV、短期、高收益等）

### 步骤 2：执行扫描

**推荐做法：扫描所有到期日**

```bash
cd ~/.claude/skills/option-screener
python3 scripts/option_screener.py --from-watchlist --all-dates --types PUT
```

**优点：**
- 找到所有符合条件的机会
- 用户可以比较不同到期日的收益
- 不会错过任何机会

**注意**：第一次扫描会测试多个日期，可能需要 1-2 分钟。脚本会自动：
1. 测试每个周五（美股期权通常周五到期）
2. 找到有期权数据的日期
3. 扫描每个日期的所有行权价
4. 汇总所有结果并排序

### 步骤 3：展示结果

脚本会输出：
- 每个股票的当前价格
- 找到多少个到期日
- 每个到期日有多少符合条件的期权
- 详细的期权列表（按年化 ROI 排序）

## 快速启动脚本

使用 `scripts/quick_screen.sh` 快速执行常见操作：

```bash
# 扫描 watchlist（所有到期日）
./scripts/quick_screen.sh -w

# 扫描单股（所有到期日）
./scripts/quick_screen.sh -nvda

# 扫描所有默认股票（所有到期日）
./scripts/quick_screen.sh -all

# 单一日期扫描模式
./scripts/quick_screen.sh --single
```

## 参数说明

### 股票选择
- `-s SYMBOLS`：指定股票列表（空格分隔）
- `-w, --from-watchlist`：从 watchlist.txt 读取

### 日期选择
- `--all-dates`：扫描所有可用到期日（推荐）
- `-d DATE`：指定单一到期日期（YYYY-MM-DD）
- `--days-min N`：最小到期天数（默认: 0）
- `--days-max N`：最大到期天数（默认: 45）

### 期权类型
- `-t TYPES`：期权类型（PUT / CALL / PUT CALL）

### 筛选标准
- `-iv N`：最小 IV（默认: 30%）
- `-v N`：最小成交量（默认: 500 张）
- `-r N`：最小单合约 ROI（默认: 2%）
- `-a N`：最小年化 ROI（默认: 30%）
- `--put-prob-min N`：PUT 不被行权最小概率（默认: 60%）
- `--call-prob-min N`：CALL 不被行权最小概率（默认: 70%）
- `--risk-free-rate N`：无风险利率，单位%（默认: 3.68%）

## 示例对话

**用户：** "扫描一下我的自选股，看看有哪些符合 Wheel Strategy 的期权机会"

**响应：**
1. 从 `assets/watchlist.txt` 读取股票列表
2. 使用 `--all-dates` 扫描所有 0-45 天到期日
3. 应用默认筛选标准
4. 展示所有符合条件的 PUT 期权

**用户：** "我想找个年化收益 40% 以上的期权"

**响应：**
1. 设置 `-a 40` 参数
2. 扫描 watchlist 或询问要扫描哪些股票
3. 展示年化 ROI ≥ 40% 的期权

**用户：** "NVDA 有什么短期期权可以卖？只看 10 天内的"

**响应：**
1. 扫描 NVDA.US
2. 设置 `--days-max 10`
3. 使用 `--all-dates` 扫描所有短期到期日
4. 展示 10 天内到期的期权

## 技术说明

### Wheel Strategy 策略

1. **卖 PUT（现金担保看跌期权）**
   - 收取权利金
   - 如果被行权 → 以行权价买入股票
   - 如果不被行权 → 权利金入袋，继续卖 PUT

2. **持有股票后卖 CALL（备兑看涨期权）**
   - 收取权利金
   - 如果被行权 → 以行权价卖出股票，完成一轮 Wheel
   - 如果不被行权 → 权利金入袋，继续卖 CALL

3. **重复步骤 1**

### 不被行权概率计算

**基于 Black-Scholes 模型**的精确计算：

**计算公式：**
```
d2 = [ln(S/K) + (r - σ²/2)T] / (σ√T)

PUT 不被行权概率 = N(-d2)
CALL 不被行权概率 = N(d2)
```

**参数说明：**
- **S**: 标的资产当前价格
- **K**: 行权价
- **r**: 无风险利率（默认 3.68%）
- **σ**: 隐含波动率（IV）
- **T**: 到期时间（年）
- **N()**: 标准正态分布的累积分布函数

**无风险利率：**
- 默认值：**3.68%**
- 可通过 `--risk-free-rate` 参数自定义
- 建议根据市场环境定期更新（参考美国国债收益率）

**示例（TQQQ $42 PUT，5天后到期，IV=74.4%，无风险利率=3.68%）：**
- S = $43.33, K = $42, T = 5/365 = 0.0137
- σ = 0.744, r = 0.0368
- d2 = [ln(43.33/42) + (0.0368 - 0.744²/2) × 0.0137] / (0.744 × √0.0137)
- d2 ≈ 0.231
- 不被行权概率 = N(-0.231) ≈ **40.9%**

> **注意**：Black-Scholes 模型提供的是理论概率，实际行权概率可能因市场条件、突发事件等因素而有所不同。

### ROI 计算方法

**单合约 ROI** = 权利金 / 行权价 × 100%

**年化 ROI** = 单合约 ROI / (到期天数 / 365)

例如：
- 权利金 $2，行权价 $100 → ROI = 2%
- 如果 30 天到期 → 年化 ROI = 2% / (30/365) = 24.3%
- 如果 20 天到期 → 年化 ROI = 2% / (20/365) = 36.5%

## 故障排查

### 问题：找不到任何期权

**可能原因：**
1. 市场波动低，IV 普遍 < 30%
2. 调整 `-iv` 参数降低要求
3. 调整 `-a` 参数降低年化 ROI 要求

```bash
python3 scripts/option_screener.py --from-watchlist --all-dates -iv 20 -a 20
```

### 问题：longbridge 未登录

```bash
longbridge login
```

### 问题：扫描太慢

- 使用 `--days-max` 缩小日期范围
- 只扫描单一日期（不使用 `--all-dates`）
- 减少股票数量

## 输出格式

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ NVDA.US PUT 期权 (5个)                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ 行权价    │ 价格     │ IV     │ 成交量   │ OTM%   │ ROI    │ 年化ROI │ 概率     │
├──────────────────────────────────────────────────────────────────────────────┤
│ $175.00 │ $2.50  │ 45.2% │ 1,234   │ 5.2%  │ 1.43% │ 35.8%  │ 65-75%   │
│ $170.00 │ $1.80  │ 42.1% │ 2,567   │ 8.1%  │ 1.06% │ 26.5%  │ 70-80%   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 修改 watchlist

编辑 `assets/watchlist.txt`：

```bash
# 查看当前自选股
cat assets/watchlist.txt

# 添加新股票（手动编辑文件）
echo "TSLA.US" >> assets/watchlist.txt
```
