#!/usr/bin/env python3
"""
2단계 (TODO): data/papers.sqlite 를 읽어 분류·좌표를 계산하고
web 이 읽을 universe-<field>.json 으로 내보낸다.

계획:
  - 그래프(인용/공동인용) 또는 임베딩 구성
  - 군집화: Leiden (leidenalg / igraph)
  - 3D 좌표: UMAP/t-SNE (umap-learn)
  - 지표: 모멘텀(counts_by_year 기울기), 다리(매개중심성)
  - 출력: [{id,title,x,y,z,size,brightness,cluster,color,momentum,url}, ...]
"""
print("TODO: 2단계 분류·좌표 계산. 먼저 fetcher/fetch.py로 데이터를 모으세요.")
