import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. 页面配置
# -----------------------------------------------------------------------------
st.set_page_config(page_title="A股PE胜率热力图", page_icon="🔥", layout="wide")

# -----------------------------------------------------------------------------
# 2. 核心数据获取
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_data_via_akshare():
    try:
        df = ak.stock_a_ttm_lyr()
        
        # 清洗列名
        rename_map = {
            'averagePETTM': 'pe',
            'averagePeTtm': 'pe',
            '平均市盈率': 'pe'
        }
        df.rename(columns=rename_map, inplace=True)

        if 'pe' not in df.columns:
            st.error(f"❌ 数据解析失败，列名: {df.columns.tolist()}")
            return None

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # --- 计算逻辑 ---
        # rank(pct=True) 计算百分位 (0.0 - 1.0) -> * 100
        df['percentile'] = df['pe'].rank(pct=True) * 100
        
        # 胜率 = 100 - 百分位
        df['win_rate'] = 100 - df['percentile']
        
        return df[['date', 'pe', 'percentile', 'win_rate']]
        
    except Exception as e:
        st.error(f"❌ 获取数据发生异常: {e}")
        return None

# -----------------------------------------------------------------------------
# 3. 辅助函数
# -----------------------------------------------------------------------------
def get_status(win_rate):
    # 根据胜率判断状态
    if win_rate >= 80: return "极高胜率 (黄金坑)", "success"
    if win_rate >= 50: return "胜率尚可 (定投区)", "info"
    return "胜率较低 (风险区)", "error"

# -----------------------------------------------------------------------------
# 4. 主程序
# -----------------------------------------------------------------------------
def main():
    st.title("🔥 A股全市场 PE 胜率热力图")
    st.markdown("""
    > **颜色说明**：
    > 🔴 **红色点**：代表 **高胜率 (>80%)**，即市场极度低估，适合贪婪。  
    > 🔵 **蓝色点**：代表 **低胜率 (<50%)**，即市场高估，注意风险。
    """)

    with st.spinner('正在计算胜率模型...'):
        df = get_data_via_akshare()

    if df is not None:
        latest = df.iloc[-1]
        cur_pe = latest['pe']
        cur_win = latest['win_rate']
        cur_date = latest['date'].strftime('%Y-%m-%d')
        
        status_txt, status_color = get_status(cur_win)
        
        # --- 顶部指标 ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("数据日期", cur_date)
        col2.metric("当前PE", f"{cur_pe:.2f}")
        col3.metric("理论胜率", f"{cur_win:.2f}%", delta=f"{cur_win-50:.1f}%")
        col4.metric("市场状态", status_txt) # 直接显示文字状态

        # --- 核心图表逻辑 ---
        
        # 1. 计算关键阈值：胜率80% 和 90% 对应的 PE 是多少？
        # 胜率90% = 百分位10% 的位置
        pe_win_90 = df['pe'].quantile(0.10)
        # 胜率80% = 百分位20% 的位置
        pe_win_80 = df['pe'].quantile(0.20)
        
        # 2. 绘图：使用 scatter (散点) 来实现颜色渐变
        # 因为普通的 line (折线) 只能是一种颜色，散点可以每个点不同颜色
        fig = px.scatter(df, x='date', y='pe', 
                         color='win_rate',   # 颜色由胜率决定
                         # 颜色盘：从蓝(冷/低胜率) -> 黄 -> 红(热/高胜率)
                         color_continuous_scale='RdYlBu_r', 
                         title="A股PE历史走势 (颜色代表胜率)",
                         hover_data={'percentile':':.2f', 'win_rate':':.2f'})
        
        # 3. 添加辅助线 (80% 和 90% 胜率线)
        fig.add_hline(y=pe_win_90, line_dash="dash", line_color="red", 
                      annotation_text=f"90%胜率线 (PE={pe_win_90:.2f})", annotation_position="bottom right")
        
        fig.add_hline(y=pe_win_80, line_dash="dot", line_color="orange", 
                      annotation_text=f"80%胜率线 (PE={pe_win_80:.2f})", annotation_position="bottom right")
        
        # 4. 标记当前位置
        fig.add_annotation(x=latest['date'], y=cur_pe, text="当前", showarrow=True, arrowhead=1, yshift=10)

        st.plotly_chart(fig, use_container_width=True)

        # --- 底部表格 ---
        st.markdown("### 📋 每日胜率监控表")
        df_display = df.sort_values('date', ascending=False)
        
        # 定义简单的样式函数：高胜率标红，低胜率标绿
        def highlight_win_rate(val):
            color = 'red' if val >= 80 else 'black'
            weight = 'bold' if val >= 80 else 'normal'
            return f'color: {color}; font-weight: {weight}'

        st.dataframe(
            df_display.style.map(highlight_win_rate, subset=['win_rate']),
            use_container_width=True,
            column_config={
                "date": st.column_config.DateColumn("日期", format="YYYY-MM-DD"),
                "pe": st.column_config.NumberColumn("市盈率", format="%.2f"),
                "percentile": st.column_config.NumberColumn("历史百分位", format="%.2f%%"),
                "win_rate": st.column_config.ProgressColumn(
                    "理论胜率", format="%.2f%%", min_value=0, max_value=100
                ),
            },
            hide_index=True
        )

if __name__ == "__main__":
    main()
