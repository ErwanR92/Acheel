import streamlit as st
from google.cloud import vision
import spacy
import re
import numpy as np
import cv2
import io
import json

service_account_info = dict(st.secrets["google_service_account"])
client = vision.ImageAnnotatorClient.from_service_account_info(service_account_info)

# Configuration initiale
st.set_page_config(page_title="Vérification Sinistres", layout="wide")

# Chargement du modèle spaCy français avec cache
@st.cache_resource
def load_spacy_model():
    return spacy.load("fr_core_news_md")

nlp = load_spacy_model()

def extract_numero_devis(text):
    match = re.search(r'devis\s*[n°o]\s*([A-Za-z0-9/-]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Variante : "Devis n° 240800271 du 21/08/2024"
    match = re.search(r'devis\s*[n°o]?\s*([A-Za-z0-9/-]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_email_data(text):
    # Extraction du numéro de devis (ex : "DEVIS N°0027/01/04" ou "Devis No 1234-2024")
    numero_devis = None
    match_numero = re.search(r'devis\s*[n°o]\s*([A-Za-z0-9/\-]+)', text, re.IGNORECASE)
    if match_numero:
        numero_devis = match_numero.group(1).strip()

    # Extraction de la date en toutes lettres (ex: 10 avril 2024)
    date_lettres_match = re.search(
        r'\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})\b',
        text, re.IGNORECASE)
    if date_lettres_match:
        date_sinistre = date_lettres_match.group(1)
    else:
        date_matches = re.findall(r'\b\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}\b', text)
        date_sinistre = date_matches[0] if date_matches else None

    # Extraction du montant
    montant_matches = re.findall(
        r'(\d[\d\s.,]*\d(?:[.,]\d+)?)[\s]*?(?:€|euros?)',
        text, re.IGNORECASE)
    montant_devis = montant_matches[0].replace(' ', '') + '€' if montant_matches else None

    # Extraction du nom de l'assuré avec spaCy
    doc = nlp(text)
    nom_assure = None
    for ent in doc.ents:
        if ent.label_ == "PER":
            nom_assure = ent.text
            break
    if not nom_assure:
        match = re.search(r'Cordialement,.*\n+(.+)', text)
        if match:
            nom_assure = match.group(1).strip()

    return {
        'numero_devis': numero_devis,
        'date_sinistre': date_sinistre,
        'montant_devis': montant_devis,
        'nom_assure': nom_assure
    }

def process_image(content):
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text if response.full_text_annotation.text else ""

def montant_str_to_float(montant_str):
    if montant_str:
        montant_str = montant_str.replace('€', '').replace('euros', '').replace(' ', '').replace(',', '.')
        try:
            return float(montant_str)
        except ValueError:
            return None
    return None

def normalize_date(date_str):
    if date_str:
        return date_str.replace('-', '/').replace('.', '/')
    return date_str

def extract_montant_total_ttc(ocr_text):
    lines = ocr_text.splitlines()
    for i, line in enumerate(lines):
        # Recherche "Total TTC" (avec ou sans deux-points, insensible à la casse)
        if re.search(r'total\s+ttc', line, re.IGNORECASE):
            # Cherche un montant sur la même ligne (avec ou sans €)
            montant_match = re.search(r'([\d\s.,]+)(?:\s*€)?', line)
            if montant_match:
                montant_str = montant_match.group(1).replace(' ', '').replace(',', '.')
                try:
                    montant = float(montant_str)
                    if montant < 1_000_000:
                        return montant
                except ValueError:
                    pass
            # Sinon, regarde la ligne suivante
            if i+1 < len(lines):
                next_line = lines[i+1]
                montant_match = re.search(r'([\d\s.,]+)(?:\s*€)?', next_line)
                if montant_match:
                    montant_str = montant_match.group(1).replace(' ', '').replace(',', '.')
                    try:
                        montant = float(montant_str)
                        if montant < 1_000_000:
                            return montant
                    except ValueError:
                        pass
    return None

# Interface Streamlit
st.title("📋 Module de vérification de cohérence des sinistres")

with st.sidebar:
    st.header("1. Téléchargement des documents")
    uploaded_files = st.file_uploader(
        "Ajoutez le mail (.txt) et les devis (.jpg)",
        type=["txt", "jpg"],
        accept_multiple_files=True
    )

if uploaded_files:
    text_files = [f for f in uploaded_files if f.type == "text/plain"]
    image_files = [f for f in uploaded_files if f.type == "image/jpeg"]

    if len(text_files) != 1 or len(image_files) < 1:
        st.error("Veuillez télécharger exactement 1 fichier .txt et au moins 1 .jpg")
    else:
        # Extraction des infos du mail
        email_text = text_files[0].read().decode("utf-8")
        mail_data = extract_email_data(email_text)

        # Extraction des infos de chaque document
        ocr_results = []
        with st.spinner("Analyse des documents..."):
            for img_file in image_files:
                ocr_text = process_image(img_file.getvalue())
                ocr_results.append({
                    "nom_fichier": img_file.name,
                    "numero_devis": extract_numero_devis(ocr_text),
                    "montant_total_ttc": extract_montant_total_ttc(ocr_text),
                    "dates_trouvees": re.findall(r'\b\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}\b', ocr_text)
                })

        # Récupération des valeurs pour la cohérence
        montant_mail = montant_str_to_float(mail_data['montant_devis'])
        montants_ttc_docs = [doc["montant_total_ttc"] for doc in ocr_results if doc["montant_total_ttc"] is not None]
        numero_devis_mail = mail_data.get("numero_devis")
        numeros_devis_docs = [doc["numero_devis"] for doc in ocr_results if doc["numero_devis"]]
        date_mail = mail_data.get("date_sinistre")
        dates_docs = [date for doc in ocr_results for date in doc["dates_trouvees"]]

        # Vérification de la cohérence
        rapport = {
            "coherence_montant": bool(montant_mail and any(abs(m - montant_mail) < 0.01 for m in montants_ttc_docs)),
            "coherence_date": bool(date_mail and date_mail in dates_docs),
            "mail": mail_data,
            "documents": ocr_results
        }

        # Affichage du rapport global JSON
        st.header("Rapport global (JSON)")
        st.json(rapport)

        # Synthèse visuelle pour le gestionnaire
        st.header("Synthèse pour le gestionnaire")
        if rapport["coherence_montant"]:
            st.success("Montant du mail cohérent avec le(s) document(s).")
        else:
            st.error("Incohérence sur le montant entre mail et document(s).")
        if rapport["coherence_date"]:
            st.success("Date du mail retrouvée dans les documents.")
        else:
            st.warning("Date du mail absente des documents.")

else:
    st.info("ℹ Veuillez télécharger les documents via le panneau latéral")