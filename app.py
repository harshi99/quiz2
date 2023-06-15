from flask import Flask, jsonify, request,render_template
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import os
import csv
import pyodbc
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.distance import geodesic


app = Flask(__name__)


# Blob Storage configuration
blob_connection_string = 'DefaultEndpointsProtocol=https;AccountName=assdata1;AccountKey=WMGVFc5Btn/cWP1ErRdsoFKp+VOWcfM9r5C6uOYSod9jeunIxoThQp+A6ecG6R48CFywsaCRl/AZ+ASttwd/CA==;EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
container_name = 'quiz2'

# SQL configuration
server = 'harshi1.database.windows.net'
database = 'quiz2'
username = 'harshi'
password = 'Azure.123'
driver = Driver='{ODBC Driver 18 for SQL Server};Server=tcp:harshi1.database.windows.net,1433;Database=quiz2;Uid=harshi;Pwd={Azure.123};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

# Establish the database connection
connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"
conn = pyodbc.connect(connection_string)





@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        city_name = request.form['city']
        selected_city = None
        nearby_cities = []

        # Find the selected city
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM city WHERE City = '{city_name}'")
        selected_city_data = cursor.fetchone()
        cursor.close()

        if selected_city_data:
            selected_city = {
                'City': selected_city_data.City,
                'State': selected_city_data.State,
                'Population': selected_city_data.Population,
                'lat': selected_city_data.lat,
                'lon': selected_city_data.lon
            }

            # Find nearby cities within 100 km
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM city")
            all_cities_data = cursor.fetchall()
            cursor.close()

            for city_data in all_cities_data:
                distance = geodesic((selected_city['lat'], selected_city['lon']), (city_data.lat, city_data.lon)).km
                if distance <= 100 and city_data != selected_city_data:
                    nearby_city = {
                        'City': city_data.City,
                        'State': city_data.State,
                        'Population': city_data.Population,
                        'lat': city_data.lat,
                        'lon': city_data.lon
                    }
                    nearby_cities.append(nearby_city)

        return render_template('index.html', selected_city=selected_city, nearby_cities=nearby_cities)

    return render_template('index.html')

@app.route('/add_city', methods=['POST'])
def add_city():
    city = request.form['city']
    state = request.form['state']
    population = request.form['population']
    latitude = request.form['latitude']
    longitude = request.form['longitude']

    # Add the city to the database
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO city (City, State, Population, lat, lon) VALUES (?, ?, ?, ?, ?)",
                   city, state, population, latitude, longitude)
    conn.commit()
    cursor.close()

    return jsonify({'message': 'City added successfully'})

@app.route('/remove_city', methods=['POST'])
def remove_city():
    city = request.form['city']
    state = request.form['state']

    # Remove the city from the database
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM city WHERE City = ? AND State = ?", city, state)
    conn.commit()
    cursor.close()

    return jsonify({'message': 'City removed successfully'})

@app.route('/bounding_box', methods=['POST'])
def bounding_box():
    min_latitude = float(request.form['min_latitude'])
    min_longitude = float(request.form['min_longitude'])
    max_latitude = float(request.form['max_latitude'])
    max_longitude = float(request.form['max_longitude'])

    # Find cities within the bounding box
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM city WHERE lat BETWEEN {min_latitude} AND {max_latitude} AND lon BETWEEN {min_longitude} AND {max_longitude}")
    cities_data = cursor.fetchall()
    cursor.close()

    cities = []
    for city_data in cities_data:
        city = {
            'City': city_data.City,
            'State': city_data.State,
            'Population': city_data.Population,
            'lat': city_data.lat,
            'lon': city_data.lon
        }
        cities.append(city)

    return render_template('index.html', cities=cities)
@app.route('/increment_population', methods=['POST'])
def increment_population():
    min_latitude = float(request.form['min_latitude'])
    min_longitude = float(request.form['min_longitude'])
    max_latitude = float(request.form['max_latitude'])
    max_longitude = float(request.form['max_longitude'])
    state_name = request.form['state_name']
    min_population = int(request.form['min_population'])
    max_population = int(request.form['max_population'])
    increment = int(request.form['increment'])

    modified_cities = []

    if state_name:
        # Increment population of cities in the specified state
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM city WHERE State = '{state_name}' AND Population BETWEEN {min_population} AND {max_population}")
        cities_data = cursor.fetchall()

        for city_data in cities_data:
            new_population = city_data.Population + increment
            cursor.execute(f"UPDATE city SET Population = {new_population} WHERE City = '{city_data.City}' AND State = '{city_data.State}'")
            modified_cities.append({
                'City': city_data.City,
                'State': city_data.State,
                'Population': new_population,
                'lat': city_data.lat,
                'lon': city_data.lon
            })

        conn.commit()
        cursor.close()

    else:
        # Increment population of cities within the bounding box
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM city WHERE lat BETWEEN {min_latitude} AND {max_latitude} AND lon BETWEEN {min_longitude} AND {max_longitude}")
        cities_data = cursor.fetchall()

        for city_data in cities_data:
            new_population = city_data.Population + increment
            cursor.execute(f"UPDATE city SET Population = {new_population} WHERE City = '{city_data.City}' AND State = '{city_data.State}'")
            modified_cities.append({
                'City': city_data.City,
                'State': city_data.State,
                'Population': new_population,
                'lat': city_data.lat,
                'lon': city_data.lon
            })

        conn.commit()
        cursor.close()

    return render_template('index.html', modified_cities=modified_cities, count=len(modified_cities))



if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    app.run(debug=True)
    app.run(host='localhost', port=port)

