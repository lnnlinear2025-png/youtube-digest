
    import os
    import json
    import smtplib
    import feedparser
    import requests
    import re
    import subprocess
    import tempfile
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime, timedelta
    from youtube_transcript_api import YouTubeTranscriptApi
    import anthropic

    # ============= 配置 =============
    DAYS_TO_FETCH = int(os.environ.get("DAYS_TO_FETCH", "7"))

    # 直接读取环境变量
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "").strip()
    EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "").strip()
    EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "").strip()
    YOUTUBE_CHANNELS_STR = os.environ.get("YOUTUBE_CHANNELS", "[]").strip()

    print("=" * 60)
    print("🚀 YouTube 周报生成器启动")
    print("=" * 60)
    print("\n🔍 检查环境变量...")
    print(f"  ANTHROPIC_API_KEY: {'✅ 已设置 (' + ANTHROPIC_API_KEY[:10] + '...)' if ANTHROPIC_API_KEY else '❌ 未设置'}")
    print(f"  EMAIL_SENDER: {'✅ 已设置' if EMAIL_SENDER else '❌ 未设置'}")
    print(f"  EMAIL_PASSWORD: {'✅ 已设置' if EMAIL_PASSWORD else '❌ 未设置'}")
    print(f"  EMAIL_RECEIVER: {'✅ 已设置' if EMAIL_RECEIVER else '❌ 未设置'}")
    print(f"  GROQ_API_KEY: {'✅ 已设置 (' + GROQ_API_KEY[:10] + '...)' if GROQ_API_KEY else '⚠️ 未设置（无字幕视频将跳过）'}")
    print(f"  YOUTUBE_CHANNELS: {YOUTUBE_CHANNELS_STR}")
    print(f"  DAYS_TO_FETCH: {DAYS_TO_FETCH} 天")

    # 解析频道列表
    try:
        CHANNELS = json.loads(YOUTUBE_CHANNELS_STR)
        print(f"  ✅ 解析到 {len(CHANNELS)} 个频道")
    except:
        CHANNELS = []
        print("  ❌ 频道解析失败")

    # ============= Whisper 语音识别 =============

    def download_audio(video_id, title):
        """下载视频音频"""
        print(f"  🎵 正在下载音频...")
        try:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"{video_id}.mp3")
            
            if os.path.exists(output_path):
                os.remove(output_path)
            
            cmd = [
                "yt-dlp", "-x", "--audio-format", "mp3",
                "--audio-quality", "5", "-o", output_path,
                "--no-playlist", "--quiet",
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  ✅ 音频下载成功: {file_size:.1f} MB")
                return output_path
            else:
                print(f"  ❌ 音频下载失败")
                return None
        except Exception as e:
            print(f"  ❌ 音频下载错误: {e}")
            return None


    def transcribe_with_whisper(audio_path, title):
        """使用Groq Whisper进行语音识别"""
        if not GROQ_API_KEY:
            print(f"  ⚠️ 未配置GROQ_API_KEY，跳过语音识别")
            return None
        
        print(f"  🎤 正在进行语音识别...")
        
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    response_format="text",
                    language="en"
                )
            
            if transcription:
                print(f"  ✅ 语音识别成功: {len(transcription)} 字符")
                return transcription
        except ImportError:
            print(f"  ❌ Groq库未安装")
        except Exception as e:
            print(f"  ❌ 语音识别失败: {e}")
        finally:
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except:
                pass
        
        return None


    # ============= 核心功能 =============

    def get_channel_id(handle):
        """获取频道ID"""
        if handle.startswith("UC") and len(handle) == 24:
            return handle, handle
        
        clean = handle.lstrip("@")
        print(f"  🔍 获取 @{clean} 的频道ID...")
        
        try:
            url = f"https://www.youtube.com/@{clean}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
            response = requests.get(url, headers=headers, timeout=15)
            
            patterns = [
                r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
                r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
                r'"browseId":"(UC[a-zA-Z0-9_-]{22})"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    channel_id = match.group(1)
                    print(f"  ✅ 频道ID: {channel_id}")
                    return channel_id, clean
            
            print(f"  ❌ 无法获取频道ID")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
        
        return None, clean


    def get_recent_videos(channel_id, channel_name, days=7):
        """获取最近视频"""
        videos = []
        if not channel_id:
            return videos
        
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        try:
            feed = feedparser.parse(rss_url)
            cutoff = datetime.now() - timedelta(days=days)
            
            for entry in feed.entries:
                published = datetime(*entry.published_parsed[:6])
                if published >= cutoff:
                    videos.append({
                        "id": entry.yt_videoid,
                        "title": entry.title,
                        "channel": channel_name,
                        "published": published.strftime("%Y-%m-%d"),
                        "url": f"https://www.youtube.com/watch?v={entry.yt_videoid}"
                    })
                    print(f"    ✅ {entry.title[:40]}...")
            
            print(f"  📊 找到 {len(videos)} 个新视频")
        except Exception as e:
            print(f"  ❌ 获取视频失败: {e}")
        
        return videos


    def get_transcript(video_id, title):
        """获取字幕或语音识别"""
        # 尝试获取字幕
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['zh-Hans', 'zh-Hant', 'zh', 'en', 'en-US', 'en-GB']
            )
            text = " ".join([item['text'] for item in transcript_data])
            print(f"  📝 字幕获取成功: {len(text)} 字符")
            return text
        except Exception as e:
            print(f"  ⚠️ 无字幕，尝试语音识别...")
        
        # 尝试Whisper语音识别
        if GROQ_API_KEY:
            audio_path = download_audio(video_id, title)
            if audio_path:
                return transcribe_with_whisper(audio_path, title)
        else:
            print(f"  ⚠️ 未配置GROQ_API_KEY，跳过语音识别")
        
        return None


    def summarize_with_ai(video, transcript):
        """AI摘要"""
        if not transcript:
            return {"summary": "（无可用字幕且语音识别失败）", "key_points": [], "insights": ""}
        
        if len(transcript) > 20000:
            transcript = transcript[:20000] + "..."
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        prompt = f"""分析YouTube视频内容，返回JSON格式：

    视频：{video['title']}
    频道：{video['channel']}

    字幕：{transcript}

    返回格式：
    {{"summary": "2-3句概括", "key_points": ["要点1", "要点2", "要点3"], "insights": "最有价值的观点"}}

    用中文回复。"""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = message.content[0].text
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
                print(f"  🤖 AI摘要完成")
                return result
        except Exception as e:
            print(f"  ❌ AI摘要失败: {e}")
        
        return {"summary": "摘要生成失败", "key_points": [], "insights": ""}


    def generate_email(summaries, week_start, week_end):
        """生成邮件HTML"""
        html = f"""<!DOCTYPE html>
    <html><head><meta charset="UTF-8">
    <style>
    body{{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px;background:#f5f5f5}}
    .container{{background:white;border-radius:12px;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
    h1{{color:#ff0000;border-bottom:3px solid #ff0000;padding-bottom:10px}}
    .video-card{{background:#fafafa;border-radius:8px;padding:20px;margin-bottom:20px;border-left:4px solid #ff0000}}
    .video-title{{font-size:18px;font-weight:bold}}
    .video-title a{{color:#1a1a1a;text-decoration:none}}
    .channel{{color:#666;font-size:14px;margin:5px 0 15px}}
    .key-points{{background:white;padding:15px;border-radius:6px;margin:10px 0}}
    .insight{{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:15px;border-radius:6px}}
    .footer{{text-align:center;margin-top:30px;color:#999;font-size:12px}}
    .stats{{display:flex;gap:20px;margin-bottom:30px;padding:15px;background:linear-gradient(135deg,#ff416c,#ff4b2b);border-radius:8px;color:white}}
    .stat-item{{text-align:center;flex:1}}
    .stat-number{{font-size:24px;font-weight:bold}}
    </style></head>
    <body><div class="container">
    <h1>📺 YouTube 周报</h1>
    <p>📅 {week_start} ~ {week_end}</p>"""

        if summaries:
            channels = set(s['video']['channel'] for s in summaries)
            html += f'<div class="stats"><div class="stat-item"><div class="stat-number">{len(summaries)}</div><div>新视频</div></div><div class="stat-item"><div class="stat-number">{len(channels)}</div><div>活跃频道</div></div></div>'
            
            for s in summaries:
                v, sm = s['video'], s['summary']
                html += f'<div class="video-card"><div class="video-title"><a href="{v["url"]}">{v["title"]}</a></div><div class="channel">📺 {v["channel"]} · {v["published"]}</div><p>{sm.get("summary","")}</p>'
                if sm.get("key_points"):
                    html += '<div class="key-points"><b>📌 关键要点</b><ul>'
                    for p in sm["key_points"]:
                        html += f'<li>{p}</li>'
                    html += '</ul></div>'
                if sm.get("insights"):
                    html += f'<div class="insight">💡 {sm["insights"]}</div>'
                html += '</div>'
        else:
            html += '<p style="text-align:center;padding:40px">🎉 本周没有新视频</p>'
        
        html += '<div class="footer">由 YouTube Digest 自动生成 ❤️</div></div></body></html>'
        return html


    def send_email(html, week_start, week_end):
        """发送邮件"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📺 YouTube 周报 ({week_start} ~ {week_end})"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
            print("✅ 邮件发送成功！")
            return True
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False


    def main():
        """主函数"""
        if not ANTHROPIC_API_KEY or not EMAIL_SENDER or not EMAIL_PASSWORD or not CHANNELS:
            print("❌ 缺少必要配置，退出")
            return
        
        today = datetime.now()
        week_start = (today - timedelta(days=DAYS_TO_FETCH)).strftime("%m月%d日")
        week_end = today.strftime("%m月%d日")
        
        print(f"\n📅 获取过去 {DAYS_TO_FETCH} 天的视频\n")
        
        # 获取所有视频
        all_videos = []
        for channel in CHANNELS:
            print(f"\n{'─'*40}\n处理: {channel}\n{'─'*40}")
            channel_id, name = get_channel_id(channel)
            if channel_id:
                videos = get_recent_videos(channel_id, name, DAYS_TO_FETCH)
                all_videos.extend(videos)
        
        print(f"\n📊 共找到 {len(all_videos)} 个新视频\n")
        
        # 处理每个视频
        summaries = []
        for i, video in enumerate(all_videos, 1):
            print(f"\n[{i}/{len(all_videos)}] {video['title'][:50]}...")
            transcript = get_transcript(video['id'], video['title'])
            summary = summarize_with_ai(video, transcript)
            summaries.append({'video': video, 'summary': summary})
        
        # 发送邮件
        print("\n📧 生成并发送邮件...")
        html = generate_email(summaries, week_start, week_end)
        send_email(html, week_start, week_end)
        
        print("\n" + "="*60)
        print("✅ 完成！")
        print("="*60)


    if __name__ == "__main__":
        main()
