# Author: Johanna Melly
# Generation of questions from a given topic

# NOTE: ce code ne va pas compiler, car il utilise une base de données que j'ai créée
# et remplie avec des données SimpleQuestionsWikidata et SimpleDBPediaQA. Il faut mes
# identifiants pour y avoir accès.
# NOTE: outre l'accès à la base de données, pour pouvoir lancer ce code, il faut télécharger:
# - Le Google Word2Vec trained model: https://github.com/mmihaltz/word2vec-GoogleNews-vectors
# - Zamia-Speech English language model: https://goofy.zamia.org/zamia-speech/lm/

import sys
import gensim.downloader
from gensim.models import KeyedVectors
from SPARQLWrapper import SPARQLWrapper, JSON
import json
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import random
import re
import requests
from itertools import groupby
from collections import defaultdict
from operator import itemgetter
import nltk
import time
import urllib.request
import related_links as relevantLinksGen
import kenlm

w2v_vectors = KeyedVectors.load_word2vec_format( "./data/word2vec-google-news-300.gz", binary=True)

# Loading model
model = kenlm.Model('./data/generic_en_lang_model_large-r20190501.arpa')

# Getting database password
load_dotenv(dotenv_path='./.env')
SECRET_KEY = os.getenv("MONGO_SECRET")
# Database connexion
client = MongoClient('mongodb+srv://dbAdmin:'+SECRET_KEY+'@cluster0-bvjpk.mongodb.net/test?retryWrites=true')
db = client['QA_sets']
questions = db['questions']

# Main topic definition
theme = "politics of the united states"

# Get triples related to a Wikidata page
def getPageTriplets(subject, queryId):
    time.sleep(5)
    tripletslist = []
    # SOURCE QUERY: https://stackoverflow.com/questions/46383784/wikidata-get-all-properties-with-labels-and-values-of-an-item
    query = """
        SELECT ?wdLabel ?ps_Label ?wdpqLabel ?pq_Label ?ps_ {
          VALUES (?entity) {(wd:""" +queryId+ """)}

          ?entity ?p ?statement .
          ?statement ?ps ?ps_ .

          ?wd wikibase:statementProperty ?ps.

          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
        } ORDER BY ?wd ?ps
        """
    
    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    data = requests.get(url, params={'query': query, 'format': 'json'})
    if(data.status_code == 200):
        data = data.json()
        for item in data['results']['bindings']:
            # If object's identifier exists
            if(item['ps_']['type'] == "uri"):
                objCode = item['ps_']['value'].split('/')[-1]
            else:
                objCode = None
            # Storing object predicate
            predicate = item['wdLabel']['value']
            obj = item['ps_Label']['value']
            # Adding information in triplets list
            tripletslist.append((predicate, obj, objCode, subject, queryId))
    return tripletslist

# Gets Wikidata page ID from page name
def getIdFromName(name):
    wikidataIdFromNameparams = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': 'en',
        'search': name
    }

    idFromName = requests.get("https://www.wikidata.org/w/api.php", params=wikidataIdFromNameparams)
    if "error" not in idFromName.json() and idFromName.json()['search']:
        return idFromName.json()['search'][0]['id']
    
# Gets Wikidata page name from ID
def getNameFromId(identifier):
    time.sleep(3)
    paramsNameFromId = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': 'en',
        'search': identifier
    }

    responseName = requests.get("https://www.wikidata.org/w/api.php", params=paramsNameFromId)
    if "error" not in responseName.json() and responseName.json()['search']:
        return responseName.json()['search'][0]['label']
        
# Binds Wikidata page ID with Wikipedia page name
def produceWikipediaRequest(identifier):
    time.sleep(3)
    return """
    SELECT ?sitelink
    WHERE 
    {
      BIND(wd:"""+ identifier + """ AS ?wikipedia)
      ?sitelink schema:about ?wikipedia .
      FILTER REGEX(STR(?sitelink), "en.wikipedia.org/wiki/") .
    }
        """

# Gets Wikidata page content from Wikidata ID
def produceWikidataRequest(identifier):
    return """
    SELECT ?wdLabel ?ps_ ?ps_Label ?wdpqLabel ?pq_Label {
      VALUES (?entity) {(wd:""" +identifier+ """)}

      ?entity ?p ?statement .
      ?statement ?ps ?ps_ .

      ?wd wikibase:statementProperty ?ps.

      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
    }
    """

# Definition of APIs and query services
API = "https://www.wikidata.org/w/api.php"
API_WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
URL_WIKIDATA = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'

params = {
    'action': 'wbsearchentities',
    'format': 'json',
    'language': 'en',
    'search': theme
}

# Getting exact subject's page name and its Wikidata ID
r = requests.get(API, params=params)

xPreds = open("extendedPredicates.txt", "r").read()

subject = r.json()['search'][0]['label']
queryId = r.json()['search'][0]['id']

# Getting Wikipedia article extract from Wikidata ID
def getExtracts(queryId):
    time.sleep(3)
    # Gets Wikipedia page name from Wikidata ID
    wikinameRequest = requests.get(URL_WIKIDATA, params={'query': produceWikipediaRequest(queryId), 'format': 'json'})
    wikinameRequest = wikinameRequest.json()
    
    # If response
    if(wikinameRequest['results']['bindings']):

        # Extraction of Wikipedia page name
        wikiname = wikinameRequest['results']['bindings'][0]['sitelink']['value'].split('/')[-1]
        wikipediaArticleSubjectParams = {
            'action': 'query',
            'format': 'json',
            'prop': 'extracts',
            'exintro': '',
            'explaintext': '',
            'titles': urllib.request.unquote(wikiname)
        }

        responseSubjectWikipedia = requests.get(API_WIKIPEDIA, params=wikipediaArticleSubjectParams)
        
        # Gets matching Wikipedia ID
        pageId = list(responseSubjectWikipedia.json()['query']['pages'])[0]
        if 'extract' in responseSubjectWikipedia.json()['query']['pages'][pageId]:
            # Get subject extract
            extractSubj = responseSubjectWikipedia.json()['query']['pages'][pageId]['extract']
            # Filtered version with word2vec know vocabulary
            filteredExtractSubj = list(filter(lambda x: x in w2v_vectors.vocab, nltk.word_tokenize(extractSubj)))
            if filteredExtractSubj != []:
                return filteredExtractSubj
            else:
                return None
        else:
            return None

# Get sub-topics linked to main topic (other file)
relevantLinks = relevantLinksGen.generate_links(subject, 20)

finalSetOfQuestions = []

# Getting all the triplets concerning this subject
triplets = []
triplets.append(getPageTriplets(subject, queryId))
extendedTriplets = []

for triplet in triplets[0]:
    # Getting triplets with extended predicates (stored in file)
    if(triplet[0] in xPreds):
        extendedTriplets.append(getPageTriplets(triplet[1], triplet[2]))

# Keeping 10 random of these triplets
if(len(extendedTriplets) != 0):
    if len(extendedTriplets) > 10:
        extendedTriplets = random.sample(extendedTriplets, 10)
    triplets.extend(extendedTriplets)

# Getting triplets from relevant sub-topics
for link in relevantLinks:
    triplets.append(getPageTriplets(getNameFromId(link), link))
    

packOfQuestions = []

# Packing triplets by subject and predicate
for triplet in triplets:
    allRes = defaultdict(list)
    for t0, t1, t2, t3, t4 in triplet:
        if(t0 not in ['part of', 'mass', 'instance of', 'headquarters location']):
            allRes[t0].append((t1, t2, t3, t4))
    packOfQuestions.append(allRes)
    

numberOfQuestions = 0
nbquest = 0
nbFail = 0
needsSubjExtract = True

for pack in packOfQuestions:
    needsSubjExtract = True
    # For each triplet
    for t in pack:
        answer = pack[t][0][0]
        answerId = pack[t][0][1]
        currentSubject = pack[t][0][2]
        currentQueryId = pack[t][0][3]
        
        # If new subject, getting extract
        if(needsSubjExtract):
            extractSubj = getExtracts(currentQueryId)
            needsSubjExtract = False

        # Finding list of questions question with current predicate in database
        res = questions.find({"predicate" : t})

        # If there is at least one question
        if(res.count()!=0):
            # Taking 20 random questions
            pop = res.count() if res.count()<20 else 20
            res_sample = random.sample(list(res), pop)
            
            # Getting Wikipedia abstract of object
            if(answerId):
                extractObj = getExtracts(answerId)
            else:
                extractObj = None
            
            scoredQuestions = []
            
            print("<" + currentSubject + "><" + t + "><" + str([listofanswers[0] for listofanswers in pack[t]]) + ">")
            
            # For each of these 20 questions
            for resultat in res_sample:
                # Getting the question with the placeholser
                question = resultat['query']
                # Replacing placeholder with subject
                question = question.replace("<placeholder>", currentSubject)
                # Filtering question to keep only known vocabulary
                filteredQuestion = list(filter(lambda x: x in w2v_vectors.vocab, nltk.word_tokenize(question)))
                # Getting similarity score between Wikipedia extracts and questions
                if(extractObj is not None and extractSubj is not None):
                    sims = w2v_vectors.n_similarity(extractObj, filteredQuestion)
                    simsSubj = w2v_vectors.n_similarity(extractSubj, filteredQuestion)
                    totSim = max(sims,simsSubj)
                elif extractObj is not None:
                    totSim = w2v_vectors.n_similarity(extractObj, filteredQuestion)
                elif extractSubj is not None:
                    totSim = w2v_vectors.n_similarity(extractSubj, filteredQuestion)
                else:
                    totSim = 0
                # Storing question
                scoredQuestions.append((totSim, question, model.score(question)))
            # Sorting questions by score
            scoredQuestions.sort(key=lambda x: x[0]+x[2]/250)
            print(scoredQuestions[-1][1])
            # Keeping best question
            finalSetOfQuestions.append((scoredQuestions[-1][1].replace("?", ""), [x[0].lower() for x in pack[t]]))


# Shuffling questions
random.shuffle(finalSetOfQuestions)

# Formatting questions to get a json object
jsfile = {}
jsfile["questions"] = []
for t in finalSetOfQuestions:
    jsfile["questions"].append({"question" :  t[0], "answers" : t[1]} )

# Storing in file
with open('../chatbot/questions/politics_of_the_united_states.json', 'w') as outfile:
    json.dump(jsfile, outfile)
