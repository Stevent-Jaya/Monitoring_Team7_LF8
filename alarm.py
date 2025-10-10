# alarm.py

# Importiert das datetime-Modul, um aktuelle Zeitstempel zu erstellen.
import datetime
# Importiert das socket-Modul, um den Netzwerknamen (Hostname) der Maschine zu erhalten.
import socket
# Importiert das sys-Modul (wird hier nur zur Vollständigkeit importiert).
import sys
# NEU: HTTP-Client für Mailjet API
import requests

# --- Konfigurationskonstanten ---
# Definiert den Dateinamen für das Protokoll (Log-Datei).
LOG_FILE = "server_monitoring.log"
# Definiert die Ziel-E-Mail-Adresse für Alarme der höchsten Stufe (Hard-Limit).
EMAIL_RECIPIENT = "stiventchristian@gmail.com"

# NEU: Mailjet-Konfiguration (bitte echte Werte einsetzen)
MAILJET_API_KEY = "4bc0c20599d8fee485694ffc2d74fde5"
MAILJET_API_SECRET = "9fe518345cf25e088c4ee789b5bc7c05"
EMAIL_SENDER = "senior.yasso@gmail.com"   # verifizierte Absenderadresse bei Mailjet
SENDER_NAME = "Server Monitor"
MAILJET_ENDPOINT = "https://api.mailjet.com/v3.1/send"

# Definiert eine interne Funktion zum Schreiben von Nachrichten in die Logdatei.
# Sie akzeptiert den Alarmstatus, den aktuellen Wert, das Hardlimit und einen Informationstext.
def _log_message(message: str, current_value: float, hard_limit: float, info_text: str):
    """
    Schreibt eine formatierte Nachricht in die Logdatei und gibt sie auf der Konsole aus.
    """
    # Erstellt den aktuellen Zeitstempel im gewünschten Format (Jahr-Monat-Tag Stunde:Minute:Sekunde).
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Ruft den Hostnamen (Netzwerknamen) der Maschine ab.
    hostname = socket.gethostname()
    
    # Der Text enthält Datum/Uhrzeit, Hostname, Level, Infotext und Wert
    # Formatiert die gesamte Logzeile mithilfe von f-Strings.
    log_entry = (
        f"[{now}] Host: {hostname} | LEVEL: {message} | "
        f"INFO: {info_text} | VALUE: {current_value} | HARD_LIMIT: {hard_limit}"
    )

    # Beginnt einen try-Block, um potenzielle Fehler beim Schreiben der Datei abzufangen.
    try:
        # Öffnet die Logdatei im Anhänge-Modus ("a" für append).
        with open(LOG_FILE, "a") as f:
            # Schreibt den formatierten Eintrag gefolgt von einem Zeilenumbruch.
            f.write(log_entry + "\n")
        # Gibt die Meldung auch auf der Konsole aus.
        print(f"LOGGED: {log_entry}")
    # Fängt den IOError ab (z.B. wenn die Datei nicht erstellt/geschrieben werden kann).
    except IOError as e:
        # Gibt eine Fehlermeldung auf der Konsole aus.
        print(f"ERROR: Konnte Logdatei '{LOG_FILE}' nicht schreiben: {e}")

# Definiert eine interne Funktion zur (jetzt echten) E-Mail-Zustellung über Mailjet.
def _send_email(subject: str, body: str):
    """
    Sendet eine echte E-Mail über die Mailjet HTTP API (v3.1).
    Ersetzt die vorherige Simulation, Signatur bleibt gleich.
    """
    payload = {
        "Messages": [
            {
                "From": {"Email": EMAIL_SENDER, "Name": SENDER_NAME},
                "To": [{"Email": EMAIL_RECIPIENT, "Name": "Alarm Empfänger"}],
                "Subject": subject,
                "TextPart": body
            }
        ]
    }

    print("-" * 50)
    try:
        resp = requests.post(
            MAILJET_ENDPOINT,
            auth=(MAILJET_API_KEY, MAILJET_API_SECRET),
            json=payload,
            timeout=15
        )
        if resp.status_code == 200:
            print(f"HARD-LIMIT ALARM - E-MAIL SENT to {EMAIL_RECIPIENT} via Mailjet")
        else:
            print(f"ERROR: Mailjet antwortete mit Status {resp.status_code}: {resp.text}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
    except requests.RequestException as e:
        print(f"ERROR: Versand über Mailjet fehlgeschlagen: {e}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
    print("-" * 50)

# Definiert die Hauptfunktion zur Überprüfung der Schwellenwerte (zweistufiges Alarmsystem).
def check_limits(current_value: float, soft_limit: float, hard_limit: float, info_text: str):
    """
    Überprüft den aktuellen Wert gegen Soft- und Hardlimits und löst ggf. Alarme aus.
    """
    # Prüft, ob der aktuelle Wert das Hardlimit überschreitet (höchste Alarmstufe).
    if current_value > hard_limit:
        # Hardlimit: E-Mail senden und loggen
        _log_message("HARD_ALARM", current_value, hard_limit, info_text)
        
        # Erstellt den Betreff für die kritische E-Mail.
        subject = f"CRITICAL ALARM: {info_text} exceeded Hard Limit"
        # Erstellt den detaillierten Textkörper (Body) der E-Mail.
        body = (
            f"Machine: {socket.gethostname()}\n"
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Measurement: {info_text}\n"
            f"Current Value: {current_value}\n"
            f"Hard Limit: {hard_limit}"
        )
        # Ruft die Funktion zum Senden der E-Mail (jetzt real) auf.
        _send_email(subject, body)
        return "HARD_ALARM"

    # Prüft, ob der aktuelle Wert das Softlimit überschreitet (zweite Alarmstufe).
    elif current_value > soft_limit:
        _log_message("SOFT_WARNING", current_value, hard_limit, info_text)
        return "SOFT_WARNING"
        
    # Wenn keines der Limits überschritten wurde.
    else:
        print(f"OK: {info_text} (Current: {current_value}) is within limits.")
        return "OK"

# Definiert eine Funktion, die die aktuell eingeloggten Benutzer erfasst und protokolliert.
def log_current_users():
    """
    Erfasst die aktuell eingeloggten Benutzer und loggt diese.
    """
    try:
        import psutil
        users = psutil.users()
        user_list = [f"{u.name}@{u.host} since {datetime.datetime.fromtimestamp(u.started).strftime('%H:%M')}" for u in users]
        user_count = len(users)
        info_text = f"Currently logged in users ({user_count}): {', '.join(user_list)}"
        _log_message("USER_INFO", user_count, 0, info_text)
        return user_count
    except ImportError:
        print("WARNING: psutil is required for user logging.")
        return 0
