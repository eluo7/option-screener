# Option Screener Skill - 安装指南

## 方案1：直接复制（最简单）

```bash
# 在目标机器上，直接复制整个skill文件夹
cp -r option-screener ~/.claude/skills/
```

## 方案2：创建Git仓库（推荐）

### 步骤1：初始化Git仓库
```bash
cd /Users/jiahaoluo/.claude/skills/option-screener
git init
git add .
git commit -m "Initial commit: Option screener with probability calculation fix"
```

### 步骤2：推送到远程仓库
```bash
# GitHub
git remote add origin https://github.com/YOUR_USERNAME/option-screener.git
git branch -M main
git push -u origin main

# 或者 GitLab
git remote add origin https://gitlab.com/YOUR_USERNAME/option-screener.git
git push -u origin main
```

### 步骤3：其他Agent安装
```bash
# 克隆到skills目录
git clone https://github.com/YOUR_USERNAME/option-screener.git ~/.claude/skills/option-screener
```

## 方案3：打包分享

```bash
# 创建压缩包
cd /Users/jiahaoluo/.claude/skills/
tar -czf option-screener.tar.gz option-screener/

# 或者zip
zip -r option-screener.zip option-screener/

# 分享后，在其他机器上解压
tar -xzf option-screener.tar.gz -C ~/.claude/skills/
# 或
unzip option-screener.zip -d ~/.claude/skills/
```

## 前置依赖

在安装skill之前，确保目标机器已安装：

### 1. Longbridge CLI
```bash
# 安装longbridge CLI
pip install longbridge

# 配置登录
longbridge login
```

### 2. Python依赖
```bash
pip install scipy
```

## 验证安装

安装完成后，验证skill是否可用：

```bash
# 测试扫描
cd ~/.claude/skills/option-screener
python3 scripts/option_screener.py --all-dates -s TQQQ.US -t PUT

# 或者检查SKILL.md
cat ~/.claude/skills/option-screener/SKILL.md
```

## 配置Watchlist

如果需要扫描自选股，编辑watchlist文件：

```bash
# 编辑watchlist
vim ~/.claude/skills/option-screener/assets/watchlist.txt

# 添加股票代码（每行一个）
TQQQ.US
NVDA.US
AAPL.US
```

## 更新Skill

如果是通过Git安装的：

```bash
cd ~/.claude/skills/option-screener
git pull
```

如果是直接复制的：

```bash
# 重新复制
cp -r /path/to/new/option-screener ~/.claude/skills/
```

## 卸载Skill

```bash
# 删除skill目录
rm -rf ~/.claude/skills/option-screener
```
