import os
import requests
import time
import signal
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from database import TweetDatabase
from ai_summarizer import AISummarizer
from dingtalk_bot import dingtalk_bot


class TwitterAPIIOMonitor:
    def __init__(self):
        # 加载环境变量
        load_dotenv()

        self.api_key = os.getenv("TWITTER_API_KEY")
        if not self.api_key:
            raise ValueError("请在.env配置TWITTER_API_KEY")

        self.base_url = "https://api.twitterapi.io"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # 🔧 从环境变量读取多个博主
        target_users_str = os.getenv("TARGET_USERS", "whyyoutouzhele")
        self.target_users = [user.strip() for user in target_users_str.split(",") if user.strip()]

        # 🔧 从环境变量读取监控配置
        self.monitor_interval = int(os.getenv("MONITOR_INTERVAL", "300"))  # 默认5分钟
        # 🔧 修改：默认只获取5条最新推文，节省token
        self.max_tweets_per_request = int(os.getenv("MAX_TWEETS_PER_REQUEST", "5"))

        # 控制程序运行的标志
        self.running = True

        # 设置信号处理，支持优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.db = TweetDatabase()  # 初始化数据库模块
        self.ai_summarizer = AISummarizer()  # 初始化AI摘要模块

        print(f"🎯 监控目标: {', '.join(['@' + user for user in self.target_users])}")
        print(f"⏰ 监控间隔: {self.monitor_interval} 秒")
        print(f"📊 每次获取: {self.max_tweets_per_request} 条推文 (节省token模式)")
        print(f"💰 预计每周期消耗: {len(self.target_users) * 1} 次API调用")

    def signal_handler(self, signum, frame):
        """处理退出信号"""
        print(f"\n🛑 收到退出信号，正在停止监控...")
        self.running = False

    def get_latest_tweets(self, username, limit=None):
        """获取用户最新推文"""
        if limit is None:
            limit = self.max_tweets_per_request

        endpoint = f"{self.base_url}/twitter/tweet/advanced_search"

        params = {
            "query": f"from:{username}",
            "queryType": "Latest",
            "limit": limit
        }

        try:
            print(f"📡 正在获取 @{username} 的最新 {limit} 条推文...")
            resp = requests.get(endpoint, headers=self.headers, params=params, timeout=30)

            if resp.status_code != 200:
                print(f"❌ 请求失败: {resp.status_code} - {resp.text}")
                return []

            data = resp.json()
            tweets = data.get("tweets", []) or data.get("data", [])

            print(f"✅ 成功获取 @{username} 的 {len(tweets)} 条推文")
            return tweets

        except Exception as e:
            print(f"❌ 获取 @{username} 最新推文失败: {e}")
            return []

    def format_tweet(self, tweet, username):
        """标准化推文"""
        tweet_id = tweet.get("id")
        text = tweet.get("text", "")

        # 时间处理 - 转换为北京时间
        created_at_raw = tweet.get('createdAt')
        beijing_time = created_at_raw

        if created_at_raw:
            try:
                # 解析格式：'Sat Nov 22 04:00:00 +0000 2025'
                dt = datetime.strptime(created_at_raw, '%a %b %d %H:%M:%S %z %Y')
                # 转换为UTC+8北京时间
                beijing_tz = timezone(timedelta(hours=8))
                dt_beijing = dt.astimezone(beijing_tz)
                beijing_time = dt_beijing.strftime("%Y-%m-%d %H:%M:%S")
                print(f"🕐 时间转换: {created_at_raw} -> {beijing_time} (北京时间)")
            except Exception as e:
                try:
                    # 尝试ISO格式
                    dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
                    beijing_tz = timezone(timedelta(hours=8))
                    dt_beijing = dt.astimezone(beijing_tz)
                    beijing_time = dt_beijing.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"🕐 时间转换(ISO): {created_at_raw} -> {beijing_time} (北京时间)")
                except Exception as e2:
                    print(f"⚠️ 时间解析失败: {created_at_raw}, 错误: {e2}")
                    beijing_time = created_at_raw

        # 互动数据 - 确保正确提取所有字段
        likes = tweet.get('likeCount', 0) or tweet.get('favorite_count', 0)
        retweets = tweet.get('retweetCount', 0)
        replies = tweet.get('replyCount', 0)
        quotes = tweet.get('quoteCount', 0)
        views = tweet.get('viewCount', 0)

        # 打印调试信息
        print(
            f"📊 原始互动数据 - 点赞: {tweet.get('likeCount')}, 转推: {tweet.get('retweetCount')}, 回复: {tweet.get('replyCount')}, 引用: {tweet.get('quoteCount')}, 浏览: {tweet.get('viewCount')}")
        print(f"📊 处理后互动数据 - 点赞: {likes}, 转推: {retweets}, 回复: {replies}, 引用: {quotes}, 浏览: {views}")

        return {
            "username": username,
            "tweet_id": tweet_id,
            "text": text,
            "created_at": beijing_time,  # 使用北京时间
            "raw_created_at": created_at_raw,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "quotes": quotes,
            "views": views,
            "entities": tweet.get("entities", {}),
            "attachments": tweet.get("attachments", {}),
            "geo": tweet.get("geo", {}),
            "source": tweet.get("source"),
            "lang": tweet.get("lang"),
            "possibly_sensitive": tweet.get("possibly_sensitive", False),
            "public_metrics": {
                'like_count': likes,
                'retweet_count': retweets,
                'reply_count': replies,
                'quote_count': quotes,
                'view_count': views
            },
            "raw_tweet": tweet
        }

    def process_single_tweet(self, tweet_data):
        """处理单条推文 - 生成AI摘要并立即推送"""
        print("\n" + "=" * 60)
        print("🔥 捕获到新推文！")
        print(f"👤 用户: @{tweet_data['username']}")
        print(f"🕐 时间: {tweet_data['created_at']} (北京时间)")
        print(f"📝 内容: {tweet_data['text'][:100]}{'...' if len(tweet_data['text']) > 100 else ''}")
        print(
            f"📊 互动: 👍 {tweet_data['likes']} | 🔄 {tweet_data['retweets']} | 💬 {tweet_data['replies']} | 👁️ {tweet_data['views']}")

        # 立即生成AI摘要
        print("🤖 正在生成AI摘要...")
        ai_summary = self.ai_summarizer.generate_summary(tweet_data)
        tweet_data['ai_summary'] = ai_summary

        print("🤖 AI摘要:")
        print(f"   {ai_summary}")
        print("=" * 60)

        # 写入数据库
        self.db.insert_tweet(tweet_data)

        # 立即发送钉钉通知
        print("📤 正在发送钉钉通知...")
        success = dingtalk_bot.send_tweet_notification(tweet_data)
        if success:
            print("✅ 钉钉通知发送成功")
        else:
            print("❌ 钉钉通知发送失败")

        # 添加延迟避免频繁请求
        time.sleep(2)

        return True

    def process_new_tweets(self, formatted_tweets):
        """处理新推文 - 逐条处理并立即推送"""
        if not formatted_tweets:
            return 0

        print(f"🤖 发现 {len(formatted_tweets)} 条新推文，开始逐条处理...")

        processed_count = 0
        for tweet in formatted_tweets:
            if not self.running:
                break

            try:
                self.process_single_tweet(tweet)
                processed_count += 1
            except Exception as e:
                print(f"❌ 处理推文失败: {e}")
                # 继续处理下一条推文
                continue

        return processed_count

    def monitor_single_cycle(self):
        """执行单次监控循环"""
        print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始监控循环...")

        all_new_tweets = []
        total_checked = 0

        for username in self.target_users:
            if not self.running:
                break

            print(f"🔍 正在检查 @{username} ...")
            tweets = self.get_latest_tweets(username)
            total_checked += len(tweets)

            new_tweets = []
            for tweet in tweets:
                if not self.running:
                    break

                tweet_id = tweet.get("id")
                if tweet_id and not self.db.tweet_exists(tweet_id):
                    formatted = self.format_tweet(tweet, username)
                    new_tweets.append(formatted)

            if new_tweets:
                print(f"✅ @{username}: 发现 {len(new_tweets)} 条新推文")
                all_new_tweets.extend(new_tweets)
            else:
                print(f"ℹ️  @{username}: 没有新推文")

        # 处理所有新推文
        if all_new_tweets:
            processed_count = self.process_new_tweets(all_new_tweets)
            print(f"🎉 本轮监控完成: 成功处理 {processed_count}/{len(all_new_tweets)} 条新推文")
        else:
            print(f"📭 本轮监控完成: 没有发现新推文 (检查了 {total_checked} 条推文)")

    def start_real_time_monitoring(self):
        """启动实时监控"""
        print("🚀 启动 Twitter 实时监控...")
        print("💡 按 Ctrl+C 停止监控")

        cycle_count = 0

        while self.running:
            cycle_count += 1
            print(f"\n{'=' * 50}")
            print(f"📈 监控周期 #{cycle_count}")
            print(f"{'=' * 50}")

            try:
                self.monitor_single_cycle()
            except Exception as e:
                print(f"❌ 监控周期执行出错: {e}")
                # 继续运行，不退出

            if not self.running:
                break

            # 等待下一个监控周期
            print(f"\n⏳ 等待 {self.monitor_interval} 秒后继续监控...")
            for i in range(self.monitor_interval):
                if not self.running:
                    break
                time.sleep(1)
                if i % 30 == 0 and i > 0:  # 每30秒打印一次等待状态
                    remaining = self.monitor_interval - i
                    print(f"  等待中... {remaining} 秒后继续")

        print("\n🛑 监控已停止")


def main():
    try:
        monitor = TwitterAPIIOMonitor()
        monitor.start_real_time_monitoring()
    except KeyboardInterrupt:
        print("\n👋 用户主动停止监控")
    except Exception as e:
        print(f"💥 程序运行出错: {e}")
    finally:
        print("🎯 监控程序已退出")


if __name__ == "__main__":
    main()