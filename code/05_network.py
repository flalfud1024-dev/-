"""
05_network.py — 인물 공출현 네트워크
번역본별 담론 중심 인물 비교
"""

from itertools import combinations
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

CHARACTERS = {
    '英惠':   '영혜',
    '仁惠':   '인혜',
    '韩医生': '남편',
    '姐夫':   '형부',
    '父亲':   '아버지',
    '母亲':   '어머니',
}


def build_network(df: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(CHARACTERS.keys())
    for _, row in df.iterrows():
        text = str(row['text'])
        found = [c for c in CHARACTERS if c in text]
        for a, b in combinations(found, 2):
            if G.has_edge(a, b):
                G[a][b]['weight'] += 1
            else:
                G.add_edge(a, b, weight=1)
    return G


def plot_network_comparison(df: pd.DataFrame, output_path: str):
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    versions = ['tianyi_2013', 'taiwan_2016', 'huchutong_2021']
    labels = ['천일본(2013)', '천일본(2016)', '후추통본(2021)']

    for ax, ver, label in zip(axes, versions, labels):
        G = build_network(df[df['version'] == ver])

        centrality = nx.degree_centrality(G)
        node_sizes = [centrality[n] * 5000 + 500 for n in G.nodes()]
        weights = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]

        pos = nx.spring_layout(G, seed=42)
        nx.draw_networkx(
            G, pos, ax=ax,
            node_size=node_sizes,
            width=weights,
            labels={k: v for k, v in CHARACTERS.items()},
            font_size=9,
            node_color='#4C9BE8',
            font_color='white',
            edge_color='#888888',
        )
        top_node = max(centrality, key=centrality.get)
        ax.set_title(
            f'{label}\n핵심 인물: {CHARACTERS[top_node]}',
            fontsize=12, fontweight='bold'
        )
        ax.axis('off')

    plt.suptitle('번역본별 인물 공출현 네트워크 비교',
                 fontsize=15, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)


if __name__ == '__main__':
    df = pd.read_csv('data/processed/all_reviews.csv')
    plot_network_comparison(
        df, 'output/figures/fig3_character_network.png'
    )
    print("인물 네트워크 저장 완료")
