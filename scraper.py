import re
from urllib.parse import urlparse, urljoin, urldefrag
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
    print("links found:", links_found)
    return links_found

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        #FIXME - Need to check if links are in the expected domains
        #FIXME - Need to not get stuck in traps
        if parsed.scheme not in set(["http", "https"]):
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
        print ("TypeError for ", parsed)
        raise
