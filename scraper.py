import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import json

longest_page = dict() # url, length in words, for finding longest page in terms of number of words excluding stopwords
word_frequencies = dict() # word, frequency, for finding top 50 most common words
subdomains = dict() # subdomain (ie vision.uci.edu), number of pages in it. you can count # of unique pages by summing values of this dictionary
seen_urls = set()

STOPWORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he",
    "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me",
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves"
])

crawled_num = 0
SAVE_EVERY_X_PAGES = 100

def scraper(url, resp):
    links = extract_next_links(url, resp)
    process_url_for_report(url, resp)
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

    links_found = []

    #checks if the status is an error
    if resp.status != 200 or resp.raw_response is None:
        print(f'Resp error: {resp.error}') #prints error number (404 and such)
        return links_found
    
    try:
        #goes through the content of the page (HTML) and grabs each tag (headers, paragrpahs, etc)
        html_content = BeautifulSoup(resp.raw_response.content, 'html.parser') 

        #loops through all the link tags <a> that have a href value (actual link)
        for links in html_content.find_all('a', href=True): 
            href = links.get('href') #gets the actual link (relative)
            abs_url = urldefrag(urljoin(url, href))[0] #removes the fragment part of the absolute URL (url + href/relative url), does not save the fragment part (i.e. getting the first element)
            links_found.append(abs_url)
    except Exception as e:
        print(f'There was an issue grabbing a link from {url}: {e}')
    return links_found

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]
        domain = parsed.netloc.lower()
        #Found how to check for certain text pattern using regrex (This checks for yyyy-mm-dd)
        if 'today.uci.edu' == domain and not parsed.path.startswith("/department/information_computer_sciences/"): #checks if the path today domain is a specific path
            return False
        #check if the domain ends with .allowedDomains, but also checks if the domain itself is an allowed domain (no .allowedDomain, but just allowedDomain)
        elif not any(domain == allowed or domain.endswith("." + allowed) for allowed in allowed_domains): #checks if parsed domain has any of the allowed domains
            return False
        
        unallowed_queries = [
            "ical=",
            "outlook-ical=",
            "tribe-bar-date=",
            "eventDate=",
            "paged=",
            "eventDisplay="
        ]
        #may be inificient
        if any(query in parsed.query for query in unallowed_queries): #checks if parsed queries have any of the unallowed_queries
            return False
        
        #Checking for specific traps
        #Kept seeing same pattern, but for different directories <path>/YYYY-MM
        #Found [^/]+ which is like a stand-in that can be some sub-path
        if re.search(
            r'(day/\d{4}-\d{2}-\d{2}|events/\d{4}-\d{2}-\d{2}' +
            r'|/events/category/[^/]+/\d{4}-\d{2}|events/[^/]+/\d{4}-\d{2}' +
            r'|/talks/\d{4}-\d{2}-\d{2})', parsed.path):
            return False
        
        
        #FIXME - Do we want php files?
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz|php)$", parsed.path.lower())
                                                #Want this?
    except TypeError:
        print ("TypeError for ", parsed)
        raise

def process_url_for_report(url, resp):
    if resp.status != 200 or resp.raw_response is None:
        print(f'Resp error: {resp.error}')
        return

    # global word_frequencies
    # global longest_page

    # defrag the url to get just the domain
    defragged_url = urldefrag(url)[0]
    parsed_url = urlparse(defragged_url)

    #unique pages
    if defragged_url not in seen_urls:
        seen_urls.add(defragged_url)

    # add the subdomain to the dictionary and increment by 1
    if parsed_url.netloc.endswith(".uci.edu"):
        subdomains[parsed_url.netloc] = subdomains.get(parsed_url.netloc, 0) + 1

    html_content = BeautifulSoup(resp.raw_response.content, 'html.parser')
    words = html_content.get_text(separator=' ', strip=True).split()

    words_without_stopwords = [word.lower() for word in words if word.lower() not in STOPWORDS]

    for word in words_without_stopwords:
        word_frequencies[word] = word_frequencies.get(word, 0) + 1

    longest_page[defragged_url] = len(words) #FIXME - may have to change to words_without_stopwords

    # if parsed_url not in longest_page:
    #     # count the number of words in the page and add the url and its word count to the dictionary
    #     html_content = BeautifulSoup(resp.raw_response.content, 'html.parser')
    #     words = html_content.get_text(strip=True).split()

    #     # count the word frequency
    #     for word in words:
    #         word_frequencies[word] += 1

    #     longest_page[parsed.netloc] = len(words)

    # save the report json every X crawls
    global crawled_num
    crawled_num += 1
    if crawled_num % SAVE_EVERY_X_PAGES == 0:
        save_report()

    # to count the number of subdomain pages, we add the subdomain to the dictionary
    # and then add it by 1 each time we encounter the subdomain

def save_report():
    report = {
        "unique pages": len(seen_urls),
        "subdomains": dict(sorted(subdomains.items(), key=lambda item: item[1], reverse=True)),
        "word frequencies": sorted(word_frequencies.items(), key=lambda item: item[1], reverse=True)[:50],
        "longest page": max(longest_page.items())
    }
    with open("report/report.json", "w") as f:
        json.dump(report, f, indent=2)