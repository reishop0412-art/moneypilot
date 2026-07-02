# -*- coding: utf-8 -*-
# =====================================================================
#  MoneyPilot 글감 수집 대시보드
#  - CFPB · Federal Reserve · FDIC · SBA · SSA
#  ※ 모두 미국 정부 공식 사이트 — 저작권 문제 없음
# =====================================================================

import sys
import re
import webbrowser
import datetime
import html as html_lib
import requests
import feedparser

# Windows 터미널에서 이모지 출력 시 에러 방지 (UTF-8 강제)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------
# 1) RSS 소스 목록 — 여기만 바꾸면 소스 추가/제거 가능
# ---------------------------------------------------------------------
RSS_SOURCES = [
    {
        "name": "CFPB",
        "url": "https://www.consumerfinance.gov/about-us/newsroom/feed/",
        "icon": "🏛️",
    },
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "icon": "🏦",
    },
    {
        "name": "FDIC",
        "url": "https://public.govdelivery.com/topics/USFDIC_26/feed.rss",
        "icon": "🏧",
    },
    {
        "name": "SBA",
        "url": "https://advocacy.sba.gov/feed/",
        "icon": "💼",
    },
    {
        "name": "SSA",
        "url": "https://public.govdelivery.com/topics/USSSA_117/feed.rss",
        "icon": "👴",
    },
    {
        "name": "FTC",
        "url": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml",
        "icon": "⚠️",
        "category": "소비자경고",
    },
    {
        "name": "VA",
        "url": "https://news.va.gov/feed/",
        "icon": "🎖️",
        "category": "참전용사",
    },
    {
        "name": "IRS",
        "url": "https://public.govdelivery.com/topics/USIRS_t24647/feed.rss",
        # 기본주소 실패 시 시도할 대체주소 (GovDelivery는 둘 중 하나가 맞음)
        "url_fallbacks": [
            "https://public.govdelivery.com/topics/USIRS_24647/feed.rss",
        ],
        "icon": "🧾",
        "category": "세금",
    },
]

MAX_PER_SOURCE = 8  # 소스당 최대 기사 수


# ---------------------------------------------------------------------
# 2) RSS 피드 가져오기
# ---------------------------------------------------------------------
def strip_html(text):
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def get_rss_feed(source):
    """RSS 피드 URL에서 기사 목록 가져오기.
    기본주소가 실패하면 url_fallbacks(있을 때만)를 차례로 시도한다.
    한 피드가 실패해도 예외를 잡아 그 피드만 건너뛰고 계속 진행한다."""
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

    # 시도할 주소 목록: 기본주소 + (있으면) 대체주소들
    urls = [source["url"]] + source.get("url_fallbacks", [])

    for url in urls:
        try:
            raw = requests.get(url, headers=headers, timeout=15)
            raw.raise_for_status()
            feed = feedparser.parse(raw.content)

            for entry in feed.entries[:MAX_PER_SOURCE]:
                title = strip_html(entry.get("title", ""))
                link = entry.get("link", "#")
                summary = strip_html(entry.get("summary", ""))[:300]
                if title:
                    items.append({
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "source": source["name"],
                        "icon": source["icon"],
                        "category": source.get("category", ""),  # 라벨 (없으면 빈 값)
                    })

            if items:
                return items  # 성공 → 대체주소는 시도하지 않음
        except Exception as e:
            # 어떤 주소에서 실패했는지 화면에 출력하고 다음 주소로 넘어감
            print(f"  [{source['name']} 실패] {url} → {e} (건너뜀)")

    return items  # 전부 실패하면 빈 목록


# ---------------------------------------------------------------------
# 3) HTML 대시보드 조립
# ---------------------------------------------------------------------
def build_html(all_data):
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = ""

    # 소스 이름 -> {아이콘, 카테고리} 찾아보기 (카드가 비어도 라벨 표시하려고)
    source_meta = {s["name"]: s for s in RSS_SOURCES}

    for source_name, items in all_data.items():
        meta = source_meta.get(source_name, {})
        icon = meta.get("icon") or (items[0]["icon"] if items else "📄")
        category = meta.get("category", "")
        badge = (
            f'<span class="badge">{html_lib.escape(category)}</span>'
            if category else ""
        )
        rows = ""
        for it in items:
            t = html_lib.escape(it["title"])
            s = html_lib.escape(it.get("summary", ""))
            summary_html = f'<span class="summary">{s}</span>' if s else ""
            rows += (
                f'<li><a href="{it["link"]}" target="_blank">{t}</a>'
                f'{summary_html}</li>'
            )
        if not rows:
            rows = '<li class="empty">결과 없음 (RSS 피드 확인 필요)</li>'
        blocks += (
            f'<div class="card"><h3>{icon} {html_lib.escape(source_name)}{badge}</h3>'
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
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr));
           gap:16px; }}
  .card {{ background:#1e293b; border-radius:12px; padding:16px 18px; }}
  .card h3 {{ margin:0 0 10px; font-size:15px; color:#fbbf24; }}
  ul {{ list-style:none; margin:0; padding:0; }}
  li {{ padding:8px 0; border-bottom:1px solid #334155; font-size:14px; }}
  li:last-child {{ border-bottom:none; }}
  a {{ color:#e2e8f0; text-decoration:none; }}
  a:hover {{ color:#38bdf8; }}
  .summary {{ display:block; color:#64748b; font-size:12px; margin-top:3px;
              line-height:1.4; }}
  .empty {{ color:#64748b; }}
  .badge {{ display:inline-block; margin-left:8px; padding:2px 8px; font-size:11px;
            border-radius:10px; background:#38bdf8; color:#0f172a; vertical-align:middle; }}
  #filter {{ width:100%; max-width:520px; box-sizing:border-box; padding:12px 16px;
             margin-bottom:8px; font-size:15px; border-radius:10px;
             border:1px solid #334155; background:#1e293b; color:#e2e8f0; }}
  #filter::placeholder {{ color:#64748b; }}
  .card.hidden, li.hidden {{ display:none; }}
</style>
</head>
<body>
  <h1>🛩️ MoneyPilot 글감 대시보드</h1>
  <div class="date">수집 시각: {today} | 소스: CFPB · Federal Reserve · FDIC · SBA · SSA · FTC · VA · IRS</div>

  <input id="filter" placeholder="🔍 글감 검색 — 키워드를 입력하면 관련 글만 보여요"
         oninput="filterItems()">

  <div class="section-title">📰 미국 정부 공식 금융·혜택 뉴스</div>
  <div class="grid">{blocks}</div>

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
    card.classList.toggle('hidden', !anyVisible);
  }});
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------
# 4) 메인 실행
# ---------------------------------------------------------------------
def main():
    print("글감 수집 시작... (CFPB · Federal Reserve · FDIC · SBA · SSA)")
    all_data = {}

    for source in RSS_SOURCES:
        print(f"  {source['icon']} {source['name']} 가져오는 중...")
        items = get_rss_feed(source)
        all_data[source["name"]] = items
        print(f"     → {len(items)}개 수집")

    html = build_html(all_data)

    import os
    folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(folder, "money_dashboard.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    silent = "--silent" in sys.argv
    if silent:
        print(f"완료! (조용한 모드) 저장됨: {filepath}")
    else:
        print(f"완료! '{filepath}' 파일을 브라우저로 엽니다.")
        webbrowser.open(filepath)


if __name__ == "__main__":
    main()
