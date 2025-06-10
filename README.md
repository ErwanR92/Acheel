Fonctionnalités principales

    Extraction automatique des informations clés :
    Montant total TTC
    Numéro de devis
    Date du sinistre
    Nom de l’assuré

Analyse OCR des devis (fichiers .jpg)
Contrôle de cohérence entre le mail et les documents
Rapport global structuré (format JSON) pour exploitation ou archivage
Synthèse visuelle pour le gestionnaire (voyants de cohérence)

1. Lancer l’application

    bash : streamlit run app.py 

    Dans le terminal au sein du dossier assurance_test_technique_partie_2

    une fenêtre s'ouvre vers l'application web locale.

2. Arrêter l'application

    Ctrl + C dans le terminal avant de fermer l'application web.

2. Charger les documents

    Mail : un fichier .txt contenant le message de l’assuré.
    Devis : un ou plusieurs fichiers .jpg (scans ou photos des devis).

3. Vérification automatique

    Le module extrait et compare :

        Montant du mail vs. montant total TTC du/des devis
        Numéro de devis du mail vs. documents
        Date du sinistre vs. dates trouvées dans les devis

    Un rapport global en JSON est généré et affiché.


