import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter

CRAWL_STATS = {
    "unique_urls": set(),
    "longest_page": {"url": "", "word_count": 0},
    "word_frequencies": Counter(),
    "subdomains": Counter()
}

STOP_WORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at", "be",
    "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "did", "do", "does", "doing",
    "don", "down", "during", "each", "few", "for", "from", "further", "had", "has", "have", "having", "here", "how",
    "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s",
    "same", "she", "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with", "you", "your",
    "yours", "yourself", "yourselves"
])


def scraper(url, resp):
    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]

    if resp.status == 200 and resp.raw_response:
        content = resp.raw_response.content
        soup = BeautifulSoup(content, "lxml")

        text = soup.get_text(separator=' ', strip=True).lower()
        words = re.findall(r'[a-zA-Z0-9]{3,}', text)

        word_count = len(words)
        if word_count > CRAWL_STATS["longest_page"]["word_count"]:
            CRAWL_STATS["longest_page"] = {"url": url, "word_count": word_count}

        meaningful_words = [w for w in words if w not in STOP_WORDS]
        CRAWL_STATS["word_frequencies"].update(meaningful_words)

        parsed = urlparse(url)
        allowed_subdomains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]

        if any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in allowed_subdomains):
            if url not in CRAWL_STATS["unique_urls"]:
                CRAWL_STATS["subdomains"][parsed.netloc] += 1

        CRAWL_STATS["unique_urls"].add(url)

        try:
            with open("stats_report.txt", "w") as f:
                f.write(f"Unique Pages: {len(CRAWL_STATS['unique_urls'])}\n")
                f.write(
                    f"Longest Page: {CRAWL_STATS['longest_page']['url']} ({CRAWL_STATS['longest_page']['word_count']} words)\n")
                f.write(f"Top 50 Words: {CRAWL_STATS['word_frequencies'].most_common(50)}\n")
                f.write(f"Subdomains (uci.edu): {dict(sorted(CRAWL_STATS['subdomains'].items()))}\n")
                f.flush()
        except Exception:
            pass

    return valid_links


def extract_next_links(url, resp):
    found_links = set()
    if resp.status == 200 and resp.raw_response and resp.raw_response.content:
        try:
            soup = BeautifulSoup(resp.raw_response.content, "lxml")
            for link in soup.find_all('a', href=True):
                href = urljoin(resp.url, link['href'])
                clean_url = href.split('#')[0]
                found_links.add(clean_url)
        except Exception:
            pass
    return list(found_links)


def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False

        allowed_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        if not any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in allowed_domains):
            return False

        if "doku.php" in parsed.path.lower():
            if "do=" in parsed.query.lower() or "rev=" in parsed.query.lower():
                return False

        if "archive.ics.uci.edu" in parsed.netloc:
            if "/datasets" in parsed.path or "search" in parsed.query or "Keywords" in parsed.query:
                return False

        trap_pattern = r".*(calendar|date|event|gallery|wp-content|login|share|action=).*"
        if re.match(trap_pattern, parsed.path.lower()) or re.match(trap_pattern, parsed.query.lower()):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        return False