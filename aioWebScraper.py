__author__ = 'isox'

# Asyncio web scraper for parallel web download
#
# Usage:
#
# downloadedData = getBulkUrl(['url1', 'url2', 'url3'])
#
# It will return key:val dict with {'url1':url1data, 'url2':url2data}
#
# Cloudflare bypass by "aiocfscrape"
# Progressbar made with TQDM
#
# isox@vulners.com

import asyncio
import aiohttp
import tqdm
from aiocfscrape import CloudflareScraper

@asyncio.coroutine
def get(session, url, timeout, rawResult, maxRetry = 5):
    currentTry = 1
    while(currentTry < maxRetry):
        try:
            response = yield from session.get(url.strip(), timeout = timeout)
            if rawResult:
                result = {url:(yield from response.read())}
            else:
                result = {url:(yield from response.text())}
            response.release()
            return result
        except Exception as e:
            currentTry += 1
            if currentTry > maxRetry:
                raise e

@asyncio.coroutine
def wait_with_progress(urlList, concurency = 30, timeout = 120, rawResults = False, cloudflare = False, headers = None):
    sem = asyncio.Semaphore(concurency)
    # Client session worker
    headers = headers or {}
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.104 Safari/537.36 vulners.com/bot'})
    if cloudflare:
        sessionClient = CloudflareScraper
    else:
        sessionClient = aiohttp.ClientSession
    urlToResultDict = {}
    with sessionClient(connector=aiohttp.TCPConnector(verify_ssl=False), headers=headers) as session:
        coros = [parseUrl(url = d, semaphore = sem, session = session, timeout = timeout, rawResults=rawResults) for d in urlList]
        for f in tqdm.tqdm(asyncio.as_completed(coros), total=len(coros)):
            result = yield from f
            urlToResultDict.update(result)
    return urlToResultDict

@asyncio.coroutine
def parseUrl(url, semaphore, session, timeout, rawResults):
    with (yield from semaphore):
        page = yield from get(session, url, timeout, rawResults)
    return page

def getBulkUrl(urlList, concurency = 30, timeout = 120, rawResults = False, cloudflare = False, headers = None):
    loop = asyncio.get_event_loop()
    # Gather URLs
    runner = wait_with_progress(urlList, concurency, timeout, rawResults, cloudflare, headers)
    result =  loop.run_until_complete(runner)
    return result

