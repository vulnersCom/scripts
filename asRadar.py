__author__ = 'isox'
#
# https://radar.qrator.net
# IP networks extractor utility
# User AS number from https://radar.qrator.net/search?query=qiwi
# As example 5750
# MacBook-Pro:Misc isox$ python3.5 radarQrator.py 57570
#
# Output will be:
# 91.232.230.0/23
#
# vulners.com

import requests
import netaddr
import bs4
try:
    import re2 as re
except:
    import re
from optparse import OptionParser

def getRadarAs(asNumber):
    radarResponse = requests.get("https://radar.qrator.net/api/prefixes/%s?tab_id=current&page=1" % asNumber).json()
    totalPrefixes = int(radarResponse.get('total'))
    initalPageSoup = bs4.BeautifulSoup(radarResponse.get('page'), "html.parser")
    networkRawSet = set()
    for a in initalPageSoup.find_all(text=re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+?$")):
        networkRawSet.add("%s" % a)
    startPage = 1
    while len(networkRawSet) < totalPrefixes:
        radarResponse = requests.get("https://radar.qrator.net/api/prefixes/%s?tab_id=current&page=%s" % (asNumber, startPage)).json()
        pageSoup = bs4.BeautifulSoup(radarResponse.get('page'), "html.parser")
        for a in pageSoup.find_all(text=re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+?$")):
            networkRawSet.add("%s" % a)
        startPage += 1
    # Now minimize this shit
    networkSet = netaddr.IPSet([netaddr.IPNetwork(item) for item in networkRawSet])
    mergedNetworks = netaddr.cidr_merge(networkSet)
    if not mergedNetworks:
        print("Nothing found. Wrong AS number?")
    else:
        print("\n".join(["%s" % network for network in mergedNetworks]))

def main():
    parser = OptionParser(usage="usage: %prog [AS number as int]",
                          version="%prog 1.0")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("Wrong number of arguments. Only one argument as input - AS numbers")
    if not args[0].isdigit():
        parser.error("Wrong AS number. Must be int")
    getRadarAs(args[0])

if __name__ == '__main__':
    main()
