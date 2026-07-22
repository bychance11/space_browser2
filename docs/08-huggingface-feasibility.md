# HuggingFace 우주 — 초기 타당성 검토 (2026-07-22)

결론: **가능. OpenAlex 파이프라인(수집→SQLite→군집/좌표→JSON→Three.js)을 거의 그대로 재사용할 수 있다.**
API 3종(models/datasets/spaces) 모두 인증 없이 JSON 응답 확인 완료.

## API 검증 결과
| 엔드포인트 | 확인 | 비고 |
|---|---|---|
| `GET /api/models?full=true&sort=downloads` | ✅ | 다운로드·좋아요·태그·생성일 포함 |
| `GET /api/datasets?full=true` | ✅ | 설명·태그·다운로드 포함 |
| `GET /api/spaces?full=true` | ✅ | likes, sdk, cardData(연결 모델 목록) 포함 |
| `GET /api/models/<id>?expand[]=downloadsAllTime` | ✅ | 누적 다운로드 별도 제공 (기본 `downloads`는 **최근 30일**) |

- 인증 불필요(비로그인 OK), 커서 페이지네이션(`Link` 헤더) — OpenAlex와 동일 패턴.
- 파이썬은 공식 `huggingface_hub` 라이브러리(`list_models` 등)로 더 간단하게 수집 가능.
- 메타데이터는 공개 API로 자유 접근. 상업 사용 시 HF ToS 확인 필요(개별 모델 라이선스는 태그에 포함됨).

## 필드 매핑 — 논문 우주 ↔ HF 우주
| 논문(OpenAlex) | HF | 확인된 필드 |
|---|---|---|
| 논문 (별) | 모델/데이터셋/스페이스 | `id`, `author`, `createdAt` |
| 인용수 (크기·밝기) | 다운로드·좋아요 | `downloads`(30일), `downloadsAllTime`, `likes` |
| concepts (분야→색) | 태스크·라이브러리·언어 | `pipeline_tag`, `library_name`, `tags`(license, language 등) |
| referenced_works (엣지) | **모델 계보** | `base_model:` 태그 (finetune/quantized/adapter/merge 관계까지 표기) |
| — | 모델↔데이터셋 엣지 | `dataset:` 태그 |
| — | 스페이스↔모델 엣지 | 스페이스 `cardData.models` |
| **논문 연결** | **`arxiv:` 태그** | → **기존 학술 우주와 은하 간 다리 가능** ⭐ |
| abstract (임베딩) | README(모델 카드) | 별도 fetch 필요 (`/raw/main/README.md`) |
| counts_by_year (모멘텀) | ❌ **시계열 없음** | 아래 참고 |

## 갭 & 대응
1. **시계열 지표 부재**: 다운로드/좋아요 히스토리 API 없음.
   - 대응: 주기 수집 시 스냅샷을 SQLite에 누적 → 자체 시계열 구축. (이미 주 1회 갱신 계획이므로 fetch 구조 그대로.)
   - 단기 대체: `downloads`(30일) / `downloadsAllTime` 비율 = 즉석 모멘텀 근사.
2. **규모**: 모델 200만+ → 논문 때처럼 분야(pipeline_tag)·다운로드 임계로 슬라이스 수집. `fields.json` 패턴 재사용.
3. **임베딩**: OpenAlex처럼 제공 안 됨 → README 텍스트를 sentence-transformers로 직접 임베딩 후 UMAP.

## 논문 방식 지표 적용 가능성
- 군집(Leiden): `base_model` 계보 그래프 + 태그 공유 그래프로 가능 ✅
- 3D 좌표(UMAP): README 임베딩 or 태그 벡터로 가능 ✅
- 모멘텀: 스냅샷 축적 후 가능 (초기엔 30일/누적 비율) ⚠️
- 다리(매개중심성): 계보·데이터셋 공유 그래프에서 가능 ✅

## 은하 구조 설계 — 마인드맵 방지
순수 연관성(태그 공유) 그래프로 배치하면 은하가 안 생긴다:
- **허브 태그 문제**: `transformers`, `pytorch`, `license:*`를 수십만 모델이 공유 → 전체가 털뭉치(hairball)로 뭉침.
- **계보 편향**: `base_model` 엣지는 Llama/Qwen 등 소수 가문에 쏠림 → 은하 대신 초거대 항성계 몇 개 + 고립 별.

→ **뼈대(계층)와 살(연관성)을 분리**한다. 논문 우주의 concepts 계층 역할을 HF의 숨은 계층으로 대체:

| 우주 구조 | HF 대응 | 근거 |
|---|---|---|
| 은하군 | 모달리티 (NLP/Vision/Audio/Multimodal/Tabular/RL) | HF 자체 태스크 대분류 |
| 은하 | 태스크 (`pipeline_tag`) | 모델당 정확히 1개 → 소속 배타적 |
| 성단·항성계 | `base_model` 계보 가문 (Llama계, SD계 등) | 은하 **내부**에서만 사용 |
| 행성·위성 | finetune / quantized / adapter | 계보 태그에 관계 유형 명시 |

연관성 엣지는 전역 배치에 쓰지 않고 두 곳에만:
1. **은하 간 거리** — 태스크끼리 데이터셋·arxiv·스페이스 공유량으로 측정. (예: image-to-text는 Vision–NLP 사이의 "다리 은하")
2. **은하 내부 별 배치** — README 임베딩 + 계보.
허브 태그는 TF-IDF식 가중치로 감쇠 또는 제외.

## 탐험 목적성 — 세렌디피티
논문 우주가 "이런 **연구**가 있구나"라면, HF 우주는 "이런 게 **이미 만들어져 돌아가는구나**". 별 클릭 = 즉시 실행 가능한 데모(Space)·다운로드 가능한 모델 → 아이디어가 실행 가능한 형태로 수급됨.
- 낯선 은하: 마이너 pipeline_tag (단백질 접힘, 시계열, 깊이 추정, 로보틱스 등 40+)
- 다리 별: 여러 태스크 은하에서 쓰이는 데이터셋, 여러 은하의 모델을 조합한 스페이스
- 양방향 왕복: `arxiv:` 태그로 도구↔이론(학술 우주) 점프
- 한계 인지: 논문 우주는 전 과학, HF는 AI 한 대륙. 다양성의 축은 학문 분야 → **응용 도메인**으로 이동.

## 제2의 축 — 응용 도메인 우주
태스크 외에 의료/법률/금융/화학/음악 등 **응용 도메인**으로도 은하를 묶을 수 있다.
- 단, 도메인은 API 1급 필드가 아님 → 자유 태그(`medical`, `legal`...) + 데이터셋 이름 + README 임베딩에서 **추론** 필요.
- 07 문서의 "구조 필터" 개념과 일치: 같은 별들로 좌표 2벌을 미리 계산 → **태스크 우주 ↔ 도메인 우주** 전환.
- 태스크 우주에선 흩어진 의료 모델들이 도메인 우주에선 의료 은하로 결집 → 탐험(모르는 응용 분야 발견) 목적엔 도메인 우주가 더 강력.

## 다음 단계 제안
1. fetcher를 일반화해 소스 플러그인 구조로 (openalex / huggingface)
2. 파일럿: `pipeline_tag=text-generation` 상위 500개 모델 수집 → SQLite
3. `base_model` 계보로 엣지 생성 → 미니 우주 JSON 1개 생성
4. `arxiv:` 태그로 학술 우주와 교차 링크 실험
5. README 임베딩에서 도메인 군집 추출 실험 → 도메인 우주 좌표 2벌째 생성
