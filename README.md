# 📺 YouTube 周报生成器

自动追踪 YouTube 频道更新，每周发送精华摘要到邮箱。

## 🚀 快速开始

### 1. 上传这些文件到 GitHub 仓库

### 2. 设置 Secrets（Settings → Secrets → Actions）

| Name | Value | 必需 |
|------|-------|------|
| `ANTHROPIC_API_KEY` | 你的 Anthropic API Key | ✅ |
| `EMAIL_SENDER` | 发件 Gmail 地址 | ✅ |
| `EMAIL_PASSWORD` | Gmail 应用专用密码 | ✅ |
| `EMAIL_RECEIVER` | 收件邮箱 | ✅ |
| `YOUTUBE_CHANNELS` | `["@channel1","@channel2"]` | ✅ |
| `GROQ_API_KEY` | Groq API Key（用于语音识别） | 可选 |
| `DAYS_TO_FETCH` | 获取天数，默认 7 | 可选 |

### 3. 运行

- 自动：每周日早上 9:00（北京时间）
- 手动：Actions → Run workflow

## 📝 获取 API Keys

- **Anthropic**: https://console.anthropic.com
- **Groq**: https://console.groq.com
- **Gmail 应用密码**: Google 账号 → 安全性 → 两步验证 → 应用专用密码
