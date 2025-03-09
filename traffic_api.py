import requests
import json
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
WORKDAYS_PER_YEAR = 250
HOURLY_WAGE = 20
FUEL_CONSUMPTION_MIN = 0.016
FUEL_COST_PER_GALLON = 3
AI_REDUCTION_PERCENT = 0.20
CURRENT_DATE = datetime(2025, 3, 9)

# HERE Traffic API configuration
HERE_API_BASE_URL = "https://data.traffic.hereapi.com/v7/flow"
HERE_API_KEY = "6gbAUK7xvwNxdcExWOPDcKizVzc7fkLkeXAjuc1uwPk"
LAT = 42.8864  # Example latitude for Buffalo, NY
LON = -78.8784  # Example longitude for Buffalo, NY
RADIUS = 500  # Radius in meters

# xAI API configuration
XAI_API_KEY = "xai-r825JSFImisHEYkTzPDRmY8K5dUpqbs01nuVSMCot72XWfDGHVoAWKqx0xaHqd1KHlhdrFiOEUrCnMyE"
XAI_API_URL = "https://api.x.ai/v1/chat/completions"
XAI_HEADERS = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}

# Town and intersection data with approximate coordinates
TOWNS_INTERSECTIONS = {
    "Amherst": {"coords": (42.9784, -78.7998), "intersections": [
        "Transit Road (NY-78) & Maple Road",
        "Sheridan Drive (NY-324) & Niagara Falls Boulevard (US-62)",
        "Main Street (NY-5) & Eggert Road",
        "Millersport Highway (NY-263) & Sheridan Drive",
        "Maple Road & North Forest Road"
    ]},
    "Buffalo": {"coords": (42.8864, -78.8784), "intersections": [
        "Delaware Avenue (NY-384) & Niagara Square",
        "Main Street (NY-5) & Bailey Avenue (US-62)",
        "Elmwood Avenue & Hertel Avenue",
        "Kensington Avenue (NY-33) & Harlem Road",
        "Jefferson Avenue & Best Street"
    ]},
    "Cheektowaga": {"coords": (42.9034, -78.7548), "intersections": [
        "Walden Avenue & Union Road (NY-277)",
        "Genesee Street (NY-33) & Transit Road",
        "Harlem Road (NY-240) & Walden Avenue",
        "Union Road & George Urban Boulevard",
        "Dick Road & Genesee Street"
    ]},
    "Evans": {"coords": (42.6384, -79.0278), "intersections": [
        "US-20 (Southwestern Boulevard) & NY-5",
        "NY-5 & Sturgeon Point Road",
        "US-20 & Kennedy Avenue",
        "NY-5 & Derby Road",
        "US-20 & Bennett Road"
    ]},
    "Grand Island": {"coords": (43.0130, -78.9654), "intersections": [
        "Grand Island Boulevard (NY-324) & I-190 Ramps",
        "Staley Road & Grand Island Boulevard",
        "Baseline Road & Grand Island Boulevard",
        "Whitehaven Road & East River Road",
        "I-190 & West River Parkway"
    ]},
    "Hamburg": {"coords": (42.7159, -78.8295), "intersections": [
        "US-62 (South Park Avenue) & McKinley Parkway",
        "NY-5 & Camp Road",
        "US-20 & NY-75 (Camp Road)",
        "McKinley Parkway & Southwestern Boulevard (US-20)",
        "NY-5 & Sowles Road"
    ]},
    "Lancaster": {"coords": (42.9006, -78.6700), "intersections": [
        "Transit Road (NY-78) & Walden Avenue",
        "Broadway (US-20) & Bowen Road",
        "Transit Road & Genesee Street",
        "Aurora Street & Pavement Road",
        "Walden Avenue & Central Avenue"
    ]},
    "Orchard Park": {"coords": (42.7675, -78.7440), "intersections": [
        "US-20A & NY-240 (Orchard Park Road)",
        "US-219 & Milestrip Road",
        "NY-277 & Southwestern Boulevard (US-20)",
        "Big Tree Road (NY-20A) & California Road",
        "US-20 & Powers Road"
    ]},
    "Tonawanda": {"coords": (43.0203, -78.8803), "intersections": [
        "Niagara Falls Boulevard (US-62) & Sheridan Drive",
        "Delaware Avenue (NY-384) & Sheridan Drive",
        "Young Street & Colvin Boulevard",
        "Niagara Falls Boulevard & Ellicott Creek Road",
        "Kenmore Avenue & Military Road"
    ]},
    "West Seneca": {"coords": (42.8303, -78.7498), "intersections": [
        "Union Road (NY-277) & Seneca Street (NY-16)",
        "Transit Road (NY-78) & Clinton Street",
        "Ridge Road & Orchard Park Road",
        "Seneca Street & Harlem Road",
        "Union Road & Center Road"
    ]}
}

# Time period configurations
TIME_FILTERS = {
    "past_day": {"days": 1, "workdays": 1, "peak_hours": 8},
    "past_week": {"days": 7, "workdays": 5, "peak_hours": 8},
    "past_month": {"days": 30, "workdays": 22, "peak_hours": 8},
    "past_year": {"days": 365, "workdays": 250, "peak_hours": 8}
}

app = Flask(__name__)

def fetch_here_traffic_data(timeframe: str, lat: float, lon: float) -> Tuple[float, int]:
    """Fetch traffic data from HERE Traffic API."""
    url = f"{HERE_API_BASE_URL}?locationReferencing=shape&in=circle:{lat},{lon};r={RADIUS}&apiKey={HERE_API_KEY}"
    
    if timeframe != "realtime":
        logger.warning(f"Historical data ({timeframe}) not supported by HERE /v7/flow. Using real-time data instead.")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and data["results"]:
            result = data["results"][0]
            jam_factor = result.get("currentFlow", {}).get("jamFactor", 0)
            average_delay = jam_factor * 0.5
            total_vehicles = 8000
            
            if timeframe != "realtime":
                if timeframe == "past_day":
                    average_delay *= 1.1
                    total_vehicles = int(total_vehicles * 0.9)
                elif timeframe == "past_week":
                    average_delay *= 1.2
                    total_vehicles = int(total_vehicles * 0.8)
                elif timeframe == "past_month":
                    average_delay *= 1.3
                    total_vehicles = int(total_vehicles * 0.7)
                elif timeframe == "past_year":
                    average_delay *= 1.4
                    total_vehicles = int(total_vehicles * 0.6)
            
            return average_delay, total_vehicles
        else:
            logger.warning("No traffic data found in HERE API response. Using defaults.")
            return 2.0, 8000
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching HERE traffic data: {e}")
        return 2.0, 8000

def analyze_with_xai(town: str, traffic_data: Dict) -> str:
    """Analyze traffic data using xAI API."""
    if not traffic_data or not traffic_data["intersections"]:
        return "No traffic data available for analysis."

    data_str = f"Traffic Data for {town} (Timeframe: {traffic_data['timeframe']}):\n"
    for item in traffic_data["intersections"]:
        data_str += f"- Intersection: {item['name']}, Delay: {item['delay_minutes']} min/vehicle, Vehicles: {item['total_vehicles']}, Time Savings: ${item['time_savings_usd']}, Fuel Savings: ${item['fuel_savings_usd']}\n"

    prompt = f"Analyze the following traffic data for congestion trends and provide recommendations for traffic optimization:\n{data_str}"
    
    payload = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(XAI_API_URL, headers=XAI_HEADERS, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and result["choices"]:
            analysis = result["choices"][0]["message"]["content"]
            return analysis
        else:
            logger.warning("No analysis returned from xAI API.")
            return "Unable to generate analysis."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling xAI API: {e}")
        return f"Error analyzing data: {str(e)}"

def calculate_savings_per_intersection(intersection: str, period: str, lat: float, lon: float) -> Tuple[float, float, float, int]:
    """Calculate savings using HERE traffic data."""
    filter_config = TIME_FILTERS[period]
    start_date = CURRENT_DATE - timedelta(days=filter_config["days"])
    end_date = CURRENT_DATE

    base_delay, total_vehicles = fetch_here_traffic_data(period, lat, lon)

    weather_impact = 1 + (0.10 * 0.137 * (end_date - start_date).days / filter_config["days"])
    adjusted_delay = base_delay * weather_impact

    total_delay_minutes = total_vehicles * adjusted_delay
    saved_minutes = total_delay_minutes * AI_REDUCTION_PERCENT
    saved_hours = saved_minutes / 60
    time_savings_usd = saved_hours * HOURLY_WAGE
    fuel_savings_gallons = saved_minutes * FUEL_CONSUMPTION_MIN
    fuel_savings_usd = fuel_savings_gallons * FUEL_COST_PER_GALLON

    return time_savings_usd, fuel_savings_usd, adjusted_delay, total_vehicles

def analyze_towns(towns_data: Dict[str, Dict[str, any]], time_filter: str) -> Dict[str, Dict]:
    """Analyze towns using HERE traffic data and xAI."""
    results = {}
    for town, data in towns_data.items():
        lat, lon = data["coords"]
        town_results = {
            "timeframe": time_filter,
            "intersections": [],
            "total_time_savings": 0,
            "total_fuel_savings": 0,
            "xai_analysis": ""
        }
        for intersection in data["intersections"]:
            try:
                time_savings, fuel_savings, delay, total_vehicles = calculate_savings_per_intersection(
                    intersection, time_filter, lat, lon
                )
                town_results["intersections"].append({
                    "name": intersection,
                    "delay_minutes": round(delay, 2),
                    "total_vehicles": total_vehicles,
                    "time_savings_usd": round(time_savings, 2),
                    "fuel_savings_usd": round(fuel_savings, 2)
                })
                town_results["total_time_savings"] += time_savings
                town_results["total_fuel_savings"] += fuel_savings
            except Exception as e:
                logger.error(f"Error processing intersection {intersection}: {e}")
                continue
        
        # Analyze the town data with xAI
        town_results["xai_analysis"] = analyze_with_xai(town, town_results)
        results[town] = town_results
    return results

@app.route('/')
def index():
    filters = ["past_day", "past_week", "past_month", "past_year"]
    all_results = {}
    for filter_name in filters:
        results = analyze_towns(TOWNS_INTERSECTIONS, filter_name)
        all_results[filter_name] = results
        export_to_json(results, filter_name)
    
    return render_template('index.html', towns=TOWNS_INTERSECTIONS, filters=filters)

def display_results(results: Dict[str, Dict], time_filter: str) -> None:
    total_savings = 0
    print(f"Traffic Analysis for AI-Optimized Traffic Lights ({time_filter.replace('_', ' ').title()})\n")
    for town, data in results.items():
        print(f"Town: {town}")
        for intersection in data['intersections']:
            print(f"  Intersection: {intersection['name']}")
            print(f"    Delay: {intersection['delay_minutes']} minutes/vehicle")
            print(f"    Total Vehicles: {intersection['total_vehicles']:,}")
            print(f"    Time Savings: ${intersection['time_savings_usd']:,}")
            print(f"    Fuel Savings: ${intersection['fuel_savings_usd']:,}")
        town_total = data['total_time_savings'] + data['total_fuel_savings']
        print(f"  Town Total Savings: ${town_total:,.2f}")
        print(f"  xAI Analysis: {data['xai_analysis']}\n")
        total_savings += town_total
    print(f"Total Savings Across All Towns: ${total_savings:,.2f}")

def export_to_json(results: Dict[str, Dict], time_filter: str) -> None:
    filename = f"traffic_results_{time_filter}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results exported to {filename}")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)