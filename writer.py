# -*- coding: utf-8 -*-
# =====================================================================
#  MoneyPilot 블로그 초안 생성기
#  - 글감 목록 → 번호 선택
#  - Notion에 초안 페이지 자동 생성 (제목·출처·날짜·상태)
#  - claude.ai에 붙여넣을 프롬프트 출력
#  ※ Anthropic API 키 불필요 — Claude Pro 구독으로 사용
#  소스: CFPB · IRS · Benefits.gov (미국 정부 공식 사이트)
# =====================================================================

import os
import sys
import re
import datetime

import requests
import feedparser

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from notion_client import Client as NotionClient
except ImportError:
    print("❌ notion-client 패키지가 없어요.")
    print("   pip install notion-client python-dotenv requests feedparser")
    sys.exit(1)


# ---------------------------------------------------------------------
# 1) RSS 소스 목록 (glamcollector.py와 동일)
# ---------------------------------------------------------------------
RSS_SOURCES = [
    {
        "name": "CFPB Newsroom",
        "url": "https://www.consumerfinance.gov/about-us/newsroom/feed/",
        "icon": "🏛️",
    },
    {
        "name": "CFPB Blog",
        "url": "https://www.consumerfinance.gov/about-us/blog/feed/",
        "icon": "📝",
    },
    {
        "name": "IRS News Releases",
        "url": "https://www.irs.gov/pub/irs-utl/IRSNewswire.rss",
        "icon": "💰",
    },
    {
        "name": "IRS Tax Tips",
        "url": "https://www.irs.gov/pub/irs-utl/IRSTaxTip.rss",
        "icon": "💡",
    },
    {
        "name": "Benefits.gov",
        "url": "https://www.benefits.gov/rss",
        "icon": "🎁",
    },
]

MAX_PER_SOURCE = 8


# ---------------------------------------------------------------------
# 2) RSS 피드 가져오기
# ---------------------------------------------------------------------
def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def get_rss_feed(source):
    items = []
    try:
        headers = {"User-Agent": "MoneyPilot/1.0 (finance research bot)"}
        raw = requests.get(source["url"], headers=headers, timeout=15)
        raw.raise_for_status()
        feed = feedparser.parse(raw.content)
        for entry in feed.entries[:MAX_PER_SOURCE]:
            title = strip_html(entry.get("title", ""))
            link = entry.get("link", "#")
            summary = strip_html(entry.get("summary", ""))[:500]
            if title:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": source["name"],
                    "icon": source["icon"],
                })
    except Exception as e:
        print(f"  [{source['name']} 오류] {e}")
    return items


# ---------------------------------------------------------------------
# 3) 글감 수집 → 중복 제거 → 번호 목록 출력
# ---------------------------------------------------------------------
def collect_and_show():
    print("\n📡 글감 수집 중... (CFPB · IRS · Benefits.gov)\n")
    all_articles = []

    for source in RSS_SOURCES:
        print(f"  {source['icon']} {source['name']}")
        all_articles.extend(get_rss_feed(source))

    seen = set()
    unique = []
    for a in all_articles:
        if a["title"] and a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)

    print(f"\n{'=' * 65}")
    print(f"  총 {len(unique)}개 글감 수집 완료")
    print(f"{'=' * 65}\n")

    for i, a in enumerate(unique, 1):
        print(f"  {i:3}. {a['icon']} [{a['source']}]")
        print(f"       {a['title']}")

    print(f"\n{'=' * 65}")
    return unique


# ---------------------------------------------------------------------
# 4) Notion에 빈 초안 페이지 생성
# ---------------------------------------------------------------------
def create_notion_draft(article):
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DATABASE_ID")

    if not token or not db_id:
        print("\n⚠️  .env 파일에 NOTION_TOKEN 또는 NOTION_DATABASE_ID가 없어요.")
        return None

    try:
        notion = NotionClient(auth=token)
        today = datetime.date.today().isoformat()
        source_text = f"{article['source']} — {article['link']}"

        page = notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "제목": {
                    "title": [{"text": {"content": article["title"][:2000]}}]
                },
                "출처 글감": {
                    "rich_text": [{"type": "text", "text": {
                        "content": source_text[:2000]
                    }}]
                },
                "작성일": {
                    "date": {"start": today}
                },
                "상태": {
                    "status": {"name": "초안"}
                },
            },
            children=[
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {
                            "content": "✍️ 아래에 claude.ai 결과를 붙여넣으세요."
                        }}],
                        "icon": {"emoji": "📋"},
                        "color": "yellow_background",
                    },
                }
            ],
        )

        return page.get("url")

    except Exception as e:
        print(f"\n⚠️  Notion 저장 실패: {e}")
        return None


# ---------------------------------------------------------------------
# 5) claude.ai에 붙여넣을 프롬프트 출력
# ---------------------------------------------------------------------
def print_claude_prompt(article):
    summary_section = ""
    if article.get("summary"):
        summary_section = f"\nOriginal summary: {article['summary']}\n"

    prompt = f"""Write a complete, engaging English blog post for an American audience.

Topic: {article['title']}
Source: {article['source']}
Reference URL: {article['link']}{summary_section}

Requirements:
- Target audience: Americans who want to use AI to improve their personal finances
- Tone: Friendly, practical, conversational — like a smart friend giving advice
- Blog theme: AI × personal finance (how AI tools help with money habits)
- Length: 800–1,000 words
- Structure:
  # [SEO-optimized title]

  [Hook paragraph — relatable money problem or surprising stat]

  ## [Section 1 heading]
  [Content]

  ## [Section 2 heading]
  [Content]

  ## [Section 3 heading]
  [Content — include 3–5 actionable tips as a bullet list]

  ## Final Thoughts
  [Conclusion + call-to-action]

- Plain English, no jargon
- Do NOT plagiarize the source — use it as inspiration only
- Ready to paste into WordPress

Write the full post now."""

    print("\n" + "=" * 65)
    print("  📋 아래 프롬프트를 복사해서 claude.ai에 붙여넣으세요")
    print("=" * 65)
    print(prompt)
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------
# 6) 메인 실행
# ---------------------------------------------------------------------
def main():
    print("\n🛩️  MoneyPilot 블로그 초안 생성기")
    print("   글감 선택 → Notion 페이지 자동 생성 → claude.ai 프롬프트 출력\n")

    articles = collect_and_show()
    if not articles:
        print("글감을 가져오지 못했어요. 인터넷 연결을 확인해주세요.")
        return

    print("번호를 입력하면 Notion 페이지를 만들고 프롬프트를 출력해줍니다.")
    print("(0을 입력하면 종료)\n")

    while True:
        try:
            raw = input("  번호 선택 → ").strip()
            if raw == "0":
                print("종료합니다.")
                break
            choice = int(raw)
            if 1 <= choice <= len(articles):
                article = articles[choice - 1]

                print(f"\n📝 Notion에 초안 페이지 만드는 중...")
                page_url = create_notion_draft(article)

                if page_url:
                    print(f"✅ Notion 페이지 생성 완료!")
                    print(f"   → {page_url}")

                print_claude_prompt(article)

                print("  [다음 할 일]")
                print("  1. 위 프롬프트 복사 → claude.ai 에 붙여넣기 → 블로그 글 받기")
                if page_url:
                    print(f"  2. Notion 페이지 열기: {page_url}")
                    print("  3. claude.ai 결과를 Notion 페이지 본문에 붙여넣기")
                print()
                break

            print(f"  1 ~ {len(articles)} 사이 숫자를 입력해주세요.")
        except ValueError:
            print("  숫자만 입력해주세요.")
        except KeyboardInterrupt:
            print("\n종료합니다.")
            break


if __name__ == "__main__":
    main()
