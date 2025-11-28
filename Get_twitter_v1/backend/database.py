import os
import json
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


class TweetDatabase:
    def __init__(self):
        load_dotenv()

        self.host = os.getenv("MYSQL_HOST")
        self.user = os.getenv("MYSQL_USER")
        self.password = os.getenv("MYSQL_PASSWORD")
        self.database = os.getenv("MYSQL_DB")

        self.conn = None
        self.connect()
        self.create_table()

    def connect(self):
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("✅ 数据库连接成功")
        except Error as e:
            print(f"❌ 数据库连接失败: {e}")
            raise e

    def create_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS tweets (
            tweet_id VARCHAR(30) PRIMARY KEY,
            username VARCHAR(255),
            text TEXT,
            source VARCHAR(255),
            retweetCount INT DEFAULT 0,
            replyCount INT DEFAULT 0,
            likeCount INT DEFAULT 0,
            quoteCount INT DEFAULT 0,
            viewCount INT DEFAULT 0,
            createdAt VARCHAR(255),
            lang VARCHAR(20),
            bookmarkCount INT DEFAULT 0,
            isReply BOOLEAN,
            inReplyToId VARCHAR(30),
            conversationId VARCHAR(30),
            displayTextRange TEXT,
            inReplyToUserId VARCHAR(30),
            inReplyToUsername VARCHAR(255),
            author JSON,
            raw_tweet JSON,
            ai_summary TEXT
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(create_table_sql)
        cursor.close()
        self.conn.commit()
        print("✅ 数据表检查/创建完成")

    def tweet_exists(self, tweet_id):
        """判断该推文是否已存在"""
        sql = "SELECT tweet_id FROM tweets WHERE tweet_id = %s LIMIT 1"
        cursor = self.conn.cursor()
        cursor.execute(sql, (tweet_id,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    def insert_tweet(self, tweet: dict):
        """插入新推文"""
        sql = """
        INSERT INTO tweets (
            tweet_id, username, text, source,
            retweetCount, replyCount, likeCount, quoteCount, viewCount,
            createdAt, lang, bookmarkCount, isReply,
            inReplyToId, conversationId, displayTextRange,
            inReplyToUserId, inReplyToUsername, author, raw_tweet, ai_summary
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 调试输出，检查数据是否正确
        print(f"🔍 数据库插入数据检查:")
        print(f"   tweet_id: {tweet['tweet_id']}")
        print(f"   retweetCount: {tweet.get('retweets', 0)}")
        print(f"   replyCount: {tweet.get('replies', 0)}")
        print(f"   likeCount: {tweet.get('likes', 0)}")
        print(f"   quoteCount: {tweet.get('quotes', 0)}")
        print(f"   viewCount: {tweet.get('views', 0)}")

        values = (
            tweet["tweet_id"],
            tweet["username"],
            tweet["text"],
            tweet.get("source"),
            tweet.get("retweets", 0),  # 修正字段映射
            tweet.get("replies", 0),   # 修正字段映射
            tweet.get("likes", 0),     # 修正字段映射
            tweet.get("quotes", 0),    # 修正字段映射
            tweet.get("views", 0),     # 修正字段映射
            tweet.get("created_at"),   # 使用转换后的北京时间
            tweet.get("lang"),
            tweet.get("bookmarkCount", 0),
            tweet.get("isReply", False),
            tweet.get("inReplyToId"),
            tweet.get("conversationId"),
            json.dumps(tweet.get("displayTextRange"), ensure_ascii=False) if tweet.get("displayTextRange") else None,
            tweet.get("inReplyToUserId"),
            tweet.get("inReplyToUsername"),
            json.dumps(tweet.get("author"), ensure_ascii=False) if tweet.get("author") else None,
            json.dumps(tweet.get("raw_tweet"), ensure_ascii=False) if tweet.get("raw_tweet") else None,
            tweet.get("ai_summary", "")  # 添加AI摘要字段
        )

        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, values)
            self.conn.commit()
            print(f"✅ 数据库插入成功: tweet_id={tweet['tweet_id']}")
            print(f"✅ 插入的互动数据 - 点赞: {tweet.get('likes', 0)}, 转推: {tweet.get('retweets', 0)}, 回复: {tweet.get('replies', 0)}")
        except Error as e:
            print(f"❌ 插入失败: {e}")
            # 打印详细的错误信息
            print(f"❌ 错误详情: {e}")
        finally:
            cursor.close()