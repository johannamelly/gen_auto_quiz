# Author: Johanna Melly
# Generates n random links that are related to a Wikipedia page

import requests
import random
import time

def generate_links(theme, nbLinks):
    API = "https://en.wikipedia.org/w/api.php"

    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'links',
        'titles': theme,
        'pllimit': 'max',
        'redirects': '1'
    }
    
    links = []

    while(True):
        # Request for page links
        linksRequest = requests.get(API, params=params)
        pageId = list(linksRequest.json()['query']['pages'])[0]
        # If there are no links
        if('links' not in linksRequest.json()['query']['pages'][pageId]):
            # Stop the loop
            break
        # Getting the links of wanted page
        currentLinks = linksRequest.json()['query']['pages'][pageId]['links']
        # Only keeping usable links
        links += [l['title']for l in currentLinks if l['ns'] == 0 and '(' not in l['title']]
        # If more than 500 links, needs an other request
        if('continue' in linksRequest.json()):
            continueID = linksRequest.json()['continue']['plcontinue']
            # New params to get following links
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'links',
                'titles': theme,
                'pllimit': 'max',
                'plcontinue': continueID,
                'redirects': '1'
            }
        else:
            break
    # Shuffle links to get different ones everytime
    random.shuffle(links)
    listOfRelevant = []
    # For each link
    for link in links:
        wikidataParams = {
                'action': 'query',
                'format': 'json',
                'prop': 'pageprops',
                'titles': link,
                'ppprop': 'wikibase_item',
                'redirects': '1'
            }
        # Getting page properties
        pageDetails = requests.get(API, params=wikidataParams, headers = {"User-Agent": "QuestionGeneration/0.0 (johanna.melly@heig-vd.ch)"})
        pageId = list(pageDetails.json()['query']['pages'])[0]
        if('pageprops' in pageDetails.json()['query']['pages'][pageId]):
            # Extract wikidata ID
            wikidataID = pageDetails.json()['query']['pages'][pageId]['pageprops']['wikibase_item']
            # Keeping small IDs (popular pages)
            if len(wikidataID) < 7:
                queryWD = """SELECT DISTINCT ?items
                WHERE
                {
                    VALUES ?items {wd:""" + wikidataID +"""}
                    ?items wikibase:statements ?statementcount .
                    FILTER (?statementcount > 25 ) .
                }
                """
                url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
                time.sleep(3)
                # Request Wikidata page details if page contains more than 25 triples
                data = requests.get(url, params={'query': queryWD, 'format': 'json'})
                data = data.json()
                # If we have a response
                if data['results']['bindings'] != [] :
                    # Saving the Wikidata ID of the page
                    listOfRelevant.append(data['results']['bindings'][0]['items']['value'].split('/')[-1])
                # If we have enough links
                if(len(listOfRelevant) == nbLinks):
                    return(listOfRelevant)
    return (listOfRelevant)
