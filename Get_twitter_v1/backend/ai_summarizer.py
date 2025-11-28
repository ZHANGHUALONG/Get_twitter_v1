# import os
# import json
# from openai import OpenAI
# from dotenv import load_dotenv
#
#
# class AISummarizer:
#     def __init__(self):
#         # 加载环境变量
#         load_dotenv()
#
#         # 获取阿里云百炼API密钥
#         self.api_key = os.getenv('DASHSCOPE_API_KEY')
#         if not self.api_key:
#             raise ValueError("请在.env文件中配置DASHSCOPE_API_KEY")
#
#         # 初始化阿里云百炼客户端 [citation:1]
#         self.client = OpenAI(
#             api_key=self.api_key,
#             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 北京地域
#         )
#
#         # 设置模型
#         self.model = "qwen-plus"  # 可根据需要改为 qwen-max 或 qwen-flash
#
#     def generate_summary(self, formatted_tweet):
#         """
#         使用阿里云百炼大模型生成推文摘要
#
#         Args:
#             formatted_tweet: 格式化后的推文数据
#
#         Returns:
#             str: 生成的摘要文本
#         """
#         try:
#             # 构建推文内容
#             tweet_content = formatted_tweet.get('text', '')
#             username = formatted_tweet.get('username', '')
#             metrics = formatted_tweet.get('public_metrics', {})
#
#             # 构建提示词
#             prompt = f"""
# 请对以下推文内容进行摘要分析：
#
# 发布者: @{username}
# 推文内容: {tweet_content}
# 互动数据: 点赞{metrics.get('like_count', 0)} | 转推{metrics.get('retweet_count', 0)} | 回复{metrics.get('reply_count', 0)}
#
# 请从以下角度生成一个简洁的摘要：
# 1. 主要内容概括
# 2. 情感倾向分析
# 3. 可能的话题标签建议
# 4. 相关话题热度情况
#
# 要求：回复内容为纯文本，不超过150字。
# """
#
#             # 调用阿里云百炼API [citation:1]
#             response = self.client.chat.completions.create(
#                 model=self.model,
#                 messages=[
#                     {"role": "system", "content": "你是一个专业的社交媒体内容分析师，擅长用简洁的语言概括推文内容。"},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.3,  # 较低的温度值以获得更稳定的输出
#                 max_tokens=300  # 限制输出长度
#             )
#
#             # 提取生成的摘要
#             summary = response.choices[0].message.content.strip()
#             return summary
#
#         except Exception as e:
#             print(f"AI摘要生成失败: {e}")
#             return f"摘要生成失败: {str(e)}"
#
#     def batch_summarize(self, tweets_list):
#         """
#         批量生成推文摘要
#
#         Args:
#             tweets_list: 推文数据列表
#
#         Returns:
#             list: 包含摘要的推文列表
#         """
#         summarized_tweets = []
#
#         for tweet in tweets_list:
#             print(f"正在为 @{tweet.get('username', '')} 的推文生成AI摘要...")
#
#             # 生成摘要
#             summary = self.generate_summary(tweet)
#
#             # 将摘要添加到推文数据中
#             tweet_with_summary = tweet.copy()
#             tweet_with_summary['ai_summary'] = summary
#
#             summarized_tweets.append(tweet_with_summary)
#
#             # 添加延迟避免API限制
#             import time
#             time.sleep(1)
#
#         return summarized_tweets
import os
import json
from openai import OpenAI
from dotenv import load_dotenv


class AISummarizer:
    def __init__(self):
        # 加载环境变量
        load_dotenv()

        # 获取阿里云百炼API密钥
        self.api_key = os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError("请在.env文件中配置DASHSCOPE_API_KEY")

        # 初始化阿里云百炼客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 北京地域
        )

        # 设置模型
        self.model = "qwen-plus"  # 可根据需要改为 qwen-max 或 qwen-flash

    def generate_summary(self, formatted_tweet):
        """
        使用阿里云百炼大模型生成推文摘要

        Args:
            formatted_tweet: 格式化后的推文数据

        Returns:
            str: 生成的摘要文本
        """
        try:
            # 构建推文内容
            tweet_content = formatted_tweet.get('text', '')
            username = formatted_tweet.get('username', '')
            metrics = formatted_tweet.get('public_metrics', {})

            # 构建提示词
            prompt = f"""
请对以下推文内容进行摘要分析：

发布者: @{username}
推文内容: {tweet_content}
互动数据: 点赞{metrics.get('like_count', 0)} | 转推{metrics.get('retweet_count', 0)} | 回复{metrics.get('reply_count', 0)}

请从以下角度生成一个简洁的摘要：
1. 主要内容概括
2. 情感倾向分析
3. 可能的话题标签建议
4. 相关话题热度情况

要求：回复内容为纯文本，不超过150字。
"""

            # 调用阿里云百炼API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的社交媒体内容分析师，擅长用简洁的语言概括推文内容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 较低的温度值以获得更稳定的输出
                max_tokens=300  # 限制输出长度
            )

            # 提取生成的摘要
            summary = response.choices[0].message.content.strip()
            return summary

        except Exception as e:
            print(f"AI摘要生成失败: {e}")
            return f"摘要生成失败: {str(e)}"

    def batch_summarize(self, tweets_list):
        """
        批量生成推文摘要 (保留此方法用于兼容性)

        Args:
            tweets_list: 推文数据列表

        Returns:
            list: 包含摘要的推文列表
        """
        summarized_tweets = []

        for tweet in tweets_list:
            print(f"正在为 @{tweet.get('username', '')} 的推文生成AI摘要...")

            # 生成摘要
            summary = self.generate_summary(tweet)

            # 将摘要添加到推文数据中
            tweet_with_summary = tweet.copy()
            tweet_with_summary['ai_summary'] = summary

            summarized_tweets.append(tweet_with_summary)

            # 添加延迟避免API限制
            import time
            time.sleep(1)

        return summarized_tweets