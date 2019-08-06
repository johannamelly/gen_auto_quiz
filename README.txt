Ce dossier contient les fichiers principaux produits dans le cadre du travail de Bachelor « Génération automatique de quiz pour chatbot ».

Liste des dossiers/fichiers et description:
- questions: contient des fichiers de questions générés pour le chatbot
- chatbot.py: contient le code du chatbot pour l'enceinte Google Home
- question_generation: contient le code final pour la génération de questions
- extendedPredicates: contient la liste des prédicats dits « étendus »
- related_links: contient le code final permettant de générer des liens relatifs à une page Wikipédia
- mapping.json: contient une liste de prédicats DBPedia et leurs ID Wikidata correspondants
- wikidata_queries_storing.py: contient le code pour le stockage en base de données des questions extraites de SimpleQuestionsWikidata. Ce fichier a été utilisé avant d'effectuer la génération de questions elle-même, afin de populer la base de données nécessaire.
- dbpedia_queries_storing.py: contient le code pour la transformation des prédicats et le stockage en base de données des questions de SimpleDBPediaQA. Ce fichier a été utilisé avant d'effectuer la génération de questions elle-même, afin de populer la base de données nécessaire.
