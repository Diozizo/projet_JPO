from datetime import datetime, timedelta
import psycopg2
from psycopg2 import sql
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# API key for geocoding
GEOCODE_API_KEY = 'your_api_key'

def geocode_address(address):
    """Get latitude and longitude from an address using OpenCage API."""
    url = f'https://api.opencagedata.com/geocode/v1/json?q={address}&key={GEOCODE_API_KEY}&language=fr&pretty=1'
    response = requests.get(url)
    data = response.json()

    if data['results']:
        lat = data['results'][0]['geometry']['lat']
        lon = data['results'][0]['geometry']['lng']
        return lat, lon
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

def get_db_connection():
    """Establish and return a database connection."""
    return psycopg2.connect(
        dbname="sae",
        user="postgres",
        password="200407",
        host="localhost",
        port="5432"
    )

@app.route('/search_jpo', methods=['POST'])
def search_jpo():
    data = request.get_json()

    address = data.get('address')
    radius = int(data.get('radius', 5000))  
    days_range = data.get('date_range') 
    custom_date = data.get('custom_date') 
    statut = data.get('statuts')
    types = data.get('types')
    hebergement = data.get('hebergements')
    sortOption = data.get('sortOption')
    longitude = data.get('longitude')
    latitude = data.get('latitude')

    allowedSortOptions = ['nom_etablissement', 'ville_adresse', 'code_postal_adresse', '']

    if sortOption not in allowedSortOptions:
        sortOption = None

    print(f"Received data: address={address}, radius={radius}, days_range={days_range}, custom_date={custom_date}, statut={statut}, types={types}, hebergement={hebergement}, sortOption={sortOption}")

    if longitude and latitude:
        lat = latitude
        lon = longitude
    else:
        lat, lon = geocode_address(address)
        
    if lat is None or lon is None:
        return jsonify({"error": "Invalid address"}), 400

    print(f"Geocoded address {address} to lat: {lat}, lon: {lon}")

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
    SELECT 
            j.id_JPO, 
            j.description_JPO, 
            e.id_Etablissement,
            e.nom_Etablissement, 
            a.ville_Adresse, 
            a.nom_rue_Adresse, 
            a.latitude_Adresse, 
            a.longitude_Adresse,
            d.date_Date
    FROM 
            JPO j
    JOIN 
            Etablissement e ON j.id_Etablissement = e.id_Etablissement
    JOIN 
            Adresse a ON e.id_Etablissement = a.id_Etablissement
    LEFT JOIN
            se_tient_le s ON j.id_JPO = s.id_JPO
    LEFT JOIN
            Date d ON s.id_Date = d.id_Date
    WHERE 
            ST_DWithin(a.geom, ST_SetSRID(ST_Point(%s, %s), 4326), %s)
    """
    
    params = [lon, lat, radius]

    if days_range:
        end_date = datetime.now() + timedelta(days=int(days_range))
        query += " AND d.date_Date BETWEEN %s AND %s"
        params.extend([datetime.now().date(), end_date.date()])
    elif custom_date:
        query += " AND d.date_Date BETWEEN %s AND %s"
        params.extend([datetime.now().date(), custom_date])
    
    print(f"{datetime.now().date()} +', ' + {custom_date} + ', ' + {str(days_range)}")
    if hebergement:
        query += " AND e.Hebergement_Etablissement ~* %s"
        params.append(r'\minternat\M')
    # Add filters
    filter_conditions = {
        'type_Etablissement': types,
        'statut_Etablissement': statut,
    }

    for column, values in filter_conditions.items():
        if values:
            query += f" AND e.{column} IN %s"
            params.append(tuple(values))
    

    if sortOption:
        query += f" ORDER BY {sortOption}"

    print(query)
    cur.execute(query, params)
    jpos = cur.fetchall()

    print(f"Query results: {jpos}")

    grouped_results = {}
    for jpo in jpos:
        etab_id = jpo[2]
        if etab_id not in grouped_results:
            grouped_results[etab_id] = {
                'id_JPO': jpo[0],
                'description_JPO': jpo[1],
                'id_Etablissement': etab_id,
                'nom_Etablissement': jpo[3],
                'ville_Adresse': jpo[4],
                'nom_rue_Adresse': jpo[5],
                'latitude_Adresse': jpo[6],
                'longitude_Adresse': jpo[7],
                'dates': set()
            }
        if jpo[8]:
            grouped_results[etab_id]['dates'].add(jpo[8])

    results = []
    for etab in grouped_results.values():
        etab['dates'] = sorted(etab['dates'])
        results.append(etab)

    days_range = None
    custom_date = None
    cur.close()
    conn.close()

    return jsonify(results)

@app.route('/autocomplete')
def autocomplete():
    query = request.args.get("query", "").strip()

    if not query:
        return jsonify([])

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ville_Adresse, code_postal_adresse
        FROM Adresse
        WHERE LOWER(ville_Adresse) LIKE LOWER(%s) 
        OR CAST(code_postal_adresse AS TEXT) LIKE %s
        LIMIT 10
    """, (f"%{query}%", f"%{query}%"))

    results = [{"ville": row[0], "code_postal": row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return jsonify(results)

@app.route('/etablissement/<id_Etablissement>', methods=['GET'])
def show_etablissement(id_Etablissement):
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            e.nom_Etablissement, 
            e.type_Etablissement, 
            e.statut_Etablissement, 
            e.Est_Internat, 
            e.Hebergement_Etablissement,
            a.nom_rue_Adresse, a.n_rue_Adresse, a.ville_Adresse, a.code_postal_Adresse,
            c.num_tel_Etablissement, c.site_web_Etablissement,
            j.description_JPO,
            f.id_formation, f.titre_Formation, f.niveau_Formation, f.duree_Formation, f.duree_du_stage_Formation, 
            f.possibilite_alternance_Formation, f.modalite_Formation, f.page_web_Formation,
            m.nom_mention, m.description_Mention
        FROM Etablissement e
        LEFT JOIN Adresse a ON e.id_Etablissement = a.id_Etablissement
        LEFT JOIN Contact c ON e.id_Etablissement = c.etablissement_id_etablissement
        LEFT JOIN JPO j ON e.id_Etablissement = j.id_Etablissement
        LEFT JOIN Propose p ON e.id_Etablissement = p.id_Etablissement
        LEFT JOIN Formation f ON p.id_Formation = f.id_Formation
        LEFT JOIN Categorise ca ON f.id_Formation = ca.id_Formation
        LEFT JOIN Mention m ON ca.id_mention = m.id_mention
        WHERE e.id_Etablissement = %s ORDER BY f.duree_Formation DESC;
    """

    cur.execute(query, (id_Etablissement,))
    establishment = cur.fetchall()

    if not establishment:
        return "Établissement non trouvé", 404

    establishment_info = {
        "nom_Etablissement": establishment[0][0],
        "type_Etablissement": establishment[0][1],
        "statut_Etablissement": establishment[0][2],
        "Est_Internat": "Oui" if establishment[0][3] else "Non",
        "Hebergement_Etablissement": establishment[0][4],
        "adresse_complete": f"{establishment[0][6]} {establishment[0][5]}, {establishment[0][7]}, {establishment[0][8]}",
        "num_tel_Etablissement": establishment[0][9],
        "site_web_Etablissement": establishment[0][10],
        "description_JPO": establishment[0][11],
        "code_uai": id_Etablissement,
        "formations": []
    }

    MAX_MODALITE_LENGTH = 50

    encountered_titles = set()

    for row in establishment:
        titre_formation = row[13] 
        if titre_formation not in encountered_titles:
            encountered_titles.add(titre_formation)

            modalite_formation = row[18]

            if modalite_formation and len(modalite_formation) > MAX_MODALITE_LENGTH:
                modalite_formation = modalite_formation[:MAX_MODALITE_LENGTH] + "..."

            establishment_info["formations"].append({
                "id_Formation": row[12],
                "titre_Formation": titre_formation,
                "niveau_Formation": row[14],
                "duree_Formation": row[15],
                "duree_du_stage_Formation": row[16],
                "possibilite_alternance_Formation": row[17],
                "modalite_Formation": modalite_formation,
                "page_web_Formation": row[19],
                "mention": {
                    "nom_mention": row[20],
                    "description_Mention": row[21]
                }
            })

    cur.close()
    conn.close()

    return render_template("etablissement_detail.html", etablissement=establishment_info)

@app.route('/formation_details/<formation_id>')
def formation_details(formation_id):

    if not formation_id:
        return "Formation not found", 404

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            f.titre_Formation, 
            f.niveau_Formation, 
            f.duree_Formation, 
            f.duree_du_stage_Formation,
            f.possibilite_alternance_Formation, 
            f.modalite_Formation, 
            f.page_web_Formation,
            m.nom_mention, 
            m.description_Mention,
            e.nom_Etablissement
        FROM Formation f
        LEFT JOIN Categorise c ON f.id_Formation = c.id_Formation
        LEFT JOIN Mention m ON c.id_mention = m.id_mention
        LEFT JOIN Propose p ON f.id_Formation = p.id_Formation
        LEFT JOIN etablissement e on e.id_Etablissement = p.id_Etablissement
        WHERE f.id_Formation = %s;
    """

    cur.execute(query, (formation_id,))
    formation = cur.fetchone()

    if not formation:
        return "Formation not found", 404

    formation_info = {
        "titre_Formation": formation[0],
        "niveau_Formation": formation[1],
        "duree_Formation": formation[2],
        "duree_du_stage_Formation": formation[3],
        "possibilite_alternance_Formation": formation[4],
        "modalite_Formation": formation[5],
        "page_web_Formation": formation[6],
        "mention": {
            "nom_mention": formation[7],
            "description_Mention": formation[8]
        },
        "nom_etablissement": formation[9]
    }

    cur.close()
    conn.close()

    return render_template('formation_details.html', formation=formation_info)

@app.route('/api/filters/types')
def get_type_filters():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT type_Etablissement FROM Etablissement WHERE type_Etablissement IS NOT NULL")
    return jsonify([row[0] for row in cur.fetchall()])

@app.route('/api/filters/hebergements')
def get_hebergement_filters():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT Hebergement_Etablissement FROM Etablissement WHERE Hebergement_Etablissement IS NOT NULL")
    return jsonify([row[0] for row in cur.fetchall()])

@app.route('/api/filters/statuts')
def get_statut_filters():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT statut_Etablissement FROM Etablissement WHERE statut_Etablissement IS NOT NULL")
    return jsonify([row[0] for row in cur.fetchall()])

@app.route('/api/etablissements')
def get_filtered_etablissements():
    conn = get_db_connection()
    cur = conn.cursor()
    filters = {
        'types': request.args.get('types', '').split(','),
        'hebergements': request.args.get('hebergements', '').split(','),
        'statuts': request.args.get('statuts', '').split(',')
    }

    query = "SELECT * FROM Etablissement WHERE 1=1"
    params = []

    if filters['types']:
        query += " AND type_Etablissement IN %s"
        params.append(tuple(filters['types']))
    
    if filters['hebergements']:
        query += " AND Hebergement_Etablissement IN %s"
        params.append(tuple(filters['hebergements']))
    
    if filters['statuts']:
        query += " AND statut_Etablissement IN %s"
        params.append(tuple(filters['statuts']))

    cur.execute(query, params)
    results = cur.fetchall()
    
    return jsonify([dict(row) for row in results])

@app.route('/ajouter_jpo')
def ajouter_jpo():
    return render_template('ajouter_jpo.html')

@app.route('/get_tables')
def get_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name NOT IN ('geography_columns', 'geometry_columns', 'spatial_ref_sys');")
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({'tables': tables})


@app.route('/get_columns/<table>')
def get_columns(table):
    table_name = table
    if not table_name:
        return jsonify({'error': 'Table name is required'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        AND table_schema = 'public'
        AND data_type NOT IN ('serial', 'bigserial') -- Exclude serial types
        AND column_name NOT IN (
            SELECT column_name
            FROM information_schema.columns c
            JOIN pg_class cl ON c.table_name = cl.relname
            WHERE c.table_name = %s
            AND (pg_get_serial_sequence(cl.relname, c.column_name) IS NOT NULL)
        );
    """, (table_name, table_name))
    
    columns = [{"column_name": row[0], "data_type": row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return jsonify({'columns': columns})

from datetime import datetime

@app.route('/add_data/<table>', methods=['POST'])
def add_data(table):
    form_data = request.form
    print(f"Form Data: {form_data}")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = %s 
          AND table_schema = 'public'
    """, (table,))

    columns = cur.fetchall()
    print(f"Columns from DB: {columns}")

    column_names = [col[0] for col in columns]
    column_types = {col[0]: col[1] for col in columns}
    column_defaults = {col[0]: col[2] for col in columns}

    print(f"Column Names: {column_names}")
    print(f"Column Defaults: {column_defaults}")

    serial_columns = [col for col, default in column_defaults.items() if default and 'nextval' in default]
    print('Serial columns detected:')
    print(serial_columns)

    for col in serial_columns:
        if col in column_names:
            column_names.remove(col)

    cur.execute("""
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_name = %s
          AND table_schema = 'public'
          AND constraint_name = 'primary'
    """, (table,))
    
    primary_key_columns = [row[0] for row in cur.fetchall()]
    print(f"Primary Key columns: {primary_key_columns}")

    for pk_column in primary_key_columns:
        if pk_column in column_names:
            column_names.remove(pk_column)

    if not column_names:
        return jsonify({'success': False, 'message': 'No valid columns found for this table.'}), 400

    column_placeholders = ', '.join([f"%({col})s" for col in column_names])
    column_names_str = ', '.join(column_names)

    query = f"INSERT INTO {table} ({column_names_str}) VALUES ({column_placeholders})"
    print(f"Generated SQL Query: {query}")

    data_to_insert = {}
    for column in column_names:
        if column in form_data:
            value = form_data[column]
            try:
                if column_types[column] == 'boolean':
                    value = value.lower() == 'true'
                elif column_types[column] == 'date':
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                data_to_insert[column] = value
            except Exception as e:
                print(f"Error processing value for column {column}: {e}")
                return jsonify({'success': False, 'message': f"Error processing value for column {column}"}), 400
    
    print(f"Data to insert: {data_to_insert}")

    try:
        cur.execute(query, data_to_insert)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Data added successfully!'})
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"Error executing query: {e}")
        return jsonify({'success': False, 'message': 'Error adding data.', 'error': str(e)}), 500



@app.route('/modifier_jpo')
def modifier_jpo():
    return render_template('modifier_jpo.html')

@app.route('/get_data', methods=['POST'])
def get_data():
    data = request.get_json()
    table = data.get('table') 
    idTable = data.get('idTable') 

    if not table or not idTable:
        return jsonify({
            'success': False,
            'message': 'Table or ID Table not provided.'
        })

    columns, primary_key = get_columns_for_table(table)

    if not primary_key:
        return jsonify({
            'success': False,
            'message': f'No primary key found for the table {table}.'
        })

    column_data = fetch_data_using_primary_key(table, primary_key, idTable)

    if column_data:
        return jsonify({
            'success': True,
            'columns': column_data
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No data found for the given table and ID.'
        })


def get_columns_for_table(table):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.column_name, c.ordinal_position, 
               CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_primary_key
        FROM information_schema.columns c
        LEFT JOIN (
            SELECT kcu.column_name, kcu.table_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc 
                ON kcu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY' AND kcu.table_name = %s
        ) pk ON c.column_name = pk.column_name
        WHERE c.table_name = %s
        ORDER BY c.ordinal_position;
    """, (table, table))

    columns_info = cursor.fetchall()

    columns = []
    primary_key = None

    for col in columns_info:
        col_name = col[0]
        is_primary_key = col[2]
        columns.append(col_name)
        if is_primary_key and not primary_key:
            primary_key = col_name  

    conn.close()

    return columns, primary_key


def fetch_data_using_primary_key(table, primary_key, idTable):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s AND table_schema = 'public'
    """
    cursor.execute(query, (table,))
    columns_info = cursor.fetchall()

    column_data = []
    for col in columns_info:
        column_name, column_type = col
        cursor.execute(f"SELECT {column_name} FROM {table} WHERE {primary_key} = %s", (idTable,))
        value = cursor.fetchone()[0]
        column_data.append({
            'name': column_name,
            'value': value,
            'type': column_type
        })

    conn.close()
    return column_data

@app.route('/modify_data', methods=['POST'])
def modify_data():
    data = request.get_json()
    table = data.get('table')
    idTable = data.get('idTable')
    updated_data = data.get('updated_data')

    if not table or not idTable or not updated_data:
        print(f"Missing parameters: table={table}, idTable={idTable}, updated_data={updated_data}")
        return jsonify({
            'success': False,
            'message': 'Missing required parameters.'
        })

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
              AND constraint_name = (
                  SELECT constraint_name
                  FROM information_schema.table_constraints
                  WHERE table_name = %s
                    AND constraint_type = 'PRIMARY KEY'
              )
        """, (table, table))

        primary_key_column = cur.fetchone()

        if primary_key_column is None:
            return jsonify({
                'success': False,
                'message': f'No primary key found for the table {table}.'
            })

        primary_key = primary_key_column[0]

        set_clause = ", ".join([f"{col} = %s" for col in updated_data.keys()])
        values = list(updated_data.values())
        values.append(idTable)

        query = f"UPDATE {table} SET {set_clause} WHERE {primary_key} = %s"

        cur.execute(query, values)
        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        print(f"Error updating data: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': 'Error updating data.'})

    finally:
        cur.close()
        conn.close()

@app.route('/delete_data', methods=['POST'])
def delete_data():
    data = request.get_json()
    table = data.get('table')
    idTable = data.get('idTable')

    if not table or not idTable:
        return jsonify({
            'success': False,
            'message': 'Missing required parameters.'
        })

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
              AND constraint_name = (
                  SELECT constraint_name
                  FROM information_schema.table_constraints
                  WHERE table_name = %s
                    AND constraint_type = 'PRIMARY KEY'
              )
        """, (table, table))

        primary_key_column = cur.fetchone()

        if primary_key_column is None:
            return jsonify({
                'success': False,
                'message': f'No primary key found for the table {table}.'
            })

        primary_key = primary_key_column[0]

        query = f"DELETE FROM {table} WHERE {primary_key} = %s"

        cur.execute(query, (idTable,))
        conn.commit()

        if cur.rowcount > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'No data found to delete.'})

    except Exception as e:
        print(f"Error deleting data: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': 'Error deleting data.'})

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
