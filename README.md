# Job-Finder App (Deutschland & Schweiz)

## Beschreibung
Eine personalisierte Job-Finder-App mit Streamlit:
- Registrierung & Login
- Job-Präferenzen (Keyword + Ort)
- Tägliche Job-Aktualisierung über JSearch API
- E-Mail-Versand nur für relevante Jobs
- Dashboard mit Filter, Top-Orte & Favoriten-Funktion

## Installation
1. Python 3.10+ installieren
2. Virtuelle Umgebung erstellen:
python3 -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

markdown
Code kopieren
3. Abhängigkeiten installieren:
pip install -r requirements.txt

shell
Code kopieren

## App starten
streamlit run streamlit_job_dashboard.py

markdown
Code kopieren

## Konfiguration
- API & E-Mail Zugang über `st.secrets` oder Umgebungsvariablen:
RAPIDAPI_KEY=DEIN_RAPIDAPI_KEY
EMAIL_ADDRESS=dein.email@gmail.com
EMAIL_PASSWORD=DEIN_APP_PASSWORT

markdown
Code kopieren

## Deployment
- Streamlit Cloud: Repository verbinden, Secrets setzen, App starten.
- VPS / Server: Streamlit starten oder Docker verwenden.
