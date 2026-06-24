#!/usr/bin/env python3
"""
네트워크 없이 저장 로직(parse_work + save_work + DB)을 점검한다.
OpenAlex 응답을 흉내 낸 모의 데이터로 임시 DB에 저장 후 다시 읽어 출력.

실행: python fetcher/selftest.py
"""
import json
import os
import sqlite3
import tempfile

import fetch  # 같은 폴더의 fetch.py

# OpenAlex works 한 건과 비슷한 모의 데이터 2건
MOCK = [
    {
        "id": "https://openalex.org/W1001",
        "title": "Deep Learning for Everything",
        "publication_year": 2019,
        "cited_by_count": 1234,
        "counts_by_year": [{"year": 2023, "cited_by_count": 200}, {"year": 2024, "cited_by_count": 350}],
        "abstract_inverted_index": {"We": [0], "study": [1], "deep": [2], "learning": [3]},
        "open_access": {"is_oa": True, "oa_url": "https://example.org/w1001.pdf"},
        "doi": "https://doi.org/10.1/abc",
        "authorships": [{"author": {"display_name": "Kim"}}, {"author": {"display_name": "Lee"}}],
        "concepts": [
            {"id": "https://openalex.org/C100", "display_name": "Machine learning", "level": 1, "score": 0.9},
            {"id": "https://openalex.org/C200", "display_name": "Computer science", "level": 0, "score": 0.8},
        ],
        "referenced_works": ["https://openalex.org/W900", "https://openalex.org/W901"],
    },
    {
        "id": "https://openalex.org/W1002",
        "title": "A Minor Note",
        "publication_year": 2023,
        "cited_by_count": 3,
        "counts_by_year": [{"year": 2024, "cited_by_count": 3}],
        "abstract_inverted_index": None,  # 초록 없는 경우
        "open_access": {"is_oa": False, "oa_url": None},
        "doi": None,
        "authorships": [{"author": {"display_name": "Park"}}],
        "concepts": [{"id": "https://openalex.org/C100", "display_name": "Machine learning", "level": 1, "score": 0.5}],
        "referenced_works": ["https://openalex.org/W1001"],  # 위 논문을 인용
    },
]


def main():
    tmp = os.path.join(tempfile.gettempdir(), "selftest_papers.sqlite")
    if os.path.exists(tmp):
        os.remove(tmp)
    conn = fetch.init_db(tmp)

    for w in MOCK:
        paper, concepts, refs = fetch.parse_work(w, query_name="selftest")
        fetch.save_work(conn, paper, concepts, refs)
    conn.commit()

    # 1) 초록 복원 확인
    ab = conn.execute("SELECT abstract FROM papers WHERE id='W1001'").fetchone()[0]
    assert ab == "We study deep learning", f"초록 복원 실패: {ab!r}"

    # 2) 저장 건수
    np = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    nc = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    nr = conn.execute("SELECT COUNT(*) FROM refs").fetchone()[0]
    assert np == 2 and nc == 2 and nr == 3, f"건수 불일치: papers={np}, concepts={nc}, refs={nr}"

    # 3) 인용 상위 + 저자 JSON
    title, cit, authors = conn.execute(
        "SELECT title, citations, authors FROM papers ORDER BY citations DESC LIMIT 1"
    ).fetchone()
    assert json.loads(authors) == ["Kim", "Lee"], authors

    print("OK ✅  저장 로직 정상")
    print(f"  papers={np}, concepts={nc}, refs={nr}")
    print(f"  초록 복원: '{ab}'")
    print(f"  인용 1위: ({cit}) {title}  / 저자={json.loads(authors)}")
    print(f"  (임시 DB: {tmp})")
    conn.close()


if __name__ == "__main__":
    main()
