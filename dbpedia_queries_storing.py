# Author: Johanna Melly
# Storing SimpleDBPediaQA questions in Wikidata format in database

# NOTE: ce code ne va pas compiler, car il utilise une base de données que j'ai créée
# et remplie avec des données SimpleQuestionsWikidata et SimpleDBPediaQA. Il faut mes
# identifiants pour y avoir accès.
# NOTE: ce code fait appel à un fichier de questions issu de SimpleDBPediaQA disponible à cette adresse: https://github.com/castorini/SimpleDBpediaQA

from SPARQLWrapper import SPARQLWrapper, JSON
import json
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import unidecode
import re
import requests
import time

# Connexion to database
load_dotenv(dotenv_path='./.env')
SECRET_KEY = os.getenv("MONGO_SECRET")
client = MongoClient('mongodb+srv://dbAdmin:'+SECRET_KEY+'@cluster0-bvjpk.mongodb.net/test?retryWrites=true')
db = client['QA_sets']
questions = db['questions']

API = "https://www.wikidata.org/w/api.php"

with open("train.json") as file1:
        jsonFile = json.load(file1)
        
with open("mapping.json") as file2:
        predList = json.load(file2)

# Tranform subject from Wikidata format to plain text        
def normalize(s):
    s = s.lower()
    s = s.replace('_', ' ')
    if('(' in s):
        s = s[:s.find('(')-1]
    if(',' in s):
        s = s[:s.find(',')]
    return s

# Correction of string to make it similar to user writing
def correct(s):
    s = s.replace('-', ' ')
    s = s.replace("'", '')
    # Unicode formatting removes accents
    s = unidecode.unidecode(s)
    return s

def getIdFromName(name):
    params = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': 'en',
        'search': name
    }

    r = requests.get(API, params=params)
    if "error" not in r.json() and r.json()['search']:
        return r.json()['search'][0]['id']

# Returns Wikidata page name from Wikidata ID
def requestEntity(e):
    params = {
    'action': 'wbgetentities',
    'format': 'json',
    'language': 'en',
    'ids': e
    }
    r = requests.get(API, params=params)
    if( "error" not in r.json() and "missing" not in r.json()["entities"][e] and "en" in r.json()["entities"][e]["labels"]):
        return(r.json()["entities"][e]["labels"]["en"]["value"])

for entry in(jsonFile["Questions"]):
    success = True
    # If question is not backward
    if entry["PredicateList"][0]["Direction"]!="backward":
        # If we can map DBPedia predicate with Wikidata predicate
        if entry["PredicateList"][0]["Predicate"].split('/')[-1] in predList:
            # Getting Wikidata predicate ID corresponding to DBPedia ID
            predicateCode = predList[entry["PredicateList"][0]["Predicate"].split('/')[-1]]
            # Getting Wikidata predicate name
            predicate = requestEntity(predicateCode)
            time.sleep(3);
            wholeQuery = entry["Query"]
            # If question is not already in database
            if (questions.find_one({'wholeQuery': wholeQuery})is None):
                # Extracting subjet
                wholeSubject = entry["Subject"].split('/')[-1]
                subject = normalize(wholeSubject)
                # Getting Wikidata ID from page name
                subjectCode = getIdFromName(subject)
                time.sleep(3)
                # If subject is in user query
                if(subject in wholeQuery):
                    # Replacing with placeholder
                    query = wholeQuery.replace(subject, "<placeholder>")
                else:
                    # Formatting subject to reproduce user possible mistakes
                    subject = correct(subject)
                    # If formatted subject is found in query
                    if(subject in wholeQuery):
                        # Replacing with placeholder
                        query = wholeQuery.replace(subject, "<placeholder>")
                    else:
                        success = False
            else:
                success = False
        else:
            success = False

        if(success):
            # Generation of data
            data = {
                    "wholeQuery" : wholeQuery,
                    "query" : query,
                    "subject" : subject,
                    "subjectCode" : subjectCode,
                    "predicate": predicate,
                    "predicateCode": predicateCode
                }
            # Storing in database
            questions.insert_one(data)
file1.close()
file2.close()
