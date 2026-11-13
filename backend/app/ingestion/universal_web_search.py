import urllib.parse
import urllib.request
import datetime
import socket
import json
import re
from typing import List, Dict, Any
import feedparser
from bs4 import BeautifulSoup
from app.ingestion.text_extractor import detect_entities, clean_html

# Fast network socket timeout
socket.setdefaulttimeout(4)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 PoliticLens/2.0"

def search_web_news(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Searches the entire web for real-time political news, statements, and debates
    using Google News RSS Search which indexes all Italian media, journals, regional portals,
    and official institutional announcements.
    """
    encoded_query = urllib.parse.quote(query)
    feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=it&gl=IT&ceid=IT:it"
    results = []

    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read()
        parsed = feedparser.parse(content)
        for entry in parsed.entries[:max_results]:
            title = entry.title if hasattr(entry, "title") else ""
            link = entry.link if hasattr(entry, "link") else ""
            summary = entry.summary if hasattr(entry, "summary") else ""
            clean_summary = clean_html(summary) if summary else ""
            
            source_title = "Web & Stampa Nazionale"
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source_title = entry.source.title

            combined_text = f"{title}. {clean_summary}"
            parties, topics = detect_entities(combined_text)

            results.append({
                "title": title,
                "url": link,
                "summary": clean_summary,
                "source_name": source_title,
                "published_at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                "detected_parties": parties,
                "detected_topics": topics,
                "raw_text": combined_text
            })
    except Exception as e:
        print(f"[UniversalWebSearch] Error querying '{query}': {e}")

    return results

def search_duckduckgo_open_web(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches the open web via DuckDuckGo HTML for wide Italian politics topics,
    official declarations, and party websites.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    results = []

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as response:
            html = response.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            
            for item in soup.find_all("div", class_="result")[:max_results]:
                title_elem = item.find("a", class_="result__a")
                snippet_elem = item.find("a", class_="result__snippet")
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    combined_text = f"{title}. {snippet}"
                    parties, topics = detect_entities(combined_text)
                    
                    if len(combined_text.strip()) > 20:
                        results.append({
                            "title": title,
                            "url": link,
                            "summary": snippet,
                            "source_name": "Open Web Search",
                            "published_at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                            "detected_parties": parties,
                            "detected_topics": topics,
                            "raw_text": combined_text
                        })
    except Exception as e:
        # DDG HTML search might be rate-limited, safely fall back
        pass

    return results

def search_historical_political_news(query: str, year: int = 2023, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches historical news archives via Google News RSS with strict yearly range filters.
    Enables autonomous ingestion of past legislative debates and program evolutions (2022-2025).
    """
    date_filtered_query = f"{query} after:{year}-01-01 before:{year+1}-01-01"
    encoded_query = urllib.parse.quote(date_filtered_query)
    feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=it&gl=IT&ceid=IT:it"
    results = []

    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read()
        parsed = feedparser.parse(content)
        for entry in parsed.entries[:max_results]:
            title = entry.title if hasattr(entry, "title") else ""
            link = entry.link if hasattr(entry, "link") else ""
            summary = entry.summary if hasattr(entry, "summary") else ""
            clean_summary = clean_html(summary) if summary else ""
            
            source_title = f"Archivio Web {year}"
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source_title = f"{entry.source.title} ({year})"

            combined_text = f"{title}. {clean_summary}"
            parties, topics = detect_entities(combined_text)

            results.append({
                "title": title,
                "url": link,
                "summary": clean_summary,
                "source_name": source_title,
                "published_at": datetime.datetime(year, 6, 15),
                "detected_parties": parties,
                "detected_topics": topics,
                "raw_text": combined_text
            })
    except Exception as e:
        print(f"[UniversalWebSearch] Error in historical query '{query}' for year {year}: {e}")

    return results
