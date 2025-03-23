import json
import psycopg2
import re
from datetime import datetime

conn = psycopg2.connect(
    dbname="sae",
    user="postgres",
    password="200407",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

with open("enseignement_sup.json", "r", encoding="utf-8") as file:
    data = json.load(file)

with open('formation.json', 'r') as formation_file:
    formation_data = json.load(formation_file)

address_pattern = re.compile(r"(\d+)\s+(.+)")

def extract_dates(description):
    date_pattern = r'\b\d{2}/\d{2}/\d{4}\b'
    matches = re.findall(date_pattern, description)
    print(f"Extracted dates: {matches}")
    return matches

def insert_date(date):
    formatted_date = date.strftime('%Y-%m-%d')
    
    cur.execute("SELECT id_Date FROM Date WHERE date_Date = %s;", (formatted_date,))
    result = cur.fetchone()
    
    if result:
        return result[0]  
    else:
        cur.execute(""" 
            INSERT INTO Date (date_Date) 
            VALUES (%s)
            RETURNING id_Date;
        """, (formatted_date,))
        
        result = cur.fetchone()
        
        if result:
            return result[0]  
        else:
            print(f"Failed to insert date {formatted_date}")
            return None

def link_jpo_with_date(jpo_id, date_id):
    cur.execute(""" 
        SELECT 1 FROM se_tient_le WHERE id_JPO = %s AND id_Date = %s;
    """, (jpo_id, date_id))
    
    if cur.fetchone():
        print(f"JPO {jpo_id} already linked with date {date_id}. Skipping insertion.")
    else:
        cur.execute(""" 
            INSERT INTO se_tient_le (id_JPO, id_Date) 
            VALUES (%s, %s);
        """, (jpo_id, date_id))
        print(f"Linked JPO {jpo_id} with date {date_id}.")

for record in data:
    id_etablissement = record.get("code_uai")

    if not id_etablissement or id_etablissement.strip() == "":
        print(f"Skipping record due to invalid or empty id_Etablissement in {record}")
        continue  

    adresse = record.get("adresse", "")
    match = address_pattern.match(adresse)
    
    if match:
        n_rue_Adresse = int(match.group(1))  
        nom_rue_Adresse = match.group(2)  
    else:
        n_rue_Adresse = None 
        nom_rue_Adresse = adresse 

    geojson_coordinates = record.get("geojson_coordinates", None)  
    if geojson_coordinates:
        longitude = geojson_coordinates[0]  
        latitude = geojson_coordinates[1] 
    else:
        longitude = float(record.get("longitude_x") or 0.0)
        latitude = float(record.get("latitude_y") or 0.0)

    cur.execute("""
        INSERT INTO Etablissement (id_Etablissement, nom_Etablissement, type_Etablissement, statut_Etablissement, contact_id_contact)
        VALUES (%s, %s, %s, %s, NULL)
        ON CONFLICT (id_Etablissement) DO NOTHING;
    """, (
        id_etablissement,
        record.get("nom"),
        record.get("type_detablissement"),
        record.get("statut")
    ))

    cur.execute("""
        INSERT INTO Adresse (code_postal_Adresse, n_rue_Adresse, nom_rue_Adresse, ville_Adresse, longitude_Adresse, latitude_Adresse, geom, id_Etablissement)
        VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s) ON CONFLICT (id_Etablissement, code_postal_Adresse, n_rue_Adresse, nom_rue_Adresse) 
    DO UPDATE 
    SET
        ville_Adresse = EXCLUDED.ville_Adresse,
        longitude_Adresse = EXCLUDED.longitude_Adresse,
        latitude_Adresse = EXCLUDED.latitude_Adresse,
        geom = EXCLUDED.geom;
    """, (
        int(record.get("cp") or 0),
        n_rue_Adresse,
        nom_rue_Adresse,
        record.get("commune"),
        longitude,
        latitude,
        longitude,
        latitude,
        id_etablissement
    ))

    cur.execute("""
    SELECT id_Adresse 
    FROM Adresse 
    WHERE id_Etablissement = %s 
    AND code_postal_Adresse = %s 
    AND n_rue_Adresse = %s 
    AND nom_rue_Adresse = %s;
    """, (
        id_etablissement,
        int(record.get("cp") or 0),
        n_rue_Adresse,
        nom_rue_Adresse
    ))

    result = cur.fetchone()

    if result:
        id_adresse = result[0]  # Fetch the id_Adresse
        print(f"Inserted or updated Adresse with id: {id_adresse}")
    else:
        print(f"No Adresse found for the given parameters. Something went wrong.")

    journees_portes_ouvertes = record.get("journees_portes_ouvertes", "")
    if journees_portes_ouvertes:
        cur.execute("""
            INSERT INTO JPO (description_JPO, id_Etablissement)
            VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """, (
            journees_portes_ouvertes,
            id_etablissement
        ))

    
    cur.execute("""
            SELECT id_JPO FROM JPO WHERE id_Etablissement = %s AND description_JPO = %s;
        """, (id_etablissement, journees_portes_ouvertes))
    jpo_id = cur.fetchone()

    if jpo_id:
        jpo_id = jpo_id[0]
        # Insert into Localisee_a table linking JPO and Adresse
        cur.execute("""
            INSERT INTO Localisee_a (id_JPO, id_Adresse)
            VALUES (%s, %s)
            ON CONFLICT (id_JPO, id_Adresse) DO NOTHING;
        """, (jpo_id, id_adresse))


    telephone = record.get("telephone")
    site_web = record.get("url_et_id_onisep") 

    if telephone or site_web:
        cur.execute("""
            INSERT INTO Contact (num_tel_Etablissement, site_web_Etablissement, etablissement_id_etablissement)
            VALUES (%s, %s, (SELECT id_Etablissement FROM Etablissement WHERE id_Etablissement = %s)) ON CONFLICT (etablissement_id_etablissement) DO NOTHING;
        """, (
            telephone,
            site_web,
            id_etablissement
        ))




cur.execute("SELECT id_JPO, description_JPO FROM JPO")
jpo_records = cur.fetchall()

for jpo_id, description in jpo_records:
    dates = extract_dates(description) 
    if not dates:
        print(f"No dates found for JPO {jpo_id}")
    for date_str in dates:
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
            date_id = insert_date(date_obj)
            if date_id:
                print(f"Inserting date {date_obj} for JPO {jpo_id} with date ID {date_id}")
                link_jpo_with_date(jpo_id, date_id)
            else:
                print(f"Failed to insert date {date_obj} for JPO {jpo_id}")
        except ValueError:
            print(f"Skipping invalid date format: {date_str} for JPO {jpo_id}")


for formation in formation_data:
    titre_formation = formation["formation_for_libelle"]
    niveau_formation = formation["for_niveau_de_sortie"]

    duree_formation = formation["af_duree_cycle_standard"]
    duree_formation = ''.join(filter(str.isdigit, duree_formation))
    if not duree_formation:
        duree_formation = None
    else:
        duree_formation = int(duree_formation)

    modalite_formation = formation["af_modalites_scolarite"]
    page_web_formation = formation["af_page_web"]

    cur.execute("""
        INSERT INTO Formation (titre_Formation, niveau_Formation, duree_Formation, modalite_Formation, page_web_Formation)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id_Formation;
    """, (titre_formation, niveau_formation, duree_formation, modalite_formation, page_web_formation))

    formation_id = cur.fetchone()[0]

    if not formation_id:
        print(f"Failed to insert formation: {titre_formation}")
        continue

    id_etablissement = formation["ens_code_uai"]

    cur.execute("""
        SELECT * FROM Etablissement WHERE id_Etablissement LIKE %s;
    """, (id_etablissement,))
    
    result = cur.fetchone()

    if not result:
        continue

    cur.execute("""
    SELECT 1 FROM Propose WHERE id_Etablissement = %s AND titre_formation = %s;
""", (id_etablissement, titre_formation))
    
    exists = cur.fetchone()

    if not exists:
        cur.execute("""
            INSERT INTO Propose (id_Etablissement, id_Formation, titre_formation)
            VALUES (%s, %s, %s)
            ON CONFLICT (id_Etablissement, titre_formation) DO NOTHING;
        """, (id_etablissement, formation_id, titre_formation))

    cur.execute("""
        UPDATE ETABLISSEMENT SET Hebergement_Etablissement = %s WHERE id_Etablissement LIKE %s
    """, (formation['ens_hebergement'], id_etablissement))


conn.commit()
cur.close()
conn.close()
