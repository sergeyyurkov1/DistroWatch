import streamlit as st
from streamlit_echarts import st_echarts

from model import DistrowatchModel

M = DistrowatchModel()

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="DistroWatch Data Explorer",
)

# box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
# padding: 1rem;
st.markdown(
    """
    <style>
    [data-testid="stVerticalBlock"] *:has(> [data-testid="element-container"]) {
        border-radius: 0.375rem; /* 6px */
        background-color: #f6efc8;
    }
    [data-testid="stVerticalBlock"] *:has(> [data-testid="element-container"] .metric) {
        border-left: 0.375rem solid #680000;
        padding: 1rem;
    }
    [data-testid="StyledFullScreenButton"] {
        display: none;
    }
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


col1, col2, col3, col4 = st.columns(4)
with col1:
    st.html("<span class='metric'></span>")
    st.metric(label="Total Distros", value=M.get_num_distros())
with col2:
    st.html("<span class='metric'></span>")
    st.metric(label="Linux Distros", value=M.get_num_linux_distros())
with col3:
    st.html("<span class='metric'></span>")
    st.metric(label="BSD Distros", value=M.get_num_bsd_distros())
with col4:
    st.html("<span class='metric'></span>")
    st.metric(label="Other Distros", value=M.get_num_other_distros())

with st.columns(1)[0]:
    fig = M.get_map()
    st.plotly_chart(fig, use_container_width=True)
    # o, m = M.get_map_options()
    # st_echarts(options=o, map=m, height="600px")

col21, col22, col23 = st.columns(3)
with col21:
    st.plotly_chart(M.get_architectures())
with col22:
    st.plotly_chart(M.get_desktops())
with col23:
    st.plotly_chart(M.get_degree_plot())

with st.columns(1)[0]:
    st_echarts(options=M.get_sankey_options(), height="1000px")


with st.sidebar:
    st.image("dwbanner.png", use_column_width="always")

    st.title("DistroWatch Data Explorer")

    # with st.popover("How the data was collected"):
    #     with st.container(border=None):
    #         ...

    st.markdown(
        """
            Created by [Yurkov Sergey](https://sergeyyurkov1.github.io/)
        """
    )
