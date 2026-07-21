# -*- coding: utf-8 -*-
import json
import requests
import feedparser
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- BILD CONFIG ---
BILD_CATEGORIES = {
    "Top-News": "https://www.bild.de/feed/alles.xml",
    "Politik": "https://www.bild.de/rss-feeds/rss-16725492,feed=politik.bild.html",
    "News": "https://www.bild.de/rss-feeds/rss-16725492,feed=news.bild.html",
    "Sport": "https://www.bild.de/rss-feeds/rss-16725492,feed=sport.bild.html",
    "Unterhaltung": "https://www.bild.de/rss-feeds/rss-16725492,feed=unterhaltung.bild.html",
    "Lifestyle": "https://www.bild.de/rss-feeds/rss-16725492,feed=lifestyle.bild.html",
    "Auto": "https://www.bild.de/rss-feeds/rss-16725492,feed=auto.bild.html",
    "Ratgeber": "https://www.bild.de/rss-feeds/rss-16725492,feed=ratgeber.bild.html",
}

# --- TAGESSCHAU CONFIG ---
TAGESSCHAU_CATEGORIES = {
    "Top-News": "https://www.tagesschau.de/infoservices/alle-meldungen~rss2.xml",
    "Inland": "https://www.tagesschau.de/inland/index~rss2.xml",
    "Ausland": "https://www.tagesschau.de/ausland/index~rss2.xml",
    "Wirtschaft": "https://www.tagesschau.de/wirtschaft/index~rss2.xml",
    "Investigativ": "https://www.tagesschau.de/investigativ/index~rss2.xml",
}


def get_article_text(url, source_type):
    """Holt den Volltext abhängig von der Quelle (BILD vs. Tagesschau)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(response.text, "html.parser")
        article_text = []

        if source_type == "BILD":
            selectors = [
                'article p', '.article-body p', '.txt p',
                '.post-content p', '[data-key="article"] p'
            ]
            for selector in selectors:
                paragraphs = soup.select(selector)
                if paragraphs:
                    for p in paragraphs:
                        text = p.get_text(" ", strip=True)
                        if len(text) > 40 and "In App öffnen" not in text:
                            article_text.append(text)
                    if article_text:
                        break

        elif source_type == "ÖRR":
            # Spezifische HTML-Selektoren für Tagesschau-Artikel
            paragraphs = soup.select('article p.textabsatz, .m-articlebody p, .article p')
            for p in paragraphs:
                text = p.get_text(" ", strip=True)
                if len(text) > 30:
                    article_text.append(text)

        if not article_text:
            return f"Volltext konnte nicht automatisch geladen werden. Bitte nutze den Link unten, um direkt zu {source_type} zu gelangen."

        # Duplikate entfernen und Text zusammensetzen
        cleaned = []
        for line in article_text:
            if line not in cleaned:
                cleaned.append(line)
        return "\n\n".join(cleaned)

    except Exception as e:
        return f"Fehler beim Scrapen des Volltextes: {str(e)}"


def build_news_json():
    compiled_news = []
    seen_links = set()

    # --- 1. BILD.DE SCRAPEN ---
    print("--- Starte Aggregation: BILD.de ---")
    for category_name, feed_url in BILD_CATEGORIES.items():
        print(f"BILD -> Kategorie: {category_name}")
        try:
            response = requests.get(feed_url, headers=HEADERS, timeout=8)
            if response.status_code != 200:
                print(f" -> Fehler {response.status_code}, überspringe...")
                continue
            feed = feedparser.parse(response.text)
        except Exception as e:
            print(f" -> Fehler beim Abruf von {category_name}: {e}")
            continue

        for entry in feed.entries[:10]:  # Limit leicht reduziert, um Laufzeit klein zu halten
            link = entry.get("link", "")
            if not link or link in seen_links:
                continue

            title = entry.get("title", "Ohne Titel")
            summary = entry.get("summary", "")

            print(f" -> Scrape BILD: {title[:35]}...")
            full_text = get_article_text(link, source_type="BILD")

            article_node = {
                "title": title,
                "plot": summary if summary else "Keine Kurzbeschreibung verfügbar.",
                "text": full_text,
                "video_url": link,
                "thumb": "https://www.bild.de/favicon.ico",
                "rating": "BILD",
                "channel": "BILD.de",
                "source": "BILD",  # Unterscheidungsmerkmal
                "year": "Heute",
                "genres_list": [category_name],
                "category": category_name
            }

            compiled_news.append(article_node)
            seen_links.add(link)

    # --- 2. TAGESSCHAU (ÖRR) SCRAPEN ---
    print("\n--- Starte Aggregation: Tagesschau (ÖRR) ---")
    for category_name, feed_url in TAGESSCHAU_CATEGORIES.items():
        print(f"Tagesschau -> Kategorie: {category_name}")
        try:
            response = requests.get(feed_url, headers=HEADERS, timeout=8)
            if response.status_code != 200:
                print(f" -> Fehler {response.status_code}, überspringe...")
                continue
            feed = feedparser.parse(response.text)
        except Exception as e:
            print(f" -> Fehler beim Abruf von {category_name}: {e}")
            continue

        for entry in feed.entries[:10]:
            link = entry.get("link", "")
            if not link or link in seen_links:
                continue

            title = entry.get("title", "Ohne Titel")
            summary = entry.get("summary", "")

            # HTML-Tags aus Tagesschau-RSS-Descriptions entfernen
            if summary:
                summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)

            print(f" -> Scrape ÖRR: {title[:35]}...")
            full_text = get_article_text(link, source_type="ÖRR")

            article_node = {
                "title": title,
                "plot": summary if summary else "Keine Kurzbeschreibung verfügbar.",
                "text": full_text,
                "video_url": link,
                "thumb": "https://www.tagesschau.de/favicon.ico",
                "rating": "ÖRR",
                "channel": "Tagesschau",
                "source": "ÖRR",  # Unterscheidungsmerkmal
                "year": "Heute",
                "genres_list": [category_name],
                "category": category_name
            }

            compiled_news.append(article_node)
            seen_links.add(link)

    # --- 3. SPEICHERN ---
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(compiled_news, f, ensure_ascii=False, indent=2)

    print(f"\nFertig! Insgesamt {len(compiled_news)} Artikel (BILD & ÖRR) in news.json gespeichert.")


if __name__ == '__main__':
    build_news_json()
