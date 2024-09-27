import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

def get_osrm_route(start_lat, start_lon, end_lat, end_lon):
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        response = session.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'routes' in data and data['routes']:
                return [tuple(coord) for coord in data['routes'][0]['geometry']['coordinates']]
            else:
                st.warning("No route found. Check coordinates or road connectivity.")
        else:
            st.error(f"Failed to fetch route, HTTP status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching route: {e}")
    return []


# Function to preprocess KSI data
def preprocess_ksi_data(ksi_data):
    ksi_data['Road_Number'] = ksi_data['Roadclass1'].astype(str) + ksi_data['roadnum1'].astype(str)
    return ksi_data

# Streamlit UI for file upload and processing
st.title("Route and KSI Data Analysis")
uploaded_speed_file = st.file_uploader("Upload Speed Data CSV", type="csv")
uploaded_ksi_file = st.file_uploader("Upload KSI Data CSV", type="csv")

if uploaded_speed_file and uploaded_ksi_file:
    speed_data = pd.read_csv(uploaded_speed_file)
    ksi_data = pd.read_csv(uploaded_ksi_file)
    ksi_data = preprocess_ksi_data(ksi_data)

    if not speed_data.empty:
        road_number = st.selectbox("Select a Road Number", speed_data['Road_Number'].unique())
        selected_road = speed_data[speed_data['Road_Number'] == road_number].iloc[0]

        route_points = get_osrm_route(selected_road['latitude_S'], selected_road['longitude_S'], 
                                      selected_road['latitude_E'], selected_road['latitude_E'])

        if route_points:
            # Map visualization
            map_center = [selected_road['latitude_S'], selected_road['longitude_S']]
            m = folium.Map(location=map_center, zoom_start=14)
            folium.PolyLine(route_points, color="blue", weight=3).add_to(m)

            # Filter and display KSI points on the map
            filtered_ksi = ksi_data[(ksi_data['Road_Number'] == road_number) & (ksi_data['severity'].isin([1, 2]))]
            for idx, row in filtered_ksi.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=5,  # Increased radius for better visibility
                    color='red',
                    fill=True,
                    fill_color='red',
                    tooltip=f"Severity: {row['severity']}"
                ).add_to(m)

            st_folium(m, width=725, height=500)

            # Display the filtered KSI data
            st.write("Filtered KSI Data:")
            st.dataframe(filtered_ksi)
        else:
            st.error("No route data available. Unable to create a visual representation.")
    else:
        st.error("Loaded speed data is empty. Please check the file content.")
else:
    st.info("Please upload both speed and KSI data CSV files to proceed.")
