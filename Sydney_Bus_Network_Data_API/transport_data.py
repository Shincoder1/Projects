from flask import Flask, send_file, request, jsonify, Response
from flask_restx import Api, Resource, fields, Namespace
from flask_cors import CORS
import hashlib
import sqlite3
import os
import requests
import datetime
import jwt
from functools import wraps
import io
import zipfile
import csv
from rapidfuzz import fuzz, process
import csv

# -------------------------------------------------- AUTHENTICATION --------------------------------------------------
# Proper authentication, taken from week 8 labs. 
class AuthenticationToken:
    def __init__(self, secret_key, expires_in):
        self.secret_key = secret_key
        self.expires_in = expires_in
    
    def generate_token(self, username):
        info = {
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=self.expires_in)
        }
        return jwt.encode(info, self.secret_key, algorithm='HS256')
    
    def validate_token(self, token):
        info = jwt.decode(token, self.secret_key, algorithms=['HS256'])
        return info['username']
    
SECRET_KEY = "A SECRET KEY; USUALLY A VERY LONG RANDOM STRING"
expires_in = 3600
auth = AuthenticationToken(SECRET_KEY, expires_in)


# -------------------------------------------------- SETUP FLASK --------------------------------------------------
# Usual flask setup.
app = Flask(__name__)
CORS(app)
api = Api(
    app, 
    version="1.0", 
    title="NSW Transport API", 
    description="User and Agency Management API", 
    doc="/", 
    authorizations={
        'API-KEY': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'AUTH-TOKEN',
            'description': "Paste your token in."
        }
    },
    security='API-KEY'
)

dbf = "z5477450.sqlite"

# -------------------------------------------------- DATABASE LOGIC --------------------------------------------------
# Create default users.
def init_users(c, conn):
    u = [("admin", "admin", "admin", 1), 
         ("commuter", "commuter", "commuter", 1), 
         ("planner", "planner", "planner", 1)]

    for username, password, role, active in u:
        salt, hashed_password = hash_password(password)
        c.execute("INSERT INTO users (username, password, salt, role, active) VALUES (?, ?, ?, ?, ?)", (username, hashed_password, salt, role, active))
        conn.commit()

# Hash function, using salt to ensure and maximise entropy of hash. 
def hash_password(password):
    salt = os.urandom(16)
    hashed_password = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
    return salt.hex(), hashed_password
def get_db():
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    return conn
# Initialise the db.
def init_db():
    conn = sqlite3.connect(dbf)
    c = conn.cursor()
    # Create a table for users. 
    c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                salt TEXT NOT NULL,
                role  TEXT CHECK (ROLE IN ('admin', 'planner', 'commuter')) NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
    # The following tables are the txt files in the zip file. 
    c.execute("""
            CREATE TABLE IF NOT EXISTS agencies (
                agency_id TEXT PRIMARY KEY,
                agency_name TEXT,
                agency_url TEXT,
                agency_timezone TEXT,
                agency_lang TEXT,
                agency_phone TEXT,
                imported_at TEXT
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS calendar_dates(
                agency_id TEXT,
                service_id TEXT,
                date TEXT,
                exception_type INTEGER,
                PRIMARY KEY(agency_id, service_id, date)
            )
        """) 

    c.execute("""
            CREATE TABLE IF NOT EXISTS calendar(
                agency_id TEXT,
                service_id TEXT,
                monday INTEGER,
                tuesday INTEGER,
                wednesday INTEGER,
                thursday INTEGER,
                friday INTEGER,
                saturday INTEGER,
                sunday INTEGER,
                start_date TEXT,
                end_date TEXT,
                PRIMARY KEY(agency_id, service_id)
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                agency_id TEXT,
                note_id TEXT,
                note_text TEXT,
                PRIMARY KEY (agency_id, note_id)
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                agency_id TEXT,
                route_id TEXT,
                route_short_name TEXT,
                route_long_name TEXT,
                route_desc TEXT,
                route_type INTEGER,
                route_url TEXT,
                route_color TEXT,
                route_text_color TEXT,
                PRIMARY KEY (agency_id, route_id)
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS shapes(
                agency_id TEXT,
                shape_id TEXT,
                shape_pt_lat REAL,
                shape_pt_lon REAL,
                shape_pt_sequence INTEGER,
                shape_dist_traveled REAL,
                PRIMARY KEY(agency_id, shape_id, shape_pt_sequence)
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS stop_times(
                agency_id TEXT,
                trip_id TEXT,
                arrival_time TEXT,
                departure_time TEXT,
                stop_id TEXT,
                stop_sequence INTEGER,
                stop_headsign TEXT,
                pickup_type INTEGER,
                drop_off_type INTEGER,
                shape_dist_traveled REAL,
                timepoint INTEGER,
                stop_note TEXT,
                PRIMARY KEY(agency_id, trip_id, stop_sequence)
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS stops (
                agency_id TEXT,
                stop_id TEXT,
                stop_code TEXT,
                stop_name TEXT,
                stop_desc TEXT,
                stop_lat REAL,
                stop_lon REAL,
                zone_id TEXT,
                stop_url TEXT,
                location_type INTEGER,
                parent_station TEXT,
                stop_timezone TEXT,
                wheelchair_boarding INTEGER,
                platform_code TEXT,
                PRIMARY KEY(agency_id, stop_id)
            )
        """)
    
    c.execute("""
            CREATE TABLE IF NOT EXISTS trips(
                agency_id TEXT,
                route_id TEXT,
                service_id TEXT,
                trip_id TEXT,
                trip_headsign TEXT,
                trip_short_name TEXT,
                direction_id INTEGER,
                block_id TEXT,
                shape_id TEXT,
                wheelchair_accessible INTEGER,
                bikes_allowed INTEGER,
                trip_note TEXT, 
                route_direction TEXT,
                PRIMARY KEY(agency_id, trip_id)
            )
        """)

    # Table to keep track of a user's favourite routes. 
    c. execute("""
            CREATE TABLE IF NOT EXISTS favourites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                route_id TEXT NOT NULL,
                UNIQUE(username, route_id)
               )
        """)
    
    conn.commit()

    c.execute("SELECT COUNT(*) FROM users")

    if c.fetchone()[0] == 0: 
        init_users(c, conn)
    conn.close()

init_db()

# -------------------------------------------------- DATABASE MODELS --------------------------------------------------
user_model = api.model("User", {
    "id": fields.Integer(readonly=True),
    "username": fields.String(required=True),
    "role": fields.String(required=True, enum=["admin", "planner", "commuter"]),
    "active": fields.Boolean
})

create_user_model = api.model("CreateUser", {
    "username": fields.String(required=True),
    "password": fields.String(required=True),
    "role": fields.String(required=True, enum=["planner", "commuter"])
})
        
# Helper function to check if a user is admin.
def is_admin(username):
    conn = sqlite3.connect(dbf)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE LOWER(username)=LOWER(?)", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        api.abort(401, "User not found")
    elif row[0].lower() != "admin":
        api.abort(403, "User is not Admin.")

# Helper function which takes in a username and a list of roles. Function will check if the user's role
# is within one of the specified roles in the list. 
def role_authorised(username, roles):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE LOWER(username)=LOWER(?)", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        api.abort(401, "User not found")
    
    broken = False
    for role in roles:
        if row[0].lower() == role.lower():
            broken = True
    if not broken:
        api.abort(403, "User not authorised.")
    
# -------------------------------------------------- NAMESPACES --------------------------------------------------
login_ns = api.namespace("LoginRoute", description="Login as a user here")
admin_ns = api.namespace("Admin", description="Admin user management")
users_ns = api.namespace("Users", description="User management")
import_ns = api.namespace("Import", description="Importing GTFS data")
routes_ns = api.namespace("Routes", description="Get route information")
trips_ns = api.namespace("Trips", description="Get trip information")
stops_ns = api.namespace("Stops", description="Get stop information")
search_ns = api.namespace("Search", description="Search stops by name (Search can be partial)")
favourite_ns = api.namespace("Favourites", description="Manage user favourite list of routes")
export_ns = api.namespace("Export",description="Generate a map showing the shape of their favourite routes")
# -------------------------------------------------- AUTHENTICATION MODELS --------------------------------------------------
credential_model = api.model('Credentials', {
    'username': fields.String(required=True),
    'password': fields.String(required=True)
})
# -------------------------------------------------- AUTHENTICATION --------------------------------------------------
# Authentication, taken from week 8 labs. 
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('AUTH-TOKEN')
        if not token:
            api.abort(401, 'Authentication token is missing')
        try:
            username = auth.validate_token(token)
        except Exception as e:
            api.abort(401, str(e))

        if len(args) > 0 and isinstance(args[0], Resource):
            return f(args[0], username, *args[1:], **kwargs)
        else:
            return f(username, *args, **kwargs)
    return decorated

# -------------------------------------------------- USER ROUTES --------------------------------------------------
def db_connect():
    return sqlite3.connect(dbf)

@login_ns.route('/login')
class Login(Resource):
    @api.expect(credential_model, validate=True)
    @api.response(200, 'Login successful')
    @api.response(400, 'Missing parameters')
    @api.response(401, 'Invalid credentials')
    @api.response(403, 'Account deactivated')
    @api.response(404, 'Username not found')
    def post(self):
        data = request.json
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return {"error": "Missing username or password"}, 400
        
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT username, password, salt, active FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()

        if not row:
            api.abort(404, f"{username} not found.")
        elif not row[3]:
            return {"error": "User has been deactivated."}, 403
        
        stored_username, stored_password, stored_salt, active = row
        salt_bytes = bytes.fromhex(stored_salt)
        verify_password = hashlib.sha256(salt_bytes + password.encode('utf-8')).hexdigest()

        if verify_password != stored_password:
            return {"error": "Incorrect password"}, 401
        
        token = auth.generate_token(username)
        return {"token": token}, 200

@admin_ns.route("/users")
class UserList(Resource):
    @requires_auth
    @admin_ns.doc(description="List all users, only functional for admins")
    @api.response(200, 'Route successful')
    @api.response(401, 'Unauthorized parameters')
    @api.response(403, 'Incorrect parameters')
    def get(self, user):
        is_admin(user)
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT id, username, role, active FROM users")
        users = [{"id": user[0], "username": user[1], "role": user[2], "active": bool(user[3])} for user in c.fetchall()]
        conn.close()

        return users, 200

    @requires_auth
    @admin_ns.expect(create_user_model, validate=True)
    @admin_ns.doc(description="Create a new user, only functional for admins")
    @api.response(201, 'Route successful')
    @api.response(400, 'Missing parameters')
    def post(self, user):
        is_admin(user)
        data = request.json
        new_username, password, role = data["username"], data["password"], data["role"].lower()
        salt, hashed_password = hash_password(password)
        conn= db_connect()
        c = conn.cursor()
        
        try: 
            c.execute("INSERT INTO users (username, password, salt, role, active) VALUES (?, ?, ?, ?, 1)", (new_username, hashed_password, salt, role))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            api.abort(400, f"{new_username} already exists.")
        conn.close()

        return {"message": f"User {new_username} has been created successfully."}, 201

@admin_ns.route("/delete/<string:delete_username>")
class UserDelete(Resource):
    @requires_auth
    @users_ns.doc(description="Delete a user, only functional for admins.")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def delete(self, user, delete_username):
        is_admin(user)

        conn= db_connect()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username=?", (delete_username,))
        conn.commit()

        if c.rowcount == 0:
            conn.close()
            api.abort(404, f"{delete_username} does not exist.")
        
        conn.close()
        return {"message": f"{delete_username} has been deleted"}, 200

@users_ns.route("/<string:activate_username>/activate")
class ActivateUser(Resource):
    @requires_auth
    @users_ns.doc(description="Activate a user, only functional for admins.")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def put(self, user, activate_username):
        is_admin(user)

        conn= db_connect()
        c = conn.cursor()
        c.execute("UPDATE users SET active=1 WHERE username=?", (activate_username,))
        conn.commit()

        if c.rowcount == 0:
            conn.close()
            api.abort(404, f"{activate_username} does not exist.")
        
        conn.close()
        return {"message": f"{activate_username} has been activated"}, 200
    
@users_ns.route("/<string:deactivate_username>/deactivate")
class DeactivateUser(Resource):
    @requires_auth
    @users_ns.doc(description="Deactivate a user, only functional for admins.")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def put(self, user, deactivate_username):
        is_admin(user)

        conn= db_connect()
        c = conn.cursor()
        c.execute("UPDATE users SET active=0 WHERE username=?", (deactivate_username,))
        conn.commit()

        if c.rowcount == 0:
            conn.close()
            api.abort(404, f"{deactivate_username} does not exist.")

        conn.close()
        return {"message": f"{deactivate_username} has been deactivated."}, 200
# -------------------------------------------------- AGENCY ROUTES --------------------------------------------------
@import_ns.route("/<string:agency_id>")
class ImportAgency(Resource):
   @requires_auth
   @import_ns.doc(description="Import agency data, only functional to admins and planners only.")
   @api.response(200, 'Route successful')
   @api.response(400, 'Invalid parameters')
   @api.response(500, 'Invalid file')
   def post(self, user, agency_id):
       role_authorised(user, ["admin", "planner"])

       if not (agency_id.startswith("GSBC") or agency_id.startswith("SBSC")):
           api.abort(400, "Invalid agency ID prefix.")

       url = f"https://api.transport.nsw.gov.au/v1/gtfs/schedule/buses/{agency_id}"
       headers = {"Authorization": "apikey eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJaajF1RngxQkVIU090czV4OHJIc0hHZFM1U0RKWjNYQk8tY1ZOUXh1MVZNIiwiaWF0IjoxNzYxNjI5ODAwfQ.jW3wXOTqEcKhSaBlwZW6kcbQRZqpyMAJMZW5UWHlsFE"}

       try:
           response = requests.get(url, headers=headers, timeout=30)
           response.raise_for_status()
       except requests.exceptions.RequestException as e:
           api.abort(500, f"Could not connect to GTFS API.")

       try:
           zip_file = zipfile.ZipFile(io.BytesIO(response.content))
       except zipfile.BadZipFile:
           api.abort(500, "Invalid ZIP file received")


       conn = db_connect()
       c = conn.cursor()


       tables = ['agencies', 'calendar_dates', 'calendar', 'notes', 'routes', 'shapes', 'stop_times', 'stops', 'trips']
       for table in tables:
           c.execute(f"DELETE FROM {table} WHERE agency_id=?", (agency_id,))


       row_counts = {}


       # All files in the zip folder.
       files_in_zip = {
           'agency.txt': 'agencies', 'calendar_dates.txt': 'calendar_dates', 'calendar.txt': 'calendar', 'notes.txt': 'notes',
           'routes.txt': 'routes', 'shapes.txt': 'shapes', 'stop_times.txt': 'stop_times','stops.txt': 'stops',
           'trips.txt': 'trips'
       }


       for filename, table in files_in_zip.items():
           if filename not in zip_file.namelist():
               continue


           with zip_file.open(filename) as file:
               text_file = io.TextIOWrapper(file, encoding='utf-8-sig')
               reader = csv.DictReader(text_file)
               data = list(reader)


               if not data:
                   continue


               for d in data:
                   d['agency_id'] = agency_id


               columns = list(data[0].keys())
               ph_list = []
               for col in columns:
                   ph_list.append('?')
               placeholders = ','.join(ph_list)
               col_names = ','.join(columns)


               for d in data:
                   values = []
                   for col in columns:
                       values.append(d.get(col, ''))
                   c.execute(f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})", values)


               row_counts[table] = len(data)


       imported_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
       c.execute("UPDATE agencies SET imported_at=? WHERE agency_id=?", (imported_at, agency_id))


       conn.commit()
       conn.close()


       return {"message": f"Imported {agency_id}"}


@routes_ns.route("/route/<string:route_id>")
class RouteDetail(Resource):
    @requires_auth
    @routes_ns.doc(description="Retrieve information about a specific route by its id.")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def get (self, user, route_id):
        conn = db_connect()
        c = conn.cursor()
        c.execute("""
                SELECT agency_id, route_id, route_short_name, route_long_name, route_desc,
                route_type, route_url, route_color, route_text_color
                FROM routes
                WHERE route_id=? 
        """, (route_id,))

        route = c.fetchone()
        conn.close()
        if not route:
            api.abort(404, "route_id not found.")
        return {
            "agency_id": route[0], "route_id": route[1], "route_short_name": route[2], "route_long_name": route[3],
            "route_desc": route[4], "route_type": route[5], "route_url": route[6],"route_color": route[7], "route_text_color": route[8]
        }, 200
    
@routes_ns.route("/trip/<string:trip_id>")
class TripDetail(Resource):
    @requires_auth
    @routes_ns.doc(description="Retrieve information about a specific trip by trip_id.")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def get (self, user, trip_id):
        conn = db_connect()
        c = conn.cursor()
        c.execute("""
                SELECT agency_id, route_id, service_id, trip_id, trip_headsign, trip_short_name, direction_id,
                block_id, shape_id, wheelchair_accessible, bikes_allowed, trip_note, route_direction
                FROM trips
                WHERE trip_id=? 
        """, (trip_id,))

        trip = c.fetchone()
        conn.close()
        
        if not trip:
            api.abort(404, f"Trip {trip_id} not found")
        
        return {
            "agency_id": trip[0], "route_id": trip[1], "service_id": trip[2], "trip_id": trip[3], "trip_headsign": trip[4],
            "trip_short_name": trip[5], "direction_id": trip[6], "block_id": trip[7], "shape_id": trip[8],
            "wheelchair_accessible": trip[9], "bikes_allowed": trip[10], "trip_note": trip[11], "route_direction": trip[12]
        }, 200
    
@routes_ns.route("/stop/<string:stop_id>")
class StopDetail(Resource):
    @requires_auth
    @routes_ns.doc(description="Retrieve information about a specific stop by stop_id.")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def get (self, user, stop_id):
        conn = db_connect()
        c = conn.cursor()
        c.execute("""
                SELECT agency_id, stop_id, stop_code, stop_name, stop_desc, stop_lat, stop_lon, zone_id,
                stop_url, location_type, parent_station, stop_timezone, wheelchair_boarding, platform_code
                FROM stops
                WHERE stop_id=? 
        """, (stop_id,))

        stop = c.fetchone()
        conn.close()
        
        if not stop:
            api.abort(404, f"Stop {stop_id} not found")
        
        return {
            "agency_id": stop[0], "stop_id": stop[1], "stop_code": stop[2], "stop_name": stop[3],"stop_desc": stop[4],
            "stop_lat": stop[5], "stop_lon": stop[6], "zone_id": stop[7],"stop_url": stop[8],"location_type": stop[9], 
            "parent_station": stop[10], "stop_timezone": stop[11],  "wheelchair_boarding": stop[12], "platform_code": stop[13]
        }, 200

# Helper function to make result into pages
def make_pages(results, page, page_num):
    length_items = len(results)
    tpages = (length_items + page_num - 1) // page_num

    start = (page - 1) * page_num
    end = start + page_num
    pages = results[start:end]
    return {"page": page, "per_page": page_num,"total_pages": (len(results) + page_num - 1) // page_num,"data": pages}


@routes_ns.route("/agency/<string:agency_id>")
class AgencyRoutes(Resource):
    @requires_auth
    @routes_ns.doc(description="Get all routes for a specific agency")
    @routes_ns.param('page', 'Page number', type=int, required=False)
    @routes_ns.param('routes_per_page', 'Results per page, choose between 50 & 100', type=int, required=False)
    @api.response(200, 'Route successful')
    @api.response(400, 'Missing parameters')
    @api.response(404, 'Parameter not found')
    def get(self, user, agency_id):
        page = request.args.get('page', 1, type=int)
        routes_per_page = request.args.get('routes_per_page', 50, type=int)

        # Check page parameters.
        if page < 1:
            api.abort(400, "Page must be more than at least 1")
        elif routes_per_page < 1 or routes_per_page > 100:
            api.abort(400, "Pages must be between 1 and 100")

        conn = db_connect()
        c = conn.cursor()
        # Check if agency has already been imported by someone. 
        c.execute("SELECT agency_id FROM agencies WHERE agency_id=?", (agency_id,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Agency {agency_id} not found")
        c.execute("""  
            SELECT agency_id, route_id, route_short_name, route_long_name, route_desc, route_type, route_url, route_color,
                  route_text_color
            FROM routes WHERE agency_id=?
            ORDER BY route_short_name
        """, (agency_id,))
        route_rows = c.fetchall()
        conn.close()

        all_routes = []

        for r in route_rows:
            rt ={"agency_id": r[0], "route_id": r[1], "route_short_name": r[2], "route_long_name": r[3],"route_desc": r[4],
                "route_type": r[5], "route_url": r[6], "route_color": r[7], "route_text_color": r[8]
            }
            all_routes.append(rt)
        return make_pages(all_routes, page, routes_per_page), 200

@trips_ns.route("/route/<string:route_id>")
class RouteTrips(Resource):
    @requires_auth
    @trips_ns.doc(description="Get all trips for a specific route")
    @trips_ns.param('page', 'Page number', type=int, required=False)
    @trips_ns.param('trips_per_page', 'Results per page, choose between 50 & 100', type=int, required=False)
    @api.response(200, 'Route successful')
    @api.response(400, 'Missing parameters')
    @api.response(404, 'Parameter not found')
    def get(self, user, route_id):
        page = request.args.get('page', 1, type=int)
        trips_per_page = request.args.get('trips_per_page', 50, type=int)

        # Check page parameters.
        if page < 1:
            api.abort(400, "Page must be >= 1")
        elif trips_per_page < 1 or trips_per_page > 100:
            api.abort(400, "Pages must be between 1 and 100")

        conn = db_connect()
        c = conn.cursor()
        # Check if agency has already been imported by someone. 
        c.execute("SELECT route_id FROM routes WHERE route_id=?", (route_id,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Route {route_id} not found")
        
        c.execute("""
            SELECT agency_id, route_id, service_id, trip_id, trip_headsign, trip_short_name, direction_id,
                    block_id, shape_id, wheelchair_accessible, bikes_allowed, trip_note, route_direction
            FROM trips WHERE route_id=?
            ORDER BY trip_id
        """, (route_id,))

        trips_row = c.fetchall()
        conn.close()

        all_trips = []

        for t in trips_row:
            rt ={
                "agency_id": t[0], "route_id": t[1], "service_id": t[2], "trip_id": t[3], "trip_headsign": t[4], "trip_short_name": t[5],
                "direction_id": t[6], "block_id": t[7], "shape_id": t[8], "wheelchair_accessible": t[9], "bikes_allowed": t[10],
                "trip_note": t[11], "route_direction": t[12]
            }
            all_trips.append(rt)
        return make_pages(all_trips, page, trips_per_page), 200
    
@stops_ns.route("/route/<string:trip_id>")
class RouteTrips(Resource):
    @requires_auth
    @stops_ns.doc(description="Get all stop for a trip")
    @stops_ns.param('page', 'Page number', type=int, required=False)
    @stops_ns.param('stops_per_page', 'Results per page, choose between 50 & 100', type=int, required=False)
    @api.response(200, 'Route successful')
    @api.response(400, 'Missing parameters')
    @api.response(404, 'Parameter not found')
    def get(self, user, trip_id):
        page = request.args.get('page', 1, type=int)
        stops_per_page = request.args.get('stops_per_page', 50, type=int)

        # Check page parameters.
        if page < 1:
            api.abort(400, "Page must be >= 1")
        if stops_per_page < 1 or stops_per_page > 100:
            api.abort(400, "Pages must be between 1 and 100")

        conn = db_connect()
        c = conn.cursor()
        # Check if agency has already been imported by someone. 
        c.execute("SELECT route_id FROM trips WHERE trip_id=?", (trip_id,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Route {trip_id} not found")
        
        c.execute("""
            SELECT s.agency_id, s.stop_id, s.stop_code, s.stop_name, s.stop_desc,
                   s.stop_lat, s.stop_lon, s.zone_id, s.stop_url, s.location_type,
                   s.parent_station, s.stop_timezone, s.wheelchair_boarding, s.platform_code,
                   st.arrival_time, st.departure_time, st.stop_sequence, st.stop_headsign,
                   st.pickup_type, st.drop_off_type, st.stop_note
            FROM stops s
            JOIN stop_times st ON s.stop_id = st.stop_id AND s.agency_id = st.agency_id
            WHERE st.trip_id=?
            ORDER BY st.stop_sequence
        """, (trip_id,))

        stops_row = c.fetchall()
        conn.close()

        all_stops = []

        for s in stops_row:
            st = {
            "agency_id": s[0], "stop_id": s[1], "stop_code": s[2], "stop_name": s[3], "stop_desc": s[4],
            "stop_lat": s[5], "stop_lon": s[6],"zone_id": s[7], "stop_url": s[8], "location_type": s[9],
            "parent_station": s[10], "stop_timezone": s[11], "wheelchair_boarding": s[12], "platform_code": s[13],
            "arrival_time": s[14], "departure_time": s[15], "stop_sequence": s[16], "stop_headsign": s[17],
            "pickup_type": s[18], "drop_off_type": s[19],"stop_note": s[20]
            }

            all_stops.append(st)

        return make_pages(all_stops, page, stops_per_page), 200

search_model = api.model("StopSearchResult", {
    "stop_id": fields.String,
    "stop_name": fields.String,
    "agency_id": fields.String,
    "associated_trips": fields.List(fields.String),
    "associated_routes": fields.List(fields.String)
})

@search_ns.route("/")
class StopSearch(Resource):
    @requires_auth
    @search_ns.doc(description="Search for stops by name. Search can be partial.")
    @search_ns.param('q', 'Stop names', required=True)
    @search_ns.param('page', 'Page number', type=int, required=False)
    @search_ns.param('stops_per_page', 'Results per page, between 50 & 100', type=int, required=False)
    @api.response(200, 'Route successful')
    @api.response(400, 'Invalid parameters')
    def get(self, user):
        q = request.args.get('q', "")
        page = request.args.get('page', 1, type=int)
        stops_per_page = request.args.get('stops_per_page', 50, type=int)

        if not q:
            api.abort(400, "Query parameter is required")
        elif page < 1:
            api.abort(400, "Page must be >= 1")
        elif stops_per_page < 1 or stops_per_page > 100:
            api.abort(400, "Pages must be between 1 and 100")

        conn = db_connect()
        c = conn.cursor()

        c.execute("SELECT agency_id, stop_id, stop_name FROM stops")
        stops = c.fetchall()

        matches = []
        for stop in stops:
            id, stop, name = stop
            if fuzz.partial_ratio(q.lower(), name.lower()) >= 80: 
                c.execute("""SELECT DISTINCT trip_id, route_id 
                          FROM trips 
                          WHERE agency_id=? 
                          AND trip_id IN (SELECT trip_id FROM stop_times WHERE stop_id=?)
                        """, (id, stop))
                all_stops = c.fetchall()
                trip_id_list = []
                route_id_list = []

                for trip_id, route_id in all_stops:
                    trip_id_list.append(trip_id)
                    if route_id not in route_id_list:
                        route_id_list.append(route_id)

                matches.append({"stop_id": stop, "stop_name": name, "agency_id": id, 
                                "matched_trips": trip_id_list,"matched_routes": route_id_list
                })

        conn.close()
        return make_pages(matches, page, stops_per_page), 200
    
# -------------------------------------------------- FAVOURITE USER ROUTES --------------------------------------------------
@favourite_ns.route("/<string:username>")
class FavouriteRoutes(Resource):
    @requires_auth
    @favourite_ns.doc(description="Get favourites list given a username")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter not found')
    def get(self, user, username):
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE username=?", (username,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Username {username} not found")

        c.execute("SELECT route_id FROM favourites WHERE username=?", (username,))
        rows = c.fetchall()

        favs = []
        for row in rows:
            favs.append(row[0])

        conn.close()

        return {"username": username, "favourites": favs}, 200
    
    @requires_auth
    @favourite_ns.doc(description="Add a new favourite route for a user")
    @favourite_ns.expect(api.model("Favourite", {"route_id": fields.String(required=True)}))
    @api.response(200, 'Route successful')
    @api.response(400, 'Too many routes')
    @api.response(404, 'Parameter not found')
    def post(self, user, username):
        data = request.get_json()
        route_id = data.get("route_id")

        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE username=?", (username,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Username {username} not found")
        # See how many favourites routes a user has stored. If trying to insert when 2 routes have already
        # been saved, return 400 error.
        c.execute("SELECT COUNT(*) FROM favourites WHERE username=?", (username,))
        count = c.fetchone()[0]
        if count >= 2:
            conn.close()
            api.abort(400, f"{username} already has saved 2 favourite routes.")

        # Now check for any duplicates before inserting. If user has already added a route to their list,
        # return 400 error. 
        c.execute("SELECT * FROM favourites WHERE username=? AND route_id=?", (username, route_id))
        if c.fetchone():
            conn.close()
            api.abort(400, f"Route {route_id} already in favourites.")

        c.execute("SELECT * FROM routes WHERE route_id=?", (route_id,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Route {route_id} is not found.")
            

        # Now insert the file into the favourites table. 
        c.execute("INSERT INTO favourites (username, route_id) VALUES (?, ?)", (username, route_id))
        conn.commit()
        conn.close()

        return {"message": f"{username} has added route {route_id} to their favourites list."}
    
    @requires_auth
    @favourite_ns.doc(description="Delete a route from a user's favourites list.")
    @favourite_ns.expect(api.model("DeleteFavourite", {"route_id": fields.String(required=True)}))
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter could not be found')
    def delete(self, user, username):
        data = request.get_json()
        route_id = data.get("route_id")

        conn = db_connect()
        c = conn.cursor()
        c.execute("DELETE FROM favourites WHERE username=? AND route_id=?", (username, route_id))
        conn.commit()

        deleted = c.rowcount
        conn.close()

        if deleted == 0:
            return {"message": f"Route {route_id} could not be found."}, 404

        return {"message": f"Deleted route {route_id} from {username}'s favourites list."}
    
# -------------------------------------------------- EXPORTING ROUTES --------------------------------------------------
@export_ns.route("/csv/<string:username>")
class FavouriteRoutesCSV(Resource):
    @requires_auth
    @export_ns.doc(description="Export a user's favourite routes as a csv file")
    @api.response(200, 'Route successful')
    @api.response(404, 'Parameter could not be found')
    def get(self, user, username):
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE username=?", (username,))
        if not c.fetchone():
            conn.close()
            api.abort(404, f"Username {username} not found")

        c.execute("SELECT route_id FROM favourites WHERE username=?", (username,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            api.abort(404, "User has no favourite routes.")

        write = io.StringIO()
        # Now write the rows into a csv file.
        csv_writer = csv.writer(write)
        csv_writer.writerow(["route_id"])
        for fav in rows:
            csv_writer.writerow([fav[0]])
        
        # Send the cursor back to the start
        write.seek(0)

        response = Response(write.getvalue(), mimetype="text/csv", 
                            headers={"Content-Disposition": "attachment; filename=favourites.csv"})
        return response

if __name__ == "__main__":
    app.run(debug=True)