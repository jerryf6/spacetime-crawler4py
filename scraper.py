import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    found_links = set()
    if resp.status == 200 and resp.raw_response and resp.raw_response.content:
        try:
            soup = BeautifulSoup(resp.raw_response.content, "lxml")
            for link in soup.find_all('a', href=True):
                href = urljoin(resp.url, link['href'])
                clean_url = href.split('#')[0]
                found_links.add(clean_url)
        except Exception as e:
            print(e)

    return list(found_links)


def is_valid(url):
    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        allowed_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]

        if parsed.scheme not in set(["http", "https"]):
            return False

        is_allowed_domain = any(parsed.netloc == d or parsed.netloc.endswith("." + d)
                                for d in allowed_domains)

        if not is_allowed_domain:
            return False

        if re.match(r".*(calendar|date|event|gallery|zip|tar|gz|archive|wp-content).*", parsed.path.lower()) or \
                re.match(r".*(calendar|date|event|gallery).*", parsed.query.lower()):
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
        print("TypeError for ", parsed)
        raise