import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter

# Crawling stats
CRAWL_STATS = {
    "unique_urls": set(),
    "longest_page": {"url": "", "word_count": 0},
    "word_frequencies": Counter(),
    "subdomains": Counter()
}

# Stop words list
STOP_WORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be",
    "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
    "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from",
    "further",
    "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's",
    "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
    "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd",
    "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
    "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
])


def scraper(url, resp):
    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]

    if resp.status == 200 and resp.raw_response:
        ctype = resp.raw_response.headers.get('Content-Type', '').lower()
        if 'text/html' not in ctype:
            return valid_links

        try:
            content = resp.raw_response.content
            soup = BeautifulSoup(content, "lxml")
            text = soup.get_text(separator=' ', strip=True).lower()


            words = re.findall(r'[a-zA-Z0-9]{3,}', text)

            word_count = len(words)
            if word_count < 20:
                return valid_links

            if word_count > CRAWL_STATS["longest_page"]["word_count"]:
                CRAWL_STATS["longest_page"] = {"url": url, "word_count": word_count}

            meaningful_words = [w for w in words if w not in STOP_WORDS]
            CRAWL_STATS["word_frequencies"].update(meaningful_words)

            parsed = urlparse(url)
            allowed_subdomains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]

            if url not in CRAWL_STATS["unique_urls"]:
                if any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in allowed_subdomains):
                    CRAWL_STATS["subdomains"][parsed.netloc] += 1

            CRAWL_STATS["unique_urls"].add(url)

            with open("stats_report.txt", "w") as f:
                f.write(f"Unique Pages: {len(CRAWL_STATS['unique_urls'])}\n")
                f.write(f"Longest Page: {CRAWL_STATS['longest_page']['url']} ({CRAWL_STATS['longest_page']['word_count']} words)\n")
                f.write(f"Top 50 Words: {CRAWL_STATS['word_frequencies'].most_common(50)}\n")
                f.write(f"Subdomains: {dict(sorted(CRAWL_STATS['subdomains'].items()))}\n")

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
                clean_url = href.split('#')[0].rstrip('/')
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

        # Common Crawler Traps:

        # DokuWiki traps
        if "doku.php" in parsed.path.lower():
            if any(p in parsed.query.lower() for p in ["do=", "rev=", "idx="]):
                return False

        # Chemical database traps
        bad_subdomains = ["cdb.ics", "chemdb", "proteomics", "deeprxn"]
        if any(sub in parsed.netloc.lower() for sub in bad_subdomains):
            return False
        if "smiles" in parsed.path.lower():
            return False

        # ML Archive loop traps
        if "archive.ics.uci.edu" in parsed.netloc:
            if "/datasets" in parsed.path or "search" in parsed.query or "Keywords" in parsed.query:
                return False

        # General traps (calendars, logins, etc)
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