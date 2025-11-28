import os
import requests
import json
import time
import hmac
import hashlib
import base64
from urllib.parse import quote_plus
from dotenv import load_dotenv


class DingTalkBot:
    def __init__(self):
        # 加载环境变量
        load_dotenv()

        # 从环境变量获取钉钉机器人配置
        self.access_token = os.getenv('DINGTALK_ACCESS_TOKEN')
        self.secret = os.getenv('DINGTALK_SECRET',
                                'SEC1e2b648e1af505a61e4b6f0e357b2be254906db38dfe28d712d2f8d172d9f161')

        if not self.access_token:
            raise ValueError("请在.env文件中配置DINGTALK_ACCESS_TOKEN")

    def generate_signature(self):
        """生成钉钉机器人签名"""
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f'{timestamp}\n{self.secret}'

        # 使用HMAC-SHA256算法计算签名
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Base64编码并进行URL编码
        sign = quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def get_webhook_url(self):
        """获取带签名的完整Webhook URL"""
        timestamp, sign = self.generate_signature()
        webhook_url = f'https://oapi.dingtalk.com/robot/send?access_token={self.access_token}&timestamp={timestamp}&sign={sign}'
        return webhook_url

    def send_markdown_message(self, title, text, at_mobiles=None, is_at_all=False):
        """
        发送Markdown格式消息到钉钉群
        """
        headers = {
            'Content-Type': 'application/json'
        }

        # 获取带签名的Webhook URL
        webhook_url = self.get_webhook_url()

        # 构建消息数据
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": is_at_all
            }
        }

        try:
            response = requests.post(
                webhook_url,
                headers=headers,
                data=json.dumps(data),
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    return True
                else:
                    print(f"❌ 钉钉消息发送失败: {result.get('errmsg')}")
                    return False
            else:
                print(f"❌ 钉钉API请求失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 钉钉消息发送异常: {e}")
            return False

    def format_tweet_message(self, tweet_data):
        """
        格式化推文数据为钉钉消息
        """
        username = tweet_data.get('username', '')
        created_at = tweet_data.get('created_at', '')
        text = tweet_data.get('text', '')
        likes = tweet_data.get('likes', 0)
        retweets = tweet_data.get('retweets', 0)
        replies = tweet_data.get('replies', 0)
        views = tweet_data.get('views', 0)
        ai_summary = tweet_data.get('ai_summary', '')

        # 构建标题
        title = f"🔥 新推文提醒 - @{username}"

        # 构建Markdown内容
        text_content = f"""## 🔥 捕获到新推文！

**👤 用户:** @{username}  
**🕐 时间:** {created_at} (北京时间)  

**📝 内容:**  
{text}  

**📊 互动数据:**  
- 👍 点赞: {likes}  
- 🔄 转推: {retweets}  
- 💬 回复: {replies}  
- 👁️ 浏览: {views}  

**🤖 AI摘要:**  
{ai_summary}  

---
*来自 Twitter 实时监控机器人*"""

        return title, text_content

    def send_tweet_notification(self, tweet_data):
        """
        发送推文通知到钉钉
        """
        title, content = self.format_tweet_message(tweet_data)
        return self.send_markdown_message(title, content)


# 单例模式，便于全局使用
dingtalk_bot = DingTalkBot()