# -*- coding: utf-8 -*-
# =====================================================================
#  MoneyPilot 글감 수집 대시보드 (1차 버전)
#  - API 키 없이 무료 소스만 사용
#  - ① 구글 뉴스 RSS (최신 뉴스/정책/이슈)
#  - ② 레딧 인기글 (지금 사람들이 떠드는 주제)
#  실행하면 데이터를 긁어와서 HTML 한 화면으로 정리하고 자동으로 열림.
# =====================================================================

import sys                  # 자동 실행(조용한 모드)인지 판단하려고
import webbrowser          # 다 만든 HTML을 자동으로 브라우저에 띄우려고
import datetime            # 오늘 날짜를 화면에 찍으려고
import html as html_lib    # 제목에 특수문자(<, & 등) 있어도 안 깨지게
import requests            # 인터넷에서 데이터 가져오는 도구
import feedparser          # 구글 뉴스 RSS를 읽는 도구

# ---------------------------------------------------------------------
# 1) 어떤 주제를 긁어올지 — 여기만 바꾸면 분야가 통째로 바뀜
# ---------------------------------------------------------------------

# 구글 뉴스에서 검색할 키워드들 (영어, 미국 타겟)
NEWS_QUERIES = [
    "personal finance",
    "AI money saving",
    "budgeting tips",
    "passive income",
    "side hustle",
]

# 해커뉴스에서 검색할 키워드들 (재테크/금융/AI, 영어)
HN_QUERIES = [
    "personal finance",
    "saving money",
    "passive income",
    "investing",
]

# 각 소스에서 몇 개씩 가져올지
MAX_PER_SOURCE = 8


# ---------------------------------------------------------------------
# 2) 구글 뉴스 RSS 긁어오기
# ---------------------------------------------------------------------
def get_google_news(query):
    """키워드 하나로 구글 뉴스 최신글 목록을 가져온다."""
    # hl=en-US gl=US -> 미국 영어 기준 결과
    url = (
        "https://news.google.com/rss/search?"
        f"q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:MAX_PER_SOURCE]:
            items.append({
                "title": entry.get("title", "(제목 없음)"),
                "link": entry.get("link", "#"),
                "source": entry.get("source", {}).get("title", "Google News"),
            })
    except Exception as e:
        print(f"  [뉴스 실패] {query}: {e}")
    return items


# ---------------------------------------------------------------------
# 3) 레딧 인기글 긁어오기
# ---------------------------------------------------------------------
def get_hackernews(query):
    """키워드 하나로 해커뉴스에서 화제인 글을 가져온다."""
    # 해커뉴스 공식 무료 검색 API (키 불필요, 거의 안 막힘)
    # tags=story -> 댓글 말고 '글'만, hitsPerPage -> 몇 개 가져올지
    url = (
        "https://hn.algolia.com/api/v1/search?"
        f"query={requests.utils.quote(query)}&tags=story"
        f"&hitsPerPage={MAX_PER_SOURCE}"
    )
    items = []
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        for hit in res.json().get("hits", []):
            title = hit.get("title")
            if not title:
                continue
            # 글에 원본 링크가 없으면 해커뉴스 토론 페이지로 연결
            link = hit.get("url") or (
                "https://news.ycombinator.com/item?id=" + hit.get("objectID", "")
            )
            items.append({
                "title": title,
                "link": link,
                "score": hit.get("points", 0),          # 추천 수 = 화제성
                "comments": hit.get("num_comments", 0),
            })
    except Exception as e:
        print(f"  [해커뉴스 실패] {query}: {e}")
    # 추천 수(화제성) 높은 글이 위로 오게 정렬
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


# ---------------------------------------------------------------------
# 4) 긁어온 걸 HTML 화면으로 조립
# ---------------------------------------------------------------------
def build_html(news_data, hn_data):
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- 뉴스 카드들 만들기 ---
    news_blocks = ""
    for query, items in news_data.items():
        rows = ""
        for it in items:
            t = html_lib.escape(it["title"])
            rows += (
                f'<li><a href="{it["link"]}" target="_blank">{t}</a>'
                f'<span class="src">{html_lib.escape(it["source"])}</span></li>'
            )
        if not rows:
            rows = '<li class="empty">결과 없음</li>'
        news_blocks += (
            f'<div class="card"><h3>📰 {html_lib.escape(query)}</h3>'
            f'<ul>{rows}</ul></div>'
        )

    # --- 해커뉴스 카드들 만들기 ---
    hn_blocks = ""
    for query, items in hn_data.items():
        rows = ""
        for it in items:
            t = html_lib.escape(it["title"])
            rows += (
                f'<li><a href="{it["link"]}" target="_blank">{t}</a>'
                f'<span class="meta">▲ {it["score"]} · 💬 {it["comments"]}</span></li>'
            )
        if not rows:
            rows = '<li class="empty">결과 없음</li>'
        hn_blocks += (
            f'<div class="card"><h3>🟧 {html_lib.escape(query)}</h3>'
            f'<ul>{rows}</ul></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>MoneyPilot 글감 대시보드</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background:#0f172a;
          color:#e2e8f0; margin:0; padding:30px; }}
  h1 {{ font-size:26px; margin:0 0 4px; }}
  .date {{ color:#94a3b8; margin-bottom:24px; font-size:14px; }}
  .section-title {{ font-size:18px; margin:30px 0 12px; color:#38bdf8; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
           gap:16px; }}
  .card {{ background:#1e293b; border-radius:12px; padding:16px 18px; }}
  .card h3 {{ margin:0 0 10px; font-size:15px; color:#fbbf24; }}
  ul {{ list-style:none; margin:0; padding:0; }}
  li {{ padding:7px 0; border-bottom:1px solid #334155; font-size:14px; }}
  li:last-child {{ border-bottom:none; }}
  a {{ color:#e2e8f0; text-decoration:none; }}
  a:hover {{ color:#38bdf8; }}
  .src, .meta {{ display:block; color:#64748b; font-size:12px; margin-top:3px; }}
  .empty {{ color:#64748b; }}
  #filter {{ width:100%; max-width:520px; box-sizing:border-box; padding:12px 16px;
             margin-bottom:8px; font-size:15px; border-radius:10px;
             border:1px solid #334155; background:#1e293b; color:#e2e8f0; }}
  #filter::placeholder {{ color:#64748b; }}
  .card.hidden, li.hidden {{ display:none; }}
</style>
</head>
<body>
  <h1>🛩️ MoneyPilot 글감 대시보드</h1>
  <div class="date">수집 시각: {today}</div>

  <input id="filter" placeholder="🔍 글감 검색 — 키워드를 입력하면 관련 글만 보여요"
         oninput="filterItems()">

  <div class="section-title">① 최신 뉴스 (구글 뉴스)</div>
  <div class="grid">{news_blocks}</div>

  <div class="section-title">② 지금 뜨는 주제 (해커뉴스)</div>
  <div class="grid">{hn_blocks}</div>

<script>
function filterItems() {{
  var q = document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('.card').forEach(function(card) {{
    var anyVisible = false;
    card.querySelectorAll('li').forEach(function(li) {{
      var hit = li.textContent.toLowerCase().indexOf(q) !== -1;
      li.classList.toggle('hidden', !hit);
      if (hit) anyVisible = true;
    }});
    // 카드 안에 보이는 글이 하나도 없으면 카드 자체를 숨김
    card.classList.toggle('hidden', !anyVisible);
  }});
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------
# 5) 메인 실행
# ---------------------------------------------------------------------
def main():
    print("글감 수집 시작...")

    news_data = {}
    for q in NEWS_QUERIES:
        print(f"  뉴스 가져오는 중: {q}")
        news_data[q] = get_google_news(q)

    hn_data = {}
    for q in HN_QUERIES:
        print(f"  해커뉴스 가져오는 중: {q}")
        hn_data[q] = get_hackernews(q)

    html = build_html(news_data, hn_data)

    # 스크립트가 있는 폴더에 저장 (자동 실행 때 엉뚱한 곳에 안 생기게)
    import os
    folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(folder, "money_dashboard.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # 실행할 때 '--silent'를 붙이면(=자동 실행) 브라우저를 안 띄움
    silent = "--silent" in sys.argv
    if silent:
        print(f"완료! (조용한 모드) 저장됨: {filepath}")
    else:
        print(f"완료! '{filepath}' 파일을 브라우저로 엽니다.")
        webbrowser.open(filepath)


if __name__ == "__main__":
    main()
