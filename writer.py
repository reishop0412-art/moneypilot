# -*- coding: utf-8 -*-
# =====================================================================
#  MoneyPilot 블로그 초안 생성기
#  - 글감 목록 → 번호 선택
#  - Notion에 초안 페이지 자동 생성 (제목·출처·날짜·상태)
#  - claude.ai에 붙여넣을 프롬프트 출력
#  ※ Anthropic API 키 불필요 — Claude Pro 구독으로 사용
#  소스: CFPB · Federal Reserve · FDIC · SBA · SSA (미국 정부 공식 사이트)
# =====================================================================

import os
import sys
import re
import datetime

import requests
import feedparser

# Windows 터미널에서 이모지 출력 시 에러 방지 (UTF-8 강제)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
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
    print("\n📡 글감 수집 중... (CFPB · Federal Reserve · FDIC · SBA · SSA)\n")
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
# 4) Notion 페이지 본문 조립 (영어 원문 + 요약본 자리)
# ---------------------------------------------------------------------
def _text_blocks(text, block_type="paragraph"):
    """긴 텍스트를 Notion 블록으로 변환 (한 블록당 2000자 제한 대응)."""
    text = (text or "").strip()
    if not text:
        return []
    chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
    return [{
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": [{"type": "text", "text": {"content": c}}]},
    } for c in chunks]


def build_page_body(article):
    """페이지 본문: 📄 영어 원문 + ✍️ 요약본(붙여넣기 자리)."""
    original = article.get("summary") or "(RSS에 원문 요약이 없어요. 위 출처 링크에서 전체 원문을 확인하세요.)"

    body = []
    # --- 📄 영어 원문 섹션 ---
    body.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📄 English Source (영어 원문)"}}]},
    })
    body.extend(_text_blocks(original))
    body.append({
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text",
            "text": {"content": f"🔗 전체 원문 보기: {article['link']}", "link": {"url": article["link"]}}}]},
    })

    body.append({"object": "block", "type": "divider", "divider": {}})

    # --- ✍️ 요약본 섹션 ---
    body.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "✍️ Summary (요약본 — 6단계 템플릿)"}}]},
    })
    body.append({
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {
                "content": "터미널에 출력된 프롬프트를 claude.ai에 붙여넣고, 나온 결과를 이 아래에 붙여넣으세요."
            }}],
            "icon": {"emoji": "📋"},
            "color": "yellow_background",
        },
    })
    return body


# ---------------------------------------------------------------------
# 5) Notion에 초안 페이지 생성
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
            children=build_page_body(article),
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
Source: {article['source']} (official U.S. government)
Reference URL: {article['link']}{summary_section}

Audience: Americans looking to claim a benefit or save on taxes.
Tone: Friendly, practical, conversational — like a smart friend explaining money.
Length: 900–1,200 words. Plain English, no jargon. Ready to paste into WordPress.
Do NOT copy the source text — rewrite everything in your own words.

Use EXACTLY this structure (keep the Markdown headings):

# How to [Get This Benefit / Save on Taxes] in 2026 — Full Guide

## 1. What is it?
[One easy paragraph explaining it simply.]

## 2. Who qualifies?
[Eligibility conditions as a bullet list.]

## 3. How much can you get?
[Dollar amounts as a Markdown table, e.g. income/family size vs amount.]

## 4. How to apply
[Step-by-step numbered instructions.]

## 5. Common mistakes to avoid
[Bullet list of mistakes people make.]

## 6. What this means for you
[YOUR analysis — this is the most important section. Give practical takeaways,
who benefits most, and 2–3 concrete action steps the reader can take today.]

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
