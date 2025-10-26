import sqlite3
import streamlit as st
import pandas as pd
import os
from typing import List


def get_db_connection(db_path='./MediaCrawler/database/sqlite_tables.db'):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except:
        return None
    
@st.cache_data
def get_statistics():
    conn = get_db_connection()
    if conn is None:
        return None

    cursor = conn.cursor()
    table_counts = {}
    total_records = 0

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        original_tables = [row[0] for row in cursor.fetchall()]

        for original_table in original_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {original_table}")
            current_count = cursor.fetchone()[0]

            table_prefix = original_table.split("_")[0]

            if table_prefix in table_counts:
                table_counts[table_prefix] += current_count
            else:
                table_counts[table_prefix] = current_count

            total_records += current_count

    except Exception as e:
        st.error(f"统计过程出错：{str(e)}")
        return None
    finally:
        if conn:
            conn.close()

    return {
        "table_counts": table_counts,
        "total_records": total_records
    }

@st.cache_data
def get_search_term():
    """
    查询每个平台的检索词（source_keyword），并按“平台+检索词”分组统计数据量
    返回结构：{平台名: {检索词: 总数量, ...}, ...}
    """
    conn = get_db_connection()
    if not conn:
        return None

    cursor = conn.cursor()
    search_term_stats = {}

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        original_tables = [row[0] for row in cursor.fetchall()]

        for table in original_tables:
            platform = table.split("_")[0]

            try:
                cursor.execute(f"""
                    SELECT source_keyword, COUNT(*) AS total 
                    FROM {table} 
                    GROUP BY source_keyword
                """)
                keyword_data = cursor.fetchall()

                for row in keyword_data:
                    keyword = row["source_keyword"] or "未指定检索词"
                    count = row["total"]

                    if platform not in search_term_stats:
                        search_term_stats[platform] = {}

                    if keyword in search_term_stats[platform]:
                        search_term_stats[platform][keyword] += count
                    else:
                        search_term_stats[platform][keyword] = count

            except sqlite3.OperationalError as e:
                continue
            except Exception as e:
                st.error(f"处理表 `{table}` 时出错：{str(e)}")
                continue

    except Exception as e:
        st.error(f"检索词统计失败：{str(e)}")
        return None
    finally:
        if conn:
            conn.close()  # 确保连接关闭

    return search_term_stats

@st.cache_data
def get_table_structure():
    """解析所有表名，返回平台与数据类型的映射关系"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        # 获取所有用户表（排除系统表）
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]

        # 解析表名：按"_"分割为 [平台, 数据类型]（处理格式异常的表名）
        table_info = {}  # 格式：{平台: {数据类型1, 数据类型2, ...}, ...}
        for table in tables:
            parts = table.split("_")
            if len(parts) >= 2:
                platform = parts[0]
                data_type = "_".join(parts[1:])  # 支持数据类型含"_"的情况（如"video_1080p"）
            else:
                # 表名无"_"时，平台为表名本身，数据类型标记为"默认"
                platform = table
                data_type = "默认"

            # 构建平台到数据类型的映射
            if platform not in table_info:
                table_info[platform] = set()
            table_info[platform].add(data_type)

        # 转换为排序后的列表（便于选择框展示）
        for platform in table_info:
            table_info[platform] = sorted(table_info[platform])
        return table_info

    except Exception as e:
        st.error(f"解析表结构失败：{str(e)}")
        return None
    finally:
        if conn:
            conn.close()


def load_table_data(platform, data_type):
    """根据平台和数据类型加载对应表的数据"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        # 拼接表名（平台_数据类型）
        if data_type == "默认":
            table_name = platform  # 无后缀的表直接用平台名
        else:
            table_name = f"{platform}_{data_type}"

        # 查询表中所有数据（可根据需求添加LIMIT限制）
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # 转换为DataFrame
        if rows:
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            return df
        else:
            return None

    except sqlite3.OperationalError as e:
        st.error(f"表 `{table_name}` 不存在或查询失败：{str(e)}")
        return None
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def get_media(platform: str, media_id: str) -> List[str]:
    """
    根据平台和ID查询对应文件夹下的所有媒体文件路径
    
    参数:
        platform: 平台名称（如"weibo"、"douyin"）
        media_id: 媒体唯一ID（对应数据中的id字段）
    
    返回:
        媒体文件路径列表（若文件夹不存在或无文件则返回空列表）
    """
    try:
        media_files = []
        for media_type in ["videos", "images"]:
            base_dir = os.path.join("MediaCrawler", "data", platform, media_type, str(media_id))
            base_dir = os.path.abspath(base_dir)
            if not os.path.exists(base_dir):
                continue
            for filename in os.listdir(base_dir):
                file_path = os.path.join(base_dir, filename)
                media_files.append(file_path)
        media_files.sort()
        return media_files
    except ValueError as ve:
        print(f"参数错误: {str(ve)}")
        return []
    except OSError as oe:
        print(f"文件操作错误: {str(oe)}")
        return []
    except Exception as e:
        print(f"未知错误: {str(e)}")
        return []