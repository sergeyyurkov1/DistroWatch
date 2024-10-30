import json
import sqlite3
from operator import itemgetter

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import pycountry
from streamlit_echarts import JsCode, Map


class DistrowatchModel:
    top_n = 20

    def __init__(self):
        self.df_raw = self.load_data()
        self.preprocess_data()

        # print(self.df)

    @staticmethod
    def load_data() -> pd.DataFrame:
        with sqlite3.connect("DistroWatch.db") as con:
            return pd.read_sql(
                "SELECT * FROM distros",
                con,
            )

    # @st.cache_data
    def preprocess_data(self):
        df = self.df_raw.copy()

        pat = r"Independent \(forked from (?P<one>[a-zA-Z0-9 ]+)\)"
        repl = lambda m: m.group("one")
        df["Based on"] = df["Based on"].str.replace(pat, repl, regex=True)

        pat = r"(?P<one>[a-zA-Z0-9 ]+) \(formerly based on [a-zA-Z0-9 ]+\)"
        repl = lambda m: m.group("one")
        df["Based on"] = df["Based on"].str.replace(pat, repl, regex=True)

        df["Based on"] = df["Based on"].str.split(", ")
        df = df.explode("Based on")
        df = df.drop_duplicates()
        df = df.reset_index(drop=True)

        to_replace = {
            "Alpine Linux": "Alpine",
            "Arch Linux": "Arch",
            "Damn Small Linux": "Damn Small",
            "Debian (Stable)": "Debian",
            "Debian (Testing)": "Debian",
            "Debian (Unstable)": "Debian",
            "Devuan GNU+Linux": "Devuan",
            "Gentoo Linux": "Gentoo",
            "Kali Linux": "Kali",
            "Lubuntu (LTS)": "Lubuntu",
            "Manjaro Linux": "Manjaro",
            "Red Hat Enterprise Linux": "Red Hat",
            "Slackware Linux": "Slackware",
            "Ubuntu (LTS)": "Ubuntu",
            "Ubuntu (Stable)": "Ubuntu",
        }
        for k, v in to_replace.items():
            df = df.replace(k, v, regex=False)
            df = df.replace(k, v, regex=True)

        df["Popularity"] = df["Popularity"].replace("Not ranked", np.nan)
        df = df.replace({None: np.nan})
        df = df.replace({"": np.nan})

        df[["Popularity", "Hits per day"]] = df["Popularity"].str.split(
            " ", expand=True, n=1
        )
        df["Hits per day"] = df["Hits per day"].replace("\D", "", regex=True)

        df["Popularity"] = df["Popularity"].fillna(0).astype(int)
        df["Hits per day"] = df["Hits per day"].fillna(0).astype(int)

        df["Origin"] = df["Origin"].replace("Taiwan", "China", regex=True)

        self.df = df

    def get_num_distros(self):
        return self.df.shape[0]

    def get_num_linux_distros(self):
        df_filtered = self.df.query("`OS Type` == 'Linux'")
        return df_filtered.shape[0]

    def get_num_bsd_distros(self):
        df_filtered = self.df.query("`OS Type` == 'BSD'")
        return df_filtered.shape[0]

    def get_num_other_distros(self):
        df_filtered = self.df.query(
            "not (`OS Type` == 'Linux') & not (`OS Type` == 'BSD')"
        )
        return df_filtered.shape[0]

    def get_sankey_options(self):
        df_filtered = self.df.query("not (`Based on` == 'Independent')")

        all_distros = pd.concat([df_filtered["Name"], df_filtered["Based on"]], axis=0)

        uniques = all_distros.unique()

        data = [{"name": i} for i in uniques]

        source = list(df_filtered["Based on"])
        target = list(df_filtered["Name"])
        value = list(df_filtered["Hits per day"])

        links = [
            {"source": s, "target": t, "value": v}
            for s, t, v in zip(source, target, value)
        ]

        return {
            "series": {
                "type": "sankey",
                "layout": "none",
                "emphasis": {"focus": "adjacency"},  # ok
                "data": data,
                "links": links,
                "layoutIterations": 0,
                "nodeGap": 0,  # ok
                "labelLayout": {"hideOverlap": True},  # ok
                "lineStyle": {"color": "source", "curveness": 0.5},
                "top": 60,
            },
            "title": {"text": "Distributions and Derivatives", "padding": 20},
        }

    def get_architectures(self):
        df = self.df.copy()

        df = df[["Name", "Architecture"]]

        df["Architecture"] = df["Architecture"].str.split(",")

        df_architecture = df.explode("Architecture")
        df_architecture["Architecture"] = df_architecture["Architecture"].str.strip()

        df_architecture["Architecture"] = df_architecture["Architecture"].replace(
            "aarch64", "arm64"
        )

        # df_architecture = df_architecture.drop_duplicates()
        # df_architecture = df_architecture.reset_index(drop=True)

        data = (
            df_architecture.groupby("Architecture")["Architecture"]
            .count()
            .sort_values(ascending=False)
            .head(self.top_n)
        )

        fig = px.bar(
            data,
            # text_auto=".2s",
            labels={"index": "Architecture", "value": "Distributions"},
            title=f"Top {self.top_n} Supported Architectures",
        )

        fig.update_traces(marker_color="#0b3b24", showlegend=False)

        return fig

    def get_desktops(self):
        df = self.df.copy()

        df = df[["Name", "Desktop"]]

        df["Desktop"] = df["Desktop"].str.split(",")

        df_desktop = df.explode("Desktop")
        df_desktop["Desktop"] = df_desktop["Desktop"].str.strip()

        df_desktop["Desktop"] = df_desktop["Desktop"].replace("KDE Plasma", "KDE")

        # df_desktop = df_desktop.drop_duplicates()
        # df_desktop = df_desktop.reset_index(drop=True)

        data = (
            df_desktop.groupby("Desktop")["Desktop"]
            .count()
            .sort_values(ascending=False)
            .head(self.top_n)
        )

        fig = px.bar(
            data,
            # text_auto=".2s",
            labels={"index": "Desktop", "value": "Distributions"},
            title=f"Top {self.top_n} Supported Desktops",
        )

        fig.update_traces(marker_color="#0b3b24", showlegend=False)

        return fig

    # @st.cache_data
    def get_map(self):
        df = self.df.copy()

        df.sort_values(["Name"])

        df["Origin"] = df["Origin"].apply(lambda x: x.split(", ")[-1])

        def get_iso_alpha(x):
            try:
                if x in ["Global", "Europe", ""]:
                    return np.nan
                return pycountry.countries.search_fuzzy(x)[0].alpha_3
            except LookupError:
                return np.nan

        df_filtered = self.df.query("not (`Based on` == 'Independent')")

        df_filtered["iso_alpha"] = df_filtered["Origin"].apply(get_iso_alpha)

        df_grouped = (
            df_filtered.drop_duplicates("Name")
            .groupby(["iso_alpha", "Origin"])["Name"]
            .agg(count="count", names=lambda x: ", ".join(x))
            .reset_index()
        )

        fig = px.scatter_geo(
            df_grouped,
            locations="iso_alpha",
            color="Origin",
            hover_name="Origin",
            size="count",
            size_max=60,
            custom_data="names",
            hover_data=["count", "names"],
        )
        fig.update_geos(
            showland=True,
            landcolor="#f6efc8",
            showocean=True,
            oceancolor="#fdffe3",
            showframe=False,
        )
        fig.update_traces(
            # hovertemplate="""
            #     <b>Number of Distros:</b> %{customdata[1]}
            # """,
            # <br />
            # <b>Distro names:</b> %{customdata[0]}
            marker_color="#0b3b24",
        )
        fig.update_layout(
            title_text="Distributions by Country (2024)",
            showlegend=False,
            dragmode=False,
            # margin={"t": 0, "r": 0, "b": 0, "l": 0},
        )

        return fig

    def get_degree_plot(self):
        all_distros = pd.concat([self.df["Name"], self.df["Based on"]], axis=0)

        nodes = all_distros.unique()

        edges = list()

        for i, j in zip(list(self.df["Based on"]), list(self.df["Name"])):
            edges.append((i, j))

        G = nx.Graph()

        G.add_nodes_from(nodes)
        G.add_edges_from(edges)

        degree_dict = dict(G.degree(G.nodes()))
        nx.set_node_attributes(G, degree_dict, "degree")
        sorted_degree = sorted(degree_dict.items(), key=itemgetter(1), reverse=True)

        print("Top 20 Nodes")
        for d in sorted_degree[:20]:
            print(type(d))

        sorted_degree_filtered = list(
            filter(lambda n: n[0] != "Independent", sorted_degree)
        )

        x, y = list(zip(*sorted_degree_filtered[:20]))

        fig = px.bar(
            x=x,
            y=y,
            # text_auto=".2s",
            labels={"x": "Distribution", "y": "Derivatives"},
            title="Distribution Importance for Derivatives",
        )

        fig.update_traces(
            marker_color="#0b3b24",
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        return fig

    def get_map_options(self):
        formatter = JsCode(
            "function (params) {"
            + "var value = (params.value + '').split('.');"
            + "value = value[0].replace(/(\d{1,3})(?=(?:\d{3})+(?!\d))/g, '$1,');"
            + "return params.seriesName + '<br/>' + params.name + ': ' + value;}"
        ).js_code

        with open("./countries.geo.json", "r") as f:  # ok
            map = Map(
                "Countries",
                json.loads(f.read()),
            )
        options = {
            "title": {
                "text": "Distributions by country",
                # "subtext": "",
                # "sublink": "",
                "left": "right",
            },
            "tooltip": {
                "trigger": "item",
                "showDelay": 0,
                "transitionDuration": 0.2,
                "formatter": formatter,
            },
            "toolbox": {
                "show": False,
                "left": "left",
                "top": "top",
                "feature": {
                    "dataView": {"readOnly": False},
                    "restore": {},
                    "saveAsImage": {},
                },
            },
            "series": [
                {
                    "name": "Distributions by country",
                    "type": "map",
                    "roam": False,
                    "map": "Countries",  # ok
                    "emphasis": {"label": {"show": True}},
                    "data": [
                        {"name": "Uzbekistan", "value": 4822023},
                    ],
                }
            ],
        }

        return options, map
