# 📺 YouTube 周报生成器

> 🎯 **零基础也能搭建！** 自动追踪你喜欢的YouTube博主，每周发送精华摘要到邮箱

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Cost](https://img.shields.io/badge/cost-FREE-brightgreen.svg)

## ✨ 功能特点

- 🔄 **自动追踪** - 自动检测关注频道的新视频
- 📝 **字幕提取** - 获取视频字幕内容
- 🤖 **AI 摘要** - Claude AI 智能总结，提炼精华
- 📧 **邮件推送** - 每周定时发送精美周报
- 💰 **完全免费** - 使用 GitHub Actions，零成本运行

## 📋 你需要准备什么

在开始之前，你需要注册以下账号（都是免费的）：

| 服务 | 用途 | 注册链接 |
|------|------|----------|
| GitHub | 存放代码 + 自动运行 | [github.com](https://github.com) |
| Gmail | 发送邮件 | [gmail.com](https://gmail.com) |
| Anthropic | AI 摘要服务 | [console.anthropic.com](https://console.anthropic.com) |

---

# 🚀 搭建教程（保姆级）

## 第一步：注册 GitHub 账号

> 如果你已有 GitHub 账号，跳过这一步

1. 打开 [github.com](https://github.com)
2. 点击右上角 **Sign up**
3. 输入邮箱、密码、用户名
4. 完成验证，创建账号

## 第二步：Fork 这个项目

1. 点击本页面右上角的 **Fork** 按钮
2. 点击 **Create fork**
3. 等待几秒，你就有了自己的项目副本

## 第三步：获取 Anthropic API Key

> 这是让 AI 帮你总结视频内容的关键

1. 打开 [console.anthropic.com](https://console.anthropic.com)
2. 注册账号（新用户有免费额度）
3. 登录后，点击左侧 **API Keys**
4. 点击 **Create Key**
5. 给 Key 起个名字（如 "youtube-digest"）
6. **复制并保存这个 Key**（只显示一次！）

> 💡 **费用说明**：新用户有 $5 免费额度，足够用很久。之后每条摘要大约 $0.01

## 第四步：设置 Gmail 应用专用密码

> 这是让程序能用你的 Gmail 发邮件

**⚠️ 注意：不是你的 Gmail 登录密码！**

1. 打开 [myaccount.google.com](https://myaccount.google.com)
2. 点击左侧 **安全性**
3. 找到 **两步验证**，如果没开启，先开启它
4. 开启后，返回安全性页面
5. 找到 **应用专用密码**（或搜索 "App passwords"）
6. 选择应用：**邮件**，设备：**其他**，输入 "YouTube Digest"
7. 点击 **生成**
8. **复制这16位密码**（格式如：xxxx xxxx xxxx xxxx）

> 📧 **推荐做法**：用一个 Gmail 发送，另一个 Gmail 接收

## 第五步：配置 GitHub Secrets

> 这是最关键的一步，设置你的私密信息

1. 打开你 Fork 的项目页面
2. 点击 **Settings**（设置）
3. 左侧找到 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**
5. 依次添加以下 5 个 Secret：

| Name（名称） | Value（值） | 说明 |
|-------------|------------|------|
| `ANTHROPIC_API_KEY` | sk-ant-api... | 第三步获取的 API Key |
| `EMAIL_SENDER` | your@gmail.com | 发送邮件的 Gmail 地址 |
| `EMAIL_PASSWORD` | xxxx xxxx xxxx xxxx | 第四步的应用专用密码 |
| `EMAIL_RECEIVER` | receive@gmail.com | 接收周报的邮箱（可以相同） |
| `YOUTUBE_CHANNELS` | ["@MrBeast","@TED"] | 要关注的频道列表（JSON格式） |

### 📺 关于 YOUTUBE_CHANNELS 的格式

这是一个 JSON 数组，包含你想关注的频道：

```json
["@MrBeast","@Fireship","@3Blue1Brown","@Kurzgesagt","@TED"]
```

**如何找到频道的 handle：**
1. 打开 YouTube，进入你想关注的频道
2. 看浏览器地址栏
3. 如果是 `youtube.com/@xxxxx` → 用 `@xxxxx`
4. 如果是 `youtube.com/channel/UCxxxxx` → 用 `UCxxxxx`

**示例：**
```json
["@MrBeast","@TED","UCX6OQ3DkcsbYNE6H8uQQuVA","@Kurzgesagt"]
```

## 第六步：手动测试运行

> 让我们先测试一下，确保一切正常

1. 打开你的项目页面
2. 点击 **Actions**
3. 左侧点击 **YouTube Weekly Digest**
4. 点击右侧 **Run workflow** → **Run workflow**
5. 等待运行（通常 2-5 分钟）
6. 如果显示 ✅ 绿色，检查你的邮箱！

### 如果失败了怎么办？

1. 点击失败的运行记录
2. 点击 **generate-digest**
3. 查看错误信息
4. 常见问题：
   - `ANTHROPIC_API_KEY` 不对 → 重新复制
   - 邮件发送失败 → 检查应用密码
   - 频道格式错误 → 确保是 JSON 数组格式

## 第七步：自动运行

配置完成后，系统会：
- **每周日早上 9:00（北京时间）** 自动运行
- 获取过去一周的新视频
- 生成摘要并发送到你的邮箱

你也可以随时手动运行（第六步的方法）

---

# 🎨 收到的周报长这样

邮件会包含：

- 📊 **统计数据** - 本周新视频数量
- 📺 **视频卡片** - 每个视频一张卡片
  - 标题（可点击跳转）
  - 频道名称和发布日期
  - AI 生成的内容摘要
  - 关键要点（3-5条）
  - 精彩洞察

---

# ⚙️ 自定义配置

## 修改运行时间

编辑 `.github/workflows/weekly.yml`：

```yaml
schedule:
  - cron: '0 1 * * 0'  # UTC时间
```

常用时间对照（北京时间）：
| 北京时间 | cron 表达式 |
|---------|------------|
| 周日 9:00 | `0 1 * * 0` |
| 周一 8:00 | `0 0 * * 1` |
| 每天 12:00 | `0 4 * * *` |

## 修改获取天数

在 `main.py` 中找到 `get_recent_videos`，修改 `days=7` 参数

---

# ❓ 常见问题

### Q: 完全免费吗？
**A:** 是的！GitHub Actions 每月有 2000 分钟免费额度，足够用。Anthropic 新用户有 $5 免费额度。

### Q: 一个视频大概消耗多少 API 费用？
**A:** 大约 $0.005-0.02，取决于视频长度。$5 额度可以处理 250-500 个视频。

### Q: 没有字幕的视频怎么办？
**A:** 会标注"无可用字幕"，不影响其他视频。

### Q: 可以关注多少个频道？
**A:** 建议 5-20 个。太多会增加运行时间和 API 费用。

### Q: 为什么有些视频没有摘要？
**A:** 可能是：1) 视频太新还没字幕 2) UP主禁用了字幕 3) 是直播回放

---

# 🔧 进阶：本地运行

如果你想在自己电脑上测试：

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/youtube-digest.git
cd youtube-digest

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export ANTHROPIC_API_KEY="你的API Key"
export EMAIL_SENDER="发件邮箱"
export EMAIL_PASSWORD="应用专用密码"
export EMAIL_RECEIVER="收件邮箱"
export YOUTUBE_CHANNELS='["@MrBeast","@TED"]'

# 4. 运行
python main.py
```

---

# 📜 开源协议

MIT License - 随便用，记得 Star ⭐

---

# 🙏 致谢

- [Claude AI](https://anthropic.com) - 强大的 AI 摘要能力
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - 字幕提取
- [GitHub Actions](https://github.com/features/actions) - 免费自动化

---

**有问题？** 提 Issue 或联系作者 💬
