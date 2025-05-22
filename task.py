import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import openai
import os
from dotenv import load_dotenv
import json

load_dotenv()
CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

headers = {'Authorization': f'Bearer {CLEARBIT_API_KEY}'}
openai.api_key = OPENAI_API_KEY

def get_clearbit_data(company_name):
    url = f"https://company.clearbit.com/v2/companies/find?name={company_name}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {
                'website': data.get('domain'),
                'industry': data.get('category', {}).get('industry'),
                'company_size': data.get('metrics', {}).get('employees'),
                'hq_location': data.get('location')
            }
    except Exception as e:
        pass
    return None

def scrape_homepage_text(website_url):
    for scheme in ['https://', 'http://']:
        try:
            response = requests.get(f"{scheme}{website_url}", timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = soup.find_all('p')
                text = ' '.join([p.get_text() for p in paragraphs])
                if text.strip():
                    return text
        except:
            continue
    return None

def analyze_with_llm(text):
    prompt = f"""
    Based on the following text about a company, please provide:
    1. A brief summary of what the company does.
    2. The target customer of the company.
    3. A creative AI automation idea to pitch to this company.

    Text: {text}

    Please respond in JSON format with keys: summary, target_customer, automation_idea.
    """
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        result = response.choices[0].text.strip()
        return json.loads(result)
    except Exception as e:
        return None

def run_enrichment(df):
    enriched_data = []
    for company in df['company_name']:
        details = get_clearbit_data(company) or {}
        website = details.get('website')
        if website:
            text = scrape_homepage_text(website)
            llm_result = analyze_with_llm(text) if text else None
        else:
            llm_result = None

        enriched_data.append({
            'company_name': company,
            'website': details.get('website', ''),
            'industry': details.get('industry', ''),
            'summary_from_llm': llm_result.get('summary', '') if llm_result else '',
            'automation_pitch_from_llm': llm_result.get('automation_idea', '') if llm_result else '',
        })

    return pd.DataFrame(enriched_data)

st.title("Lead Enrichment Automation Bot")

uploaded_file = st.file_uploader("Upload CSV with company names", type="csv")

if uploaded_file:
    df = pd.read_csv("companies.csv")
    if st.button("Run Enrichment"):
        enriched_df = run_enrichment(df)
        st.dataframe(enriched_df)
        csv = enriched_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Enriched CSV", csv, "enriched_output.csv")
