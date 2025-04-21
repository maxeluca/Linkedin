import streamlit as st
from openai import OpenAI
import zipfile
import os
import requests
import time
from datetime import datetime
from deep_translator import GoogleTranslator

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🇳🇱 LinkedIn Post Generator")

st.header("Stap 1: Invoer van onderwerp en ruwe input")
with st.form("content_form"):
    onderwerp = st.text_input("Onderwerp of thema van je LinkedIn-post")
    ruwe_inhoud = st.text_area("Ruwe input (zoals aantekeningen of observaties)")
    ingediend = st.form_submit_button("Genereer voorstellen")

def genereer_drie_posts(inhoud):
    prompt = f"""Je bent een professionele tekstschrijver gespecialiseerd in LinkedIn. Schrijf 3 verschillende concepten voor een LinkedIn-post in het Nederlands op basis van de volgende input. 
Elke post moet de volgende structuur hebben:
- Een kopregel in de vorm van een vraag of dilemma
- Een verbindende tekst van 2-3 zinnen
- Een hoofdtekst met meerdere perspectieven én persoonlijke reflectie
- Een afsluitende open vraag aan de lezer
Input:
{inhoud}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1800,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def genereer_variaties(prompt_tekst):
    prompt_en = GoogleTranslator(source='auto', target='en').translate(prompt_tekst)
    stijlen = {
        "Zakelijk": f"A professional clean image that represents: {prompt_en}. Avoid all text or numbers.",
        "Humoristisch & Creatief": f"A fun, imaginative, colorful visual metaphor that illustrates: {prompt_en}. No letters or digits."
    }
    resultaten = []
    for label, prompt in stijlen.items():
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            resultaten.append((label, response.data[0].url))
            time.sleep(15)
        except:
            resultaten.append((label, None))
    return resultaten

def extract_schone_posttekst(tekst):
    regels = [r.strip() for r in tekst.strip().split("\n") if r.strip()]
    schone_regels = []
    for regel in regels:
        if regel.lower().startswith(("kopregel:", "verbindende tekst:", "hoofdtekst:", "concept")):
            inhoud = regel.split(":", 1)[-1].strip()
            schone_regels.append(inhoud)
        else:
            schone_regels.append(regel)
    return "\n".join(schone_regels)

def alleen_tekst_zip(posttekst):
    tekstpad = "/tmp/post.txt"
    with open(tekstpad, "w") as f:
        f.write(extract_schone_posttekst(posttekst))
    zippad = "/tmp/post_only.zip"
    with zipfile.ZipFile(zippad, "w") as zipf:
        zipf.write(tekstpad, arcname="post.txt")
    return zippad

if ingediend and onderwerp and ruwe_inhoud:
    gegenereerd = genereer_drie_posts(ruwe_inhoud)
    voorstellen = [p.strip() for p in gegenereerd.split("\n\n") if len(p.strip()) > 50]
    st.session_state["voorstellen"] = voorstellen

if "voorstellen" in st.session_state:
    st.subheader("Stap 2: Kies je favoriete voorstel")
    gekozen = st.radio("Selecteer één van de gegenereerde voorstellen:", st.session_state["voorstellen"])
    st.session_state["gekozen_post"] = gekozen

if "gekozen_post" in st.session_state:
    st.subheader("Stap 3: Wil je de tekst bewerken?")
    wil_bewerken = st.radio("Wil je deze tekst nog aanpassen?", ["Ja", "Nee"])
    aangepaste_post = st.text_area("Bewerk je tekst hieronder:", value=st.session_state["gekozen_post"], height=300) if wil_bewerken == "Ja" else st.session_state["gekozen_post"]
    st.session_state["definitieve_post"] = aangepaste_post

    st.subheader("Stap 4: Kies om een eigen afbeelding toe te voegen of dat AI twee opties genereert.")
    keuze_afbeelding = st.radio("Afbeeldingskeuze", ["Ik gebruik mijn eigen afbeelding (sla deze stap over)", "Laat AI een afbeelding genereren"])

    afbeelding_url = None
    if keuze_afbeelding == "Laat AI een afbeelding genereren":
        if "afbeeldingen" not in st.session_state:
            with st.spinner("Afbeeldingen worden gegenereerd..."):
                st.session_state["afbeeldingen"] = genereer_variaties(onderwerp)
        geldige = [(label, url) for label, url in st.session_state["afbeeldingen"] if url]
        if geldige:
            gekozen = st.radio("Kies een afbeelding:", [label for label, _ in geldige])
            afbeelding_url = next(url for label, url in geldige if label == gekozen)
            st.image(afbeelding_url, caption=f"Gekozen afbeelding: {gekozen}", use_column_width=True)
            # Download afbeelding
            img_data = requests.get(afbeelding_url).content
            with open("/tmp/afbeelding.png", "wb") as f:
                f.write(img_data)
            tekstpad = "/tmp/post.txt"
            with open(tekstpad, "w") as f:
                f.write(extract_schone_posttekst(aangepaste_post))
            zippad = "/tmp/post_met_afbeelding.zip"
            with zipfile.ZipFile(zippad, "w") as zipf:
                zipf.write(tekstpad, arcname="post.txt")
                zipf.write("/tmp/afbeelding.png", arcname="afbeelding.png")
            with open(zippad, "rb") as f:
                st.download_button("📦 Download ZIP met post + afbeelding", f, file_name="LinkedIn_post.zip")

    if keuze_afbeelding == "Ik gebruik mijn eigen afbeelding (sla deze stap over)":
        zippad = alleen_tekst_zip(aangepaste_post)
        with open(zippad, "rb") as f:
            st.download_button("📄 Download ZIP met alleen posttekst", f, file_name="LinkedIn_post.zip")
