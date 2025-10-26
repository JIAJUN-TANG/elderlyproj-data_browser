import streamlit as st
from utils.data_utils import get_search_term
import pandas as pd


st.title("数据分析")

with st.spinner("正在统计检索情况", show_time=True):
    term_stats = get_search_term()

st.subheader("采集情况")
if term_stats:
    unique_terms = set()
    for platform, keywords in term_stats.items():
        unique_terms.update(keywords.keys())
    unique_terms_sorted = sorted(unique_terms)
    st.write(f"已使用的检索词：**{', '.join(unique_terms_sorted)}**")

    table_data = []
    for platform, keywords in term_stats.items():
        for keyword, count in keywords.items():
            table_data.append({
                "平台": platform,
                "检索词": keyword,
                "数据量": count
            })

    df = pd.DataFrame(table_data)
    # 按平台和数据量排序（默认按平台升序、数据量降序）
    df = df.sort_values(by=["平台", "数据量"], ascending=[True, False])
    # 格式化数据量为千分位显示
    df["数据量"] = df["数据量"].apply(lambda x: f"{x:,}")
    
    st.dataframe(
        df,
        width="stretch",  # 自适应宽度
        hide_index=True,  # 隐藏索引列
        column_config={
            "平台": st.column_config.TextColumn("平台名称"),
            "检索词": st.column_config.TextColumn("检索关键词"),
            "数据量": st.column_config.TextColumn("采集数据量")
        }
    )
else:
    st.write("暂无数据")