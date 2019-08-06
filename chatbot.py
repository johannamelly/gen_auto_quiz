# Author: Johanna Melly
# Chatbot for question generation

# SOURCE DU CODE DE BASE: https://www.mattoncode.pl/dialogflow-python-tutorial-part-1/
from flask import Flask
from flask import request
from flask import make_response
import logging
import json
import random
from http import cookies
import ast
from difflib import SequenceMatcher

# SOURCE MÉTHODE similar(a, b): https://stackoverflow.com/questions/17388213/find-the-similarity-metric-between-two-strings
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

# Usage of session cookie
c = cookies.SimpleCookie()

# Will be useful for question asking
c['questionNumber'] = 0

# Debug purpose
logger = logging.getLogger()
logger.setLevel(logging.INFO)
 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s')
 
app = Flask(__name__)

# Definition of available topics
themeChoice = ["rock music", "the legend of zelda", "switzerland", "politics of the united states", "super mario bros", "world war 2", "olympic games"]

# Mapping between Dialogflow parameter and numeric value
choiceMapping = {
    "one": 1,
    "two": 2,
    "three": 3,

}

# Speech that will be said to the player
correctExpressions = ['Excellent! ', 'Good job! ', 'Exactly! ', 'Your answer is correct! ', 'Yes, you\'re right! ']

incorrectExpressions = ['Nope! ', 'No, sorry! ', 'Sorry, that\'s not correct! ', 'Sorry, your answer is wrong! ']

idontknowExpressions = ['Okay! ', 'No problem. ', 'I\'ll tell you. ', 'Don\'t worry. ', 'That\'s okay']

questions = {}


# Method that catches Dialogflow's requests
@app.route('/', methods=['POST'])
def webhook():
    # Getting Dialogflow request
    req = request.get_json(silent=True, force=True)
    
    # Extract intent
    intent = get_intent_from_req(req)

    # If first intent - chatbot proposes 3 random themes
    if intent == 'Default Welcome Intent':
        # Chooses themes at random
        randomThemes = random.sample(themeChoice, 3)
        # Save in cookie
        c["themes"] = randomThemes
        # Speaks to user
        response = {
                'fulfillmentText': "Hello! I am going to quiz you about a topic. Please choose one of these! One: " + randomThemes[0] + ", two: " + randomThemes[1] + ", three: " + randomThemes[2] + ". Please say one, two or three.",
        }

    # If user chose a theme
    elif intent == 'choose-theme':
        # Getting choice as string
        userAnswer = req['queryResult']['parameters']['choice']
        # Formating chosen theme as filename
        chosenTheme = "./questions/" + ast.literal_eval(c["themes"].value)[choiceMapping[userAnswer]-1].replace(" ", "_") + ".json"
        # Open corresponding file
        with open(chosenTheme) as jsonFile:
             # Getting questions
             tmp = json.load(jsonFile)['questions']
             # Shuffling
             random.shuffle(tmp)
             # Saving in cookie
             c["questions"] = tmp
        # Getting current question index (should be 0)
        qNum = int(c["questionNumber"].value)
        # Asking first question
        response = {
            'fulfillmentText': "Alright, I am going to quiz you about " + ast.literal_eval(c["themes"].value)[choiceMapping[userAnswer]-1] + "! Now let's get started! First question: " + ast.literal_eval(c["questions"].value)[qNum]['question'] + '?',
        }
    # If user gave an answer
    elif intent == 'choose-theme - answer':
        # Answer to low case
        userAnswer = req['queryResult']['parameters']['answer'].lower()
        # Getting current question index
        qNum = int(c["questionNumber"].value)
        # Getting list of answers to current question
        answers = ast.literal_eval(c["questions"].value)[qNum]['answers']
        # If user answer is in one of the correct answers OR if string similarity between answers is more than 60%
        if any (userAnswer in answer for answer in answers) or sorted([similar(answer, userAnswer) for answer in answers])[-1]>0.6:
            # User did good + new questions
            response = {
                'fulfillmentText': random.choice(correctExpressions) + " Next question: " + ast.literal_eval(c["questions"].value)[qNum+1]['question'] + '?',
            }
        else:
            # User failed + new question
            text = "One of the possible answers was: " + random.choice(answers) if  len(answers) > 1 else "The answer was " + answers[0]
            response = {
                'fulfillmentText': random.choice(incorrectExpressions) + text + ". Next question: " + ast.literal_eval(c["questions"].value)[qNum+1]['question'] + '?',
            }
        # Question index is incremented
        c["questionNumber"] = qNum + 1
    # If user doesn't know the answer or want to switch
    elif intent == 'i-dont-know':
        # Getting current question index
        qNum = int(c["questionNumber"].value)
        # Getting list of correct answers
        answers = ast.literal_eval(c["questions"].value)[qNum]['answers']
        # Giving user answer to question + ask new question
        text = "One of the possible answers was: " + random.choice(answers) if  len(answers) > 1 else "The answer was " + answers[0]
        response = {
            'fulfillmentText': random.choice(idontknowExpressions) + text + ". Next question: " + ast.literal_eval(c["questions"].value)[qNum+1]['question'] + '?',
        }
        c["questionNumber"] = qNum + 1
    else:
        response = {
            'fulfillmentText': 'Sorry, something went wrong...',
        }
 
    # Create response for dialogflow
    res = create_response(response)
 
    return res
 
 
def get_intent_from_req(req):
    """ Get intent name from dialogflow request"""
    try:
        intent_name = req['queryResult']['intent']['displayName']
    except KeyError:
        return None
 
    return intent_name
 
 
def create_response(response):
    """ Creates a JSON with provided response parameters """
    
    # convert dictionary with our response to a JSON string
    res = json.dumps(response, indent=4)
 
    logger.info(res)
 
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
 
    return r

 
if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0', threaded=True)
