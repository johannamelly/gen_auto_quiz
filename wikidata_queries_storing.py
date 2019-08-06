# Author: Johanna Melly
# Storing SimpleQuestionsWikidata in database

# NOTE: ce code ne va pas compiler, car il utilise une base de données que j'ai créée
# et remplie avec des données SimpleQuestionsWikidata et SimpleDBPediaQA. Il faut mes
# identifiants pour y avoir accès.
# NOTE: ce code fait appel à un fichier de questions issu de SimpleQuestionsWikidata disponible à cette adresse: https://github.com/askplatypus/wikidata-simplequestions

from SPARQLWrapper import SPARQLWrapper, JSON
import json
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import unidecode
import requests
import time

# Connexion to database
load_dotenv(dotenv_path='./.env')
SECRET_KEY = os.getenv("MONGO_SECRET")
client = MongoClient('mongodb+srv://dbAdmin:'+SECRET_KEY+'@cluster0-bvjpk.mongodb.net/test?retryWrites=true')
db = client['QA_sets']
questions = db['questions']

API = "https://www.wikidata.org/w/api.php"

# Open file SimpleQuestionsWikidata file
with open("annotated_wd_data_valid.txt") as file1:
        questionsFile = file1.read()
        
# Tranform subject from Wikidata format to plain text
def normalize(s):
    # To lower
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

triplets = []

splitted = questionsFile.split('\n')
for line in splitted:
    success = True
    triple = line.split('\t')
    # If triple is not backward
    if('R' not in triple[1]):
        # Getting labels corresponding to subject, predicate and object IDs
        subject = requestEntity(triple[0])
        time.sleep(3)
        predicate = requestEntity(triple[1])
        time.sleep(3)
        obj = requestEntity(triple[2])
        time.sleep(3)
        # Getting corresponding question written by user
        wholeQuery = triple[3]
        if(subject is not None and predicate is not None):
            subject = subject.lower()
            # Looking for subject in query
            if(subject in wholeQuery):
                # Replacing with placeholder
                query = wholeQuery.replace(subject, "<placeholder>")
                print(query)
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
        # If previous steps were successful
        if(success):
            # Generation of data
            data = {
                "wholeQuery" : wholeQuery,
                "query" : query,
                "subject" : subject,
                "subjectCode" : triple[0],
                "predicate": predicate,
                "predicateCode": triple[1],
                "object": obj,
                "objectCode": triple[2]
            }
            # Insertion into database
            questions.insert_one(data)
file1.close()
