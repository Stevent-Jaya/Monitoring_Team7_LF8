# monitoring.py

# Importiert das argparse-Modul zur Verarbeitung von Kommandozeilen-Argumenten.
import argparse
# Importiert das sys-Modul für den Zugriff auf systembezogene Parameter und Funktionen (z.B. Beenden des Skripts).
import sys
# Importiert psutil, die Hauptbibliothek zur Abfrage von Systeminformationen (CPU, Speicher, Prozesse).
import psutil
# Importiert die Kernfunktionen check_limits und log_current_users aus dem lokalen alarm-Modul.
from alarm import check_limits, log_current_users
# Importiert das os-Modul zur Interaktion mit dem Betriebssystem (z.B. Pfadkorrektur für Windows).
import os

# --- Hilfsfunktionen für die Messdatenerfassung (Echtzeit) ---

# Definiert die Funktion zur Ermittlung des prozentualen Plattenplatzverbrauchs.
def get_disk_usage(path='/'):
    """
    Ermittelt den prozentualen Plattenplatzverbrauch eines Dateisystems.
    """
    # Beginnt einen try-Block zur Fehlerbehandlung bei Pfad- oder Zugriffsproblemen.
    try:
        # Korrigiert den Pfad für Windows-Betriebssysteme ('nt' steht für Windows), falls '/' übergeben wird.
        if os.name == 'nt' and path == '/':
             # Setzt den Pfad auf das standardmäßige Windows-Laufwerk C:\\.
             path = 'C:\\'
        
        # Ruft die Datenträgernutzungsstatistik für den angegebenen Pfad mithilfe von psutil ab.
        usage = psutil.disk_usage(path)
        # Gibt den prozentualen Nutzungsanteil des Datenträgers zurück.
        return usage.percent
    # Fängt den Fehler ab, falls der angegebene Dateisystempfad nicht existiert.
    except FileNotFoundError:
        print(f"ERROR: File system path '{path}' not found.")
        # Gibt None zurück, um anzuzeigen, dass der Wert nicht ermittelt werden konnte.
        return None
    # Fängt alle anderen möglichen Ausnahmen während der Plattenprüfung ab.
    except Exception as e:
        print(f"ERROR during disk usage check: {e}")
        # Gibt None zurück.
        return None

# Definiert die Funktion zur Ermittlung der aktuellen Anzahl laufender Prozesse.
def get_process_count():
    """
    Ermittelt die Anzahl der laufenden Prozesse.
    """
    # psutil.pids() gibt eine Liste aller Prozess-IDs zurück. len() zählt diese.
    return len(psutil.pids())

# --- Hauptlogik und Kommandozeilensteuerung ---

# Definiert die zentrale Funktion, die Daten erfasst und die Alarmprüfung auslöst.
def monitor_data(data_type: str, soft_limit: float, hard_limit: float, path: Optional[str] = None):
    """
    Erfasst die Messdaten, ruft das Alarmsystem auf und gibt das Ergebnis zurück.
    """
    # Initialisiert den Informationstext mit dem Datentyp.
    info_text = f"Measurement: {data_type}"
    # Variable für den aktuell gemessenen Wert (wird gleich überschrieben).
    current_value = None
    
    # 1. Messdaten erfassen (Echtzeit)
    # Prüft, ob der Benutzer 'disk_usage' angefordert hat.
    if data_type.lower() == 'disk_usage':
        # pick a concrete path: CLI value if given, else "/"
        selected_path = path if path is not None else '/'
        current_value = get_disk_usage(selected_path)
        info_text = f"Disk Usage (%) on {selected_path}"
    # Prüft, ob der Benutzer 'process_count' angefordert hat.
    elif data_type.lower() == 'process_count':
        # Ruft die Anzahl der Prozesse ab und konvertiert sie in float für die Prüfung.
        current_value = float(get_process_count())
        # Setzt den spezifischen Infotext.
        info_text = "Running Process Count"
    # Prüft, ob der Benutzer 'user_count' angefordert hat (nur Protokollierung, keine Limitprüfung).
    elif data_type.lower() == 'user_count':
        # Benutzer werden separat geloggt
        print("\n--- User Logging (INFO ONLY) ---")
        # Ruft die Funktion zur Protokollierung der Benutzer aus dem alarm-Modul auf.
        log_current_users()
        # Gibt den Status zurück, da keine Limitprüfung erfolgt.
        return "USER_LOGGED"
    # Wenn der übergebene Datentyp unbekannt ist.
    else:
        # Gibt eine Fehlermeldung aus.
        print(f"ERROR: Unknown data type '{data_type}'. Use 'disk_usage', 'process_count' or 'user_count'.")
        # Gibt den Status "ERROR" zurück.
        return "ERROR"
        
    # Prüft, ob bei der Datenerfassung ein Fehler aufgetreten ist (current_value ist None).
    if current_value is None:
        return "ERROR"
        
    # 2. Aktuellen Wert prüfen und Alarmsystem aufrufen
    # Gibt den Start der Limitprüfung auf der Konsole aus.
    print(f"\n--- Checking {info_text} (Current Value: {current_value}) ---")
    # Übergibt den aktuellen Wert und die Limits an die zentrale Prüflogik in alarm.py.
    return check_limits(current_value, soft_limit, hard_limit, info_text)

# Definiert die Hauptfunktion zur Initialisierung und Steuerung des Programms.
def main():
    """
    Steuert das Programm über Kommandozeilen-Parameter.
    """
    # Erstellt einen ArgumentParser mit Beschreibung und Beispiel.
    parser = argparse.ArgumentParser(
        description="Server Monitoring Tool mit zweistufigem Alarmsystem.",
        epilog="Beispiel: python monitoring.py disk_usage -s 80.0 -hl 95.0 -p /"
    )
    
    # Definiert das obligatorische positionelle Argument für den zu prüfenden Datentyp.
    parser.add_argument(
        "data_type",
        # Schränkt die gültigen Eingabewerte ein.
        choices=['disk_usage', 'process_count', 'user_count'],
        help="Art der zu prüfenden Messdaten (disk_usage, process_count, user_count)."
    )
    
    # Definiert das optionale Argument für das Soft-Limit (-s).
    parser.add_argument(
        "-s", "--soft-limit",
        type=float,
        default=80.0,
        help="Schwellenwert für Soft-Limit (z.B. 80.0 für 80%%)."
    )
    # Definiert das optionale Argument für das Hard-Limit (-hl).
    parser.add_argument(
        "-hl", "--hard-limit",
        type=float,
        default=95.0,
        help="Schwellenwert für Hard-Limit (z.B. 95.0 für 95%%)."
    )
    # Definiert das optionale Argument für den Pfad zur Plattenprüfung (-p).
    parser.add_argument(
        "-p", "--path",
        type=str,
        default='/',
        help="Pfad für die Überprüfung der Plattennutzung (z.B. C:\\ oder /var)."
    )

    # Parst die übergebenen Kommandozeilen-Argumente.
    args = parser.parse_args()

    # Überprüfung der Messdaten
    # Ruft die Funktion zur Überwachung mit den vom Benutzer übergebenen/Standard-Parametern auf.
    monitor_data(
        args.data_type, 
        args.soft_limit, 
        args.hard_limit, 
        args.path
    )

# Stellt sicher, dass der Code nur ausgeführt wird, wenn das Skript direkt gestartet wird.
if __name__ == "__main__":
    # Prüft vor dem Start, ob das essenzielle psutil-Modul installiert ist.
    try:
        import psutil
    # Fängt den Fehler ab, wenn psutil nicht gefunden wird.
    except ImportError:
        # Informiert den Benutzer über die fehlende Abhängigkeit.
        print("ERROR: Das Modul 'psutil' ist nicht installiert. Bitte installieren Sie es mit 'pip install psutil'.")
        # Beendet das Skript mit einem Fehlercode.
        sys.exit(1)
        
    # Startet die Hauptfunktion des Programms.
    main()
