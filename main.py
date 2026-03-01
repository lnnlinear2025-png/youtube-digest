#!/usr/bin/env python3
"""
YouTube 周报生成器
自动获取订阅频道的新视频，提取字幕，用AI整理成摘要，发送到邮箱
"""

import os
import json
import smtplib
import feedparser
import requests
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import anthropic

# ============= 配置区域 =============

# 获取多少天内的视频（默认7天，可通过环境变量修改）
DAYS_TO_FETCH = int(os.environ.get("DAYS_TO_FETCH", "7"))

def get_config():
    """从环境变量获取配置"""
    print("🔍 检查环境变量...")
    print(f"  ANTHROPIC_API_KEY: {'✅ 已设置' if os.environ.get('ANTHROPIC_API_KEY') else '❌ 未设置'}")
    print(f"  EMAIL_SENDER: {'✅ 已设置' if os.environ.get('EMAIL_SENDER') else '❌ 未设置'}")
    print(f"  EMAIL_PASSWORD: {'✅ 已设置' if os.environ.get('EMAIL_PASSWORD') else '❌ 未设置'}")
    print(f"  EMAIL_RECEIVER: {'✅ 已设置' if os.environ.get('EMAIL_RECEIVER') else '❌ 未设置'}")
    print(f"  DAYS_TO_FETCH: {DAYS_TO_FETCH} 天")
    
    # 获取频道列表
    channels_str = os.environ.get("YOUTUBE_CHANNELS", "")
    print(f"  YOUTUBE_CHANNELS: {channels_str if channels_str else '❌ 未设置'}")
    
    # 解析频道列表
    if channels_str:
        try:
            channels = json.loads(channels_str)
            print(f"  ✅ 解析到 {len(channels)} 个频道")
        except json.JSONDecodeError as e:
            print(f"  ❌ YOUTUBE_CHANNELS 格式错误: {e}")
            channels = []
    else:
        channels = []
    
    return {
        "email": {
            "sender": os.environ.get("EMAIL_SENDER", ""),
            "password": os.environ.get("EMAIL_PASSWORD", ""),
            "receiver": os.environ.get("EMAIL_RECEIVER", ""),
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587
        },
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "channels": channels
    }

# ============= 核心功能 =============

def get_channel_id_from_handle(handle: str) -> tuple:
    """
    从YouTube频道handle（如@MrBeast）获取频道ID和频道名称
    返回: (channel_id, channel_name)
    """
    # 如果已经是频道ID格式，直接返回
    if handle.startswith("UC") and len(handle) == 24:
        print(f"  📺 {handle} 已是频道ID格式")
        return handle, handle
    
    # 移除@符号
    clean_handle = handle.lstrip("@")
    
    print(f"  🔍 正在获取 @{clean_handle} 的频道ID...")
    
    # 尝试通过页面获取频道ID
    try:
        url = f"https://www.youtube.com/@{clean_handle}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"  ❌ 请求失败，状态码: {response.status_code}")
            return None, clean_handle
        
        # 方法1: 从 channelId 提取
        match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', response.text)
        if match:
            channel_id = match.group(1)
            print(f"  ✅ 找到频道ID: {channel_id}")
            return channel_id, clean_handle
        
        # 方法2: 从 externalId 提取
        match = re.search(r'"externalId":"(UC[a-zA-Z0-9_-]{22})"', response.text)
        if match:
            channel_id = match.group(1)
            print(f"  ✅ 找到频道ID: {channel_id}")
            return channel_id, clean_handle
        
        # 方法3: 从 canonical URL 提取
        match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})"', response.text)
        if match:
            channel_id = match.group(1)
            print(f"  ✅ 找到频道ID: {channel_id}")
            return channel_id, clean_handle
        
        # 方法4: 从 browse_id 提取
        match = re.search(r'"browseId":"(UC[a-zA-Z0-9_-]{22})"', response.text)
        if match:
            channel_id = match.group(1)
            print(f"  ✅ 找到频道ID: {channel_id}")
            return channel_id, clean_handle
            
        print(f"  ❌ 无法从页面提取频道ID")
        print(f"  📄 页面长度: {len(response.text)} 字符")
        
    except requests.exceptions.Timeout:
        print(f"  ❌ 请求超时")
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
    
    return None, clean_handle


def get_recent_videos(channel_id: str, channel_name: str, days: int = 7) -> list:
    """
    通过RSS获取频道最近的视频
    """
    videos = []
    
    if not channel_id:
        print(f"  ⚠️ {channel_name}: 无有效频道ID，跳过")
        return videos
    
    # YouTube RSS feed URL
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    print(f"  📡 RSS URL: {rss_url}")
    
    try:
        feed = feedparser.parse(rss_url)
        
        if feed.bozo:
            print(f"  ⚠️ RSS解析警告: {feed.bozo_exception}")
        
        if not feed.entries:
            print(f"  ⚠️ {channel_name}: RSS没有返回任何视频")
            return videos
        
        print(f"  📋 RSS返回 {len(feed.entries)} 个视频条目")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        print(f"  📅 筛选 {cutoff_date.strftime('%Y-%m-%d')} 之后的视频")
        
        for entry in feed.entries:
            # 解析发布时间
            published = datetime(*entry.published_parsed[:6])
            
            if published >= cutoff_date:
                video_id = entry.yt_videoid
                videos.append({
                    "id": video_id,
                    "title": entry.title,
                    "channel": channel_name,
                    "published": published.strftime("%Y-%m-%d"),
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                })
                print(f"    ✅ {entry.title[:40]}... ({published.strftime('%Y-%m-%d')})")
            else:
                print(f"    ⏭️ 跳过旧视频: {entry.title[:30]}... ({published.strftime('%Y-%m-%d')})")
        
        print(f"  📊 {channel_name}: 找到 {len(videos)} 个符合条件的新视频")
        
    except Exception as e:
        print(f"  ❌ 获取 {channel_name} 的视频失败: {e}")
        import traceback
        traceback.print_exc()
    
    return videos


def get_transcript(video_id: str, title: str) -> str:
    """
    获取视频字幕
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 优先级：中文 > 英文 > 其他
        preferred_languages = ['zh-Hans', 'zh-Hant', 'zh', 'en', 'en-US', 'en-GB']
        
        transcript = None
        
        for lang in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except:
                continue
        
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(['zh', 'en'])
            except:
                for t in transcript_list:
                    transcript = t
                    break
        
        if transcript:
            transcript_data = transcript.fetch()
            full_text = " ".join([item['text'] for item in transcript_data])
            print(f"  📝 获取字幕成功: {title[:30]}... ({len(full_text)} 字符)")
            return full_text
            
    except TranscriptsDisabled:
        print(f"  ⚠️ 字幕已禁用: {title[:30]}...")
    except NoTranscriptFound:
        print(f"  ⚠️ 无可用字幕: {title[:30]}...")
    except Exception as e:
        print(f"  ❌ 字幕获取失败: {title[:30]}... - {e}")
    
    return None


def summarize_with_ai(video: dict, transcript: str, api_key: str) -> dict:
    """
    使用Claude API对视频内容进行智能摘要
    """
    if not transcript:
        return {
            "summary": "（该视频无可用字幕）",
            "key_points": [],
            "insights": ""
        }
    
    max_length = 20000
    if len(transcript) > max_length:
        transcript = transcript[:max_length] + "..."
    
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""请分析以下YouTube视频的内容，并提供结构化的摘要。

视频标题：{video['title']}
频道：{video['channel']}
发布日期：{video['published']}

视频字幕内容：
{transcript}

请按以下格式返回（使用JSON格式）：
{{
    "summary": "用2-3句话概括视频的核心内容",
    "key_points": ["要点1", "要点2", "要点3", "要点4", "要点5"],
    "insights": "视频中最有价值或最有趣的观点/信息"
}}

注意：
1. 摘要要简洁但信息量大
2. 要点控制在3-5个，每个要点一句话
3. 洞察要突出视频的独特价值
4. 全部使用中文回复
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            print(f"  🤖 AI摘要完成: {video['title'][:30]}...")
            return result
        
    except Exception as e:
        print(f"  ❌ AI摘要失败: {e}")
    
    return {
        "summary": "摘要生成失败",
        "key_points": [],
        "insights": ""
    }


def generate_email_content(summaries: list, week_start: str, week_end: str) -> str:
    """
    生成邮件HTML内容
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #ff0000;
            border-bottom: 3px solid #ff0000;
            padding-bottom: 10px;
            font-size: 28px;
        }}
        .date-range {{
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .video-card {{
            background: #fafafa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            border-left: 4px solid #ff0000;
        }}
        .video-title {{
            font-size: 18px;
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 5px;
        }}
        .video-title a {{
            color: #1a1a1a;
            text-decoration: none;
        }}
        .video-title a:hover {{
            color: #ff0000;
        }}
        .channel-name {{
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }}
        .summary {{
            margin-bottom: 15px;
            color: #444;
        }}
        .key-points {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .key-points h4 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 14px;
        }}
        .key-points ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .key-points li {{
            margin-bottom: 5px;
            color: #555;
        }}
        .insight {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 6px;
            font-style: italic;
        }}
        .insight::before {{
            content: "💡 ";
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
        }}
        .no-videos {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            padding: 15px;
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
            border-radius: 8px;
            color: white;
        }}
        .stat-item {{
            text-align: center;
            flex: 1;
        }}
        .stat-number {{
            font-size: 24px;
            font-weight: bold;
        }}
        .stat-label {{
            font-size: 12px;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📺 YouTube 周报</h1>
        <div class="date-range">📅 {week_start} ~ {week_end}</div>
"""
    
    if not summaries:
        html += """
        <div class="no-videos">
            <p>🎉 本周你关注的频道没有发布新视频</p>
            <p>享受这份难得的清闲吧！</p>
        </div>
"""
    else:
        channels = set(s['video']['channel'] for s in summaries)
        html += f"""
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(summaries)}</div>
                <div class="stat-label">新视频</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(channels)}</div>
                <div class="stat-label">活跃频道</div>
            </div>
        </div>
"""
        
        for summary_data in summaries:
            video = summary_data['video']
            summary = summary_data['summary']
            
            html += f"""
        <div class="video-card">
            <div class="video-title">
                <a href="{video['url']}" target="_blank">{video['title']}</a>
            </div>
            <div class="channel-name">📺 {video['channel']} · {video['published']}</div>
            <div class="summary">{summary.get('summary', '无摘要')}</div>
"""
            
            if summary.get('key_points'):
                html += """
            <div class="key-points">
                <h4>📌 关键要点</h4>
                <ul>
"""
                for point in summary['key_points']:
                    html += f"                    <li>{point}</li>\n"
                html += """
                </ul>
            </div>
"""
            
            if summary.get('insights'):
                html += f"""
            <div class="insight">{summary['insights']}</div>
"""
            
            html += """
        </div>
"""
    
    html += """
        <div class="footer">
            <p>由 YouTube Digest 自动生成 ❤️</p>
            <p>Powered by Claude AI</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def send_email(config: dict, html_content: str, week_start: str, week_end: str):
    """
    发送邮件
    """
    email_config = config['email']
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📺 YouTube 周报 ({week_start} ~ {week_end})"
    msg['From'] = email_config['sender']
    msg['To'] = email_config['receiver']
    
    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)
    
    try:
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['sender'], email_config['password'])
            server.send_message(msg)
        print("✅ 邮件发送成功！")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def main():
    """
    主函数
    """
    print("=" * 60)
    print("🚀 YouTube 周报生成器启动")
    print("=" * 60)
    
    # 获取配置
    config = get_config()
    
    # 检查必要配置
    if not config['anthropic_api_key']:
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY")
        return
    
    if not config['email']['sender'] or not config['email']['password']:
        print("❌ 错误: 未设置邮箱配置")
        return
    
    if not config['channels']:
        print("❌ 错误: 未设置要关注的频道")
        return
    
    # 计算日期范围
    today = datetime.now()
    week_start = (today - timedelta(days=DAYS_TO_FETCH)).strftime("%m月%d日")
    week_end = today.strftime("%m月%d日")
    
    print(f"\n📅 获取 {week_start} ~ {week_end} 的视频（过去 {DAYS_TO_FETCH} 天）\n")
    
    # 收集所有视频
    all_videos = []
    
    print("=" * 60)
    print("📺 开始获取各频道视频")
    print("=" * 60)
    
    for channel in config['channels']:
        print(f"\n{'─' * 40}")
        print(f"处理频道: {channel}")
        print(f"{'─' * 40}")
        
        # 获取频道ID
        channel_id, channel_name = get_channel_id_from_handle(channel)
        
        if channel_id:
            videos = get_recent_videos(channel_id, channel_name, days=DAYS_TO_FETCH)
            all_videos.extend(videos)
        else:
            print(f"  ❌ 无法获取频道ID，跳过此频道")
    
    print(f"\n{'=' * 60}")
    print(f"📊 共找到 {len(all_videos)} 个新视频")
    print(f"{'=' * 60}")
    
    # 处理每个视频
    summaries = []
    
    for i, video in enumerate(all_videos, 1):
        print(f"\n[{i}/{len(all_videos)}] 处理: {video['title'][:50]}...")
        
        # 获取字幕
        transcript = get_transcript(video['id'], video['title'])
        
        # AI摘要
        summary = summarize_with_ai(video, transcript, config['anthropic_api_key'])
        
        summaries.append({
            'video': video,
            'summary': summary
        })
    
    # 生成邮件内容
    print(f"\n{'=' * 60}")
    print("📧 生成邮件内容...")
    html_content = generate_email_content(summaries, week_start, week_end)
    
    # 发送邮件
    print("📤 发送邮件...")
    send_email(config, html_content, week_start, week_end)
    
    print(f"\n{'=' * 60}")
    print("✅ 周报生成完成！")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
