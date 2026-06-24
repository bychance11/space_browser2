#!/usr/bin/env python3
"""
1단계: OpenAlex에서 논문 메타데이터를 수집해 SQLite(data/papers.sqlite)에 저장.

실행:
    python fetcher/fetch.py            # fields.json 설정대로 수집
    python fetcher/fetch.py --stats    # 저장된 내용 요약만 출력

설정: fetcher/fields.json (수집할 분야/키워드/연도/개수)
데이터: data/papers.sqlite
"""
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request

# ---------- 경로 ----------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # academic-universe/
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "papers.sqlite")
FIELDS_PATH = os.path.join(HERE, "fields.json")
API = "https://api.openalex.org/works"


# ---------- DB ----------
def init_db(path=DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY, title TEXT, abstract TEXT, year INTEGER,
            citations INTEGER, counts_by_year TEXT, is_oa INTEGER, oa_url TEXT,
            doi TEXT, url TEXT, authors TEXT, query TEXT
        );
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY, name TEXT, level INTEGER
        );
        CREATE TABLE IF NOT EXISTS paper_concepts (
            paper_id TEXT, concept_id TEXT, score REAL,
            PRIMARY KEY (paper_id, concept_id)
        );
        CREATE TABLE IF NOT EXISTS refs (
            paper_id TEXT, cited_id TEXT,
            PRIMARY KEY (paper_id, cited_id)
        );
        CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
        CREATE INDEX IF NOT EXISTS idx_papers_cit ON papers(citations);
        """
    )
    conn.commit()
    return conn


def short_id(openalex_url):
    """https://openalex.org/W123  ->  W123"""
    if not openalex_url:
        return None
    return openalex_url.rstrip("/").split("/")[-1]


def reconstruct_abstract(inverted_index):
    """OpenAlex는 초록을 단어→위치 형태로 줌. 원문 순서로 복원."""
    if not inverted_index:
        return ""
    positions = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda p: p[0])
    return " ".join(w for _, w in positions)


def parse_work(w, query_name=""):
    """OpenAlex 원본 1건 -> 저장용 dict (papers/concepts/refs)."""
    oa = w.get("open_access") or {}
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in (w.get("authorships") or [])
    ]
    authors = [a for a in authors if a]
    concepts = []
    for c in (w.get("concepts") or []):
        cid = short_id(c.get("id"))
        if cid:
            concepts.append((cid, c.get("display_name"), c.get("level"), c.get("score")))
    refs = [short_id(r) for r in (w.get("referenced_works") or []) if r]

    paper = {
        "id": short_id(w.get("id")),
        "title": w.get("title") or w.get("display_name"),
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        "year": w.get("publication_year"),
        "citations": w.get("cited_by_count", 0),
        "counts_by_year": json.dumps(w.get("counts_by_year") or [], ensure_ascii=False),
        "is_oa": 1 if oa.get("is_oa") else 0,
        "oa_url": oa.get("oa_url"),
        "doi": w.get("doi"),
        "url": w.get("id"),
        "authors": json.dumps(authors, ensure_ascii=False),
        "query": query_name,
    }
    return paper, concepts, refs


def save_work(conn, paper, concepts, refs):
    if not paper["id"]:
        return
    conn.execute(
        """INSERT OR REPLACE INTO papers
           (id,title,abstract,year,citations,counts_by_year,is_oa,oa_url,doi,url,authors,query)
           VALUES (:id,:title,:abstract,:year,:citations,:counts_by_year,:is_oa,:oa_url,:doi,:url,:authors,:query)""",
        paper,
    )
    for cid, name, level, score in concepts:
        conn.execute("INSERT OR IGNORE INTO concepts(id,name,level) VALUES (?,?,?)", (cid, name, level))
        conn.execute(
            "INSERT OR REPLACE INTO paper_concepts(paper_id,concept_id,score) VALUES (?,?,?)",
            (paper["id"], cid, score),
        )
    conn.execute("DELETE FROM refs WHERE paper_id=?", (paper["id"],))
    for cited in refs:
        if cited:
            conn.execute("INSERT OR IGNORE INTO refs(paper_id,cited_id) VALUES (?,?)", (paper["id"], cited))


# ---------- 수집 (네트워크) ----------
def fetch_query(cfg, mailto):
    """OpenAlex를 커서 페이지네이션으로 돌며 원본 work들을 yield."""
    select = ("id,display_name,title,publication_year,cited_by_count,counts_by_year,"
              "abstract_inverted_index,open_access,doi,authorships,concepts,referenced_works")
    params = {
        "search": cfg["search"],
        "per-page": "200",
        "select": select,
        "cursor": "*",
    }
    if cfg.get("from_year"):
        params["filter"] = f"from_publication_date:{cfg['from_year']}-01-01"
    if mailto:
        params["mailto"] = mailto

    got, max_records = 0, cfg.get("max_records", 500)
    while True:
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": f"space-browser/0.1 ({mailto})"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("results", [])
        if not results:
            break
        for w in results:
            yield w
            got += 1
            if got >= max_records:
                return
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        params["cursor"] = cursor
        time.sleep(0.2)  # 예의상 약간 쉼


def run():
    cfg_all = json.load(open(FIELDS_PATH, encoding="utf-8"))
    mailto = cfg_all.get("mailto", "")
    conn = init_db()
    total = 0
    for q in cfg_all["queries"]:
        print(f"[수집] '{q['name']}' (search='{q['search']}', from={q.get('from_year')}, max={q.get('max_records')})")
        n = 0
        try:
            for w in fetch_query(q, mailto):
                paper, concepts, refs = parse_work(w, q["name"])
                save_work(conn, paper, concepts, refs)
                n += 1
                if n % 100 == 0:
                    conn.commit()
                    print(f"  ...{n}건 저장")
        except Exception as e:
            print(f"  [경고] '{q['name']}' 중단: {e}")
        conn.commit()
        total += n
        print(f"  -> '{q['name']}' {n}건 완료")
    print_stats(conn)
    conn.close()
    print(f"\n완료: 총 {total}건. DB: {DB_PATH}")


def print_stats(conn):
    p = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    c = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    r = conn.execute("SELECT COUNT(*) FROM refs").fetchone()[0]
    print(f"\n[현황] papers={p}, concepts={c}, refs(인용엣지)={r}")
    top = conn.execute("SELECT title, citations FROM papers ORDER BY citations DESC LIMIT 5").fetchall()
    if top:
        print("[인용 상위 5]")
        for t, cit in top:
            print(f"  {cit:>7}  {(t or '')[:70]}")


if __name__ == "__main__":
    if "--stats" in sys.argv:
        if not os.path.exists(DB_PATH):
            print("DB가 아직 없습니다. 먼저 `python fetcher/fetch.py`로 수집하세요.")
        else:
            print_stats(init_db())
    else:
        run()
