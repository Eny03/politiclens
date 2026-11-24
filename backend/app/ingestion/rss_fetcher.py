import datetime
from typing import List, Dict, Any
import feedparser
from dateutil import parser as date_parser
from app.ingestion.sources_config import MONITORED_FEEDS
from app.ingestion.text_extractor import detect_entities, clean_html

def parse_entry_datetime(entry: Any) -> datetime.datetime:
    """Parses entry publication timestamp with fallbacks."""
    if hasattr(entry, "published"):
        try:
            return date_parser.parse(entry.published).replace(tzinfo=None)
        except Exception:
            pass
    if hasattr(entry, "updated"):
        try:
            return date_parser.parse(entry.updated).replace(tzinfo=None)
        except Exception:
            pass
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def fetch_rss_feed_entries(feed_info: Dict[str, Any], max_items: int = 10) -> List[Dict[str, Any]]:
    """
    Parses an RSS feed and filters items containing relevant political entities or topics.
    """
    url = feed_info["url"]
    feed_name = feed_info["name"]
    items = []
    
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            feed_content = resp.read()
        parsed = feedparser.parse(feed_content)
        for entry in parsed.entries[:max_items]:
            title = entry.title if hasattr(entry, "title") else ""
            link = entry.link if hasattr(entry, "link") else ""
            summary = entry.summary if hasattr(entry, "summary") else ""
            clean_summary = clean_html(summary) if summary else ""
            pub_date = parse_entry_datetime(entry)
            
            combined_text = f"{title}. {clean_summary}"
            parties, topics = detect_entities(combined_text)
            
            # Keep if any party or relevant macro-topic is mentioned
            if parties or topics:
                items.append({
                    "title": title,
                    "url": link,
                    "summary": clean_summary,
                    "source_name": feed_name,
                    "published_at": pub_date,
                    "detected_parties": parties,
                    "detected_topics": topics,
                    "raw_text": combined_text
                })
    except Exception as e:
        print(f"[RSSFetcher] Error parsing {feed_name} ({url}): {e}")
        
    return items

import concurrent.futures

def fetch_all_active_feeds(max_items_per_feed: int = 10) -> List[Dict[str, Any]]:
    """Fetches articles from all active RSS feeds in parallel."""
    active_feeds = [f for f in MONITORED_FEEDS if f.get("is_active", True)]
    all_articles = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_feed = {
            executor.submit(fetch_rss_feed_entries, feed, max_items_per_feed): feed
            for feed in active_feeds
        }
        for future in concurrent.futures.as_completed(future_to_feed):
            try:
                items = future.result()
                all_articles.extend(items)
            except Exception as e:
                feed = future_to_feed[future]
                print(f"[RSSFetcher] Parallel worker failed for {feed.get('name')}: {e}")
                
    return all_articles
