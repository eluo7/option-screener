#!/bin/bash
# Wheel Strategy 快速扫描脚本
# 用于日常期权筛选

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Wheel Strategy 期权快速扫描工具                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查参数
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -q, --quick         快速扫描（默认股票列表，所有到期日）"
    echo "  -w, --watchlist     从 watchlist.txt 读取股票列表（所有到期日）"
    echo "  -c, --custom        自定义扫描（交互式）"
    echo "  -nvda               只扫描 NVDA（所有到期日）"
    echo "  -spy                只扫描 SPY（所有到期日）"
    echo "  -all                扫描所有默认标的（所有到期日）"
    echo "  --single            单一日期扫描模式（使用默认日期）"
    echo ""
    echo "示例:"
    echo "  $0 -q               # 快速扫描（所有到期日）"
    echo "  $0 -w               # 从 watchlist.txt 扫描（所有到期日）"
    echo "  $0 -nvda            # 只扫描 NVDA（所有到期日）"
    echo "  $0 -all             # 扫描所有标的（所有到期日）"
    echo "  $0 --single         # 单一日期扫描模式"
    exit 0
fi

# 检查 longbridge 是否登录
echo -e "${YELLOW}⚠️  检查 Longbridge 登录状态...${NC}"
if ! longbridge check &>/dev/null; then
    echo -e "${YELLOW}⚠️  未登录或登录过期，正在尝试登录...${NC}"
    longbridge login
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}❌ 登录失败，请手动运行: longbridge login${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ 登录状态正常${NC}"
echo ""

# 默认股票列表
DEFAULT_SYMBOLS="NVDA.US AAPL.US SPY.US QQQ.US MSFT.US GOOGL.US AMZN.US"

# 默认到期日期（大约1个月后）
DEFAULT_DATE=$(date -v+27d +%Y-%m-%d 2>/dev/null || date -d "+27 days" +%Y-%m-%d 2>/dev/null)

# 根据参数选择扫描模式
case "$1" in
    -q|--quick)
        echo -e "${GREEN}🚀 快速扫描模式（所有到期日）${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            -s $DEFAULT_SYMBOLS \
            --all-dates \
            --types PUT
        ;;
    -w|--watchlist)
        echo -e "${GREEN}📋 自选股扫描模式（所有到期日）${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            --from-watchlist \
            --all-dates \
            --types PUT
        ;;
    -nvda)
        echo -e "${GREEN}🎯 单股扫描: NVDA（所有到期日）${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            -s NVDA.US \
            --all-dates \
            --types PUT
        ;;
    -spy)
        echo -e "${GREEN}🎯 单股扫描: SPY（所有到期日）${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            -s SPY.US \
            --all-dates \
            --types PUT
        ;;
    -all)
        echo -e "${GREEN}🔍 全量扫描模式（所有到期日）${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            -s $DEFAULT_SYMBOLS \
            --all-dates \
            --types PUT CALL
        ;;
    --single)
        echo -e "${GREEN}📅 单一日期扫描模式${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            -s $DEFAULT_SYMBOLS \
            -d $DEFAULT_DATE \
            --types PUT
        ;;
    -c|--custom)
        echo -e "${GREEN}🔧 自定义扫描模式${NC}"
        echo ""
        echo "请输入股票代码（空格分隔，如: NVDA.US AAPL.US）:"
        read -r symbols
        echo "扫描模式 (1=所有到期日, 2=单一日期):"
        read -r mode_choice
        echo "选择期权类型 (1=PUT, 2=CALL, 3=全部):"
        read -r type_choice

        case $type_choice in
            1) types="PUT" ;;
            2) types="CALL" ;;
            3) types="PUT CALL" ;;
            *) types="PUT" ;;
        esac

        if [ "$mode_choice" = "2" ]; then
            echo "请输入到期日期（YYYY-MM-DD，留空使用默认 $DEFAULT_DATE）:"
            read -r date
            date=${date:-$DEFAULT_DATE}
            python3 "$SCRIPT_DIR/option_screener.py" \
                -s $symbols \
                -d $date \
                --types $types
        else
            python3 "$SCRIPT_DIR/option_screener.py" \
                -s $symbols \
                --all-dates \
                --types $types
        fi
        ;;
    *)
        echo -e "${GREEN}🚀 默认扫描模式（所有到期日）${NC}"
        python3 "$SCRIPT_DIR/option_screener.py" \
            -s $DEFAULT_SYMBOLS \
            --all-dates \
            --types PUT
        ;;
esac

echo ""
echo -e "${GREEN}✅ 扫描完成！${NC}"
echo ""
echo -e "${BLUE}💡 提示:${NC}"
echo "  - 查看详细说明: cat $SCRIPT_DIR/OPTION_SCREENER_README.md"
echo "  - 自定义筛选: python3 $SCRIPT_DIR/option_screener.py --help"
echo "  - 保存结果: python3 $SCRIPT_DIR/option_screener.py > results.txt"
