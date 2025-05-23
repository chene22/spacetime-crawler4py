import re
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs
from bs4 import BeautifulSoup
from datetime import datetime
import json
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
STOPWORDS = set(stopwords.words('english'))

longest_page = dict() # url, length in words, for finding longest page in terms of number of words excluding stopwords
word_frequencies = dict() # word, frequency, for finding top 50 most common words
subdomains = dict() # subdomain (ie vision.uci.edu), number of pages in it. you can count # of unique pages by summing values of this dictionary
seen_urls = set()

word_filter = re.compile(r'^[a-z]+$')

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
        if 'gitlab.ics.uci.edu' in parsed.netloc and ("/commit/" in parsed.query or "/commits/" in parsed.query): #Just a bunch of github content, needs log in and is mostly empty
            return False
        if parsed.netloc == "ngs.ics.uci.edu" and ("/tag/" in parsed.path or "wp-login.php" in parsed.path):
            return False
        if 'www.cert.ics.uci.edu' in parsed.netloc:
            return False
        #check if the domain ends with .allowedDomains, but also checks if the domain itself is an allowed domain (no .allowedDomain, but just allowedDomain)
        elif not any(domain == allowed or domain.endswith("." + allowed) for allowed in allowed_domains): #checks if parsed domain has any of the allowed domains
            return False
        
        unallowed_query_keys = [
            "ical", "outlook-ical", "tribe-bar-date", "eventDate", "paged",
            "eventDisplay", "do", "ns", "tab_files", "tab_details", 
            "subPage", "C", "O", "share", "from", "action"
        ]
        
        query_params = parse_qs(parsed.query)
        # Check if any of the unallowed query parameter keys exist in the query
        if any(key in query_params for key in unallowed_query_keys):
            return False
        
        #Checking for specific traps
        #Kept seeing same pattern, but for different directories <path>/YYYY-MM
        #Found [^/]+ which is like a stand-in that can be some sub-path
        #All [] keywords were found via the internet
        if re.search(
            r'(/day/\d{4}-\d{2}-\d{2}|/events/\d{4}-\d{2}-\d{2}' +
            r'|/events/category/[^/]+/\d{4}-\d{2}|/events/[^/]+/\d{4}-\d{2}/' +
            r'|/talks/\d{4}-\d{2}-\d{2}|/-/|/~eppstein/pix/)', parsed.path):
            return False
        
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|scm|rkt|pd|mpg"
            + r"|thmx|mso|arff|rtf|jar|csv|py|ip|ipynb"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz|md)$", parsed.path.lower())
    except TypeError:
        print ("TypeError for ", parsed)
        raise

def process_url_for_report(url, resp):
    if resp.status != 200 or resp.raw_response is None:
        print(f'Resp error: {resp.error}')
        return

    # defrag the url to get just the domain
    defragged_url = urldefrag(url)[0]
    parsed_url = urlparse(defragged_url)

    #unique pages
    if defragged_url not in seen_urls:
        seen_urls.add(defragged_url)

    # add the subdomain to the dictionary and increment by 1
    if parsed_url.netloc.endswith(".uci.edu"):
        subdomains[parsed_url.netloc] = subdomains.get(parsed_url.netloc, 0) + 1

    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    for tag in soup(['script', 'style']): #FIXME - Might need to restructure so that only (p, h1, h2, etc.) is being looked at for word data
        tag.decompose()
    visible_text = soup.get_text(separator=' ', strip=True)
    words = visible_text.split()

    words_without_stopwords = [word.lower() for word in words if word.lower() not in STOPWORDS and word_filter.match(word.lower()) and len(word) > 1]

    for word in words_without_stopwords:
        word_frequencies[word] = word_frequencies.get(word, 0) + 1

    #hash function had some collisions and overwritted the longer pages
    #Checks if it is NOT in or if it is longer than the url it will replace
    if defragged_url not in longest_page or len(words_without_stopwords) > longest_page[defragged_url]: 
        longest_page[defragged_url] = len(words_without_stopwords)

    # save the report json every X crawls
    global crawled_num
    crawled_num += 1
    if crawled_num % SAVE_EVERY_X_PAGES == 0:
        save_report()

def save_report():
    print("SAVING REPORT!")
    report = {
        "unique pages": len(seen_urls),
        "subdomains": dict(sorted(subdomains.items(), key=lambda item: item[1], reverse=True)),
        "word frequencies": sorted(word_frequencies.items(), key=lambda item: item[1], reverse=True)[:50],
        "longest page": sorted(longest_page.items(), key=lambda item: item[1], reverse=True)[:25]
        #max(longest_page.items())
    }
    print("REPORT OBJECT:", report)

    current_time = datetime.now().strftime("%m-%d-%Y %H-%M-%S")
    file_path = "report/report" + str(current_time) + ".json"
    try:
        with open(file_path, "w") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        print("Failed to save report. Error:", e)