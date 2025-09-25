# streamlit_job_dashboard.py
import streamlit as st
import pandas as pd
import hashlib
import sqlite3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import altair as alt

# ------------------------------
# KONFIGURATION
# ------------------------------
# Für GitHub/Deployment: am besten über st.secrets oder Umgebungsvariablen setzen
RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", "")
EMAIL_ADDRESS = st.secrets.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD", "")

# ------------------------------
# Datenbank Setup
# ------------------------------
conn = sqlite3.connect("users_jobs.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    keyword TEXT DEFAULT 'Data Scientist',
    location TEXT DEFAULT 'Germany'
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    location TEXT,
    job_type TEXT,
    date TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    job_title TEXT,
    job_location TEXT,
    date TEXT
)
''')
conn.commit()

# ------------------------------
# Hilfsfunktionen
# ------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email, password):
    try:
        c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(email, password):
    c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, hash_password(password)))
    return c.fetchone() is not None

def update_preferences(email, keyword, location):
    c.execute('UPDATE users SET keyword = ?, location = ? WHERE email = ?', (keyword, location, email))
    conn.commit()

def add_job(title, location, job_type="Vollzeit"):
    c.execute('INSERT INTO jobs (title, location, job_type, date) VALUES (?, ?, ?, ?)',
              (title, location, job_type, str(datetime.today().date())))
    conn.commit()

def get_jobs():
    c.execute('SELECT title, location, job_type, date FROM jobs ORDER BY id DESC')
    rows = c.fetchall()
    return pd.DataFrame(rows, columns=['Titel', 'Ort', 'Jobtyp', 'Datum'])

# ------------------------------
# Job-API (JSearch)
# ------------------------------
def scrape_jobs_api(keyword="Data Scientist", location="Germany"):
    url = "https://jsearch.p.rapidapi.com/search"
    querystring = {"query": keyword, "location": location, "num_pages": "1"}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()
    
    jobs = []
    for job in data.get("data", []):
        title = job.get("job_title")
        loc = job.get("job_location")
        job_type = job.get("job_employment_type", "Vollzeit")
        if title and loc:
            jobs.append((title, loc, job_type))
    return jobs

# ------------------------------
# E-Mail-Versand
# ------------------------------
def send_job_email(email, jobs):
    if not jobs:
        return
    jobs_df = pd.DataFrame(jobs, columns=['Titel', 'Ort', 'Jobtyp'])
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email
    msg['Subject'] = 'Neue Jobangebote nach deinen Präferenzen'
    
    body = jobs_df.to_html(index=False)
    msg.attach(MIMEText(body, 'html'))
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())

# ------------------------------
# Tägliches Job-Update
# ------------------------------
def daily_job_update():
    c.execute('SELECT email, keyword, location FROM users')
    users = c.fetchall()
    
    for email, keyword, location in users:
        jobs = scrape_jobs_api(keyword=keyword, location=location)
        for title, loc, job_type in jobs:
            add_job(title, loc, job_type)
        send_job_email(email, jobs)
    print("Jobs aktualisiert & E-Mails verschickt!")

# ------------------------------
# Scheduler starten
# ------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(daily_job_update, 'interval', hours=24)
scheduler.start()

# ------------------------------
# Streamlit App
# ------------------------------
st.title("Job-Finder Deutschland & Schweiz (Dashboard)")

menu = ["Login", "Registrieren", "Jobs anzeigen", "Präferenzen", "Favoriten"]
choice = st.sidebar.selectbox("Menü", menu)

if choice == "Registrieren":
    st.subheader("Benutzerregistrierung")
    email = st.text_input("E-Mail")
    password = st.text_input("Passwort", type='password')
    if st.button("Registrieren"):
        if register_user(email, password):
            st.success("Benutzer erfolgreich registriert!")
        else:
            st.error("E-Mail existiert bereits!")

elif choice == "Login":
    st.subheader("Login")
    email = st.text_input("E-Mail")
    password = st.text_input("Passwort", type='password')
    if st.button("Login"):
        if verify_user(email, password):
            st.success(f"Willkommen, {email}!")
            st.session_state['logged_in'] = True
            st.session_state['email'] = email
        else:
            st.error("E-Mail oder Passwort falsch!")

elif choice == "Präferenzen":
    if st.session_state.get('logged_in', False):
        st.subheader("Job-Präferenzen")
        email = st.session_state.get('email')
        c.execute('SELECT keyword, location FROM users WHERE email = ?', (email,))
        row = c.fetchone()
        current_keyword = row[0] if row else "Data Scientist"
        current_location = row[1] if row else "Germany"
        
        keyword = st.text_input("Keyword", value=current_keyword)
        location = st.text_input("Ort", value=current_location)
        
        if st.button("Speichern"):
            update_preferences(email, keyword, location)
            st.success("Präferenzen gespeichert!")
    else:
        st.warning("Bitte zuerst einloggen!")

elif choice == "Jobs anzeigen":
    if st.session_state.get('logged_in', False):
        st.subheader("Neueste Jobs")
        jobs_df = get_jobs()
        
        # Filter
        job_type = st.selectbox("Jobtyp", ["Alle", "Vollzeit", "Teilzeit", "Praktikum"])
        remote_option = st.checkbox("Nur Remote-Jobs")
        
        filtered_jobs = jobs_df.copy()
        if job_type != "Alle":
            filtered_jobs = filtered_jobs[filtered_jobs['Jobtyp'] == job_type]
        if remote_option:
            filtered_jobs = filtered_jobs[filtered_jobs['Ort'].str.contains("Remote", case=False)]
        
        # Neue Jobs heute
        st.metric("Neue Jobs heute", len(filtered_jobs[filtered_jobs['Datum'] == str(datetime.today().date())]))
        
        # Dashboard Charts
        top_locations = filtered_jobs['Ort'].value_counts().reset_index()
        top_locations.columns = ['Ort', 'Anzahl']
        chart = alt.Chart(top_locations).mark_bar().encode(
            x='Ort',
            y='Anzahl'
        )
        st.altair_chart(chart, use_container_width=True)
        
        # Jobliste mit Favoriten
        for index, row in filtered_jobs.iterrows():
            st.write(f"{row['Titel']} - {row['Ort']} ({row['Jobtyp']})")
            if st.button("Als Favorit speichern", key=index):
                c.execute('INSERT INTO favorites (user_email, job_title, job_location, date) VALUES (?, ?, ?, ?)',
                          (st.session_state['email'], row['Titel'], row['Ort'], row['Datum']))
                conn.commit()
                st.success("Job als Favorit gespeichert!")
    else:
        st.warning("Bitte zuerst einloggen!")

elif choice == "Favoriten":
    if st.session_state.get('logged_in', False):
        st.subheader("Meine Favoriten")
        c.execute('SELECT job_title, job_location, date FROM favorites WHERE user_email = ?', (st.session_state['email'],))
        rows = c.fetchall()
        fav_df = pd.DataFrame(rows, columns=['Titel', 'Ort', 'Datum'])
        st.dataframe(fav_df)
    else:
        st.warning("Bitte zuerst einloggen!")
