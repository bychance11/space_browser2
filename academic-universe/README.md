# Academic Universe (학술 우주)

OpenAlex 논문 메타데이터를 수집 → DB 저장 → 분류·좌표 계산 → 3D 우주로 시각화.

## 폴더
```
academic-universe/
├── fetcher/      OpenAlex 수집 (Python)
│   ├── fetch.py        # 1단계: 수집 → SQLite 저장  ← 지금 이거
│   ├── selftest.py     # 네트워크 없이 저장 로직 점검
│   └── fields.json     # 수집할 분야/키워드/연도 설정
├── processor/    분류·좌표·지표 (다음 단계)
│   ├── build.py        # Leiden 군집 + UMAP 3D 좌표 (TODO)
│   └── metrics.py      # 모멘텀·다리 지표 (TODO)
├── data/         산출물 (papers.sqlite, universe-*.json)
└── web/          프론트엔드 (Three.js) (다음 단계)
```

## 1단계 실행 방법 (로컬)
파이썬 3가 설치돼 있어야 합니다.

```bash
cd academic-universe
pip install -r requirements.txt        # requests 설치
python fetcher/fetch.py                 # fields.json 설정대로 수집 → data/papers.sqlite
```

수집이 끝나면 `data/papers.sqlite`에 논문이 저장됩니다. 내용 확인:
```bash
python fetcher/fetch.py --stats         # 저장된 논문 수 등 요약
```

> 참고: 수집할 분야/연도/개수는 `fetcher/fields.json`에서 바꾸세요.
> 네트워크 없이 저장 로직만 점검하려면: `python fetcher/selftest.py`
