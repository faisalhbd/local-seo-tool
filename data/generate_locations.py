"""
US Locations Database - States, Cities/Towns, Zip Codes
Covers all 48 contiguous states (Excluding Alaska & Hawaii per business requirement)
Generated from SimpleMaps US Cities Database
"""

import csv
import os

# State abbreviations for 48 contiguous states (excluding AK and HI)
CONTIGUOUS_STATES = {
    'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'ID', 'IL', 'IN', 
    'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 
    'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 
    'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
}

# Use the existing local CSV file
csv_path = r'c:\Users\Faisal\Downloads\local_seo_tool update\data\uscities.csv'

# Process CSV and build US_LOCATIONS dictionary
US_LOCATIONS = {}
cities_by_state = {}

print("Processing CSV data...")
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        state_id = row.get('state_id', '').upper()
        state_name = row.get('state_name', '')
        
        # Only include 48 contiguous states
        if state_id not in CONTIGUOUS_STATES:
            continue
        
        city_name = row.get('city', '').strip()
        first_zip = row.get('zip', '').strip()
        county_name = row.get('county_name', '')
        
        if not first_zip or not city_name:
            continue
        
        if state_name not in cities_by_state:
            cities_by_state[state_name] = {
                'abbreviation': state_id,
                'cities': []
            }
        
        cities_by_state[state_name]['cities'].append({
            'name': city_name,
            'zip': first_zip,
            'county': county_name
        })

# Sort states alphabetically
state_abbr_map = {
    'Alabama': 'AL', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL',
    'Georgia': 'GA', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN',
    'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
    'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI',
    'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT',
    'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
    'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN',
    'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
    'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

for state_name in sorted(cities_by_state.keys()):
    # Sort cities by name
    cities_by_state[state_name]['cities'] = sorted(
        cities_by_state[state_name]['cities'],
        key=lambda x: x['name']
    )
    US_LOCATIONS[state_name] = cities_by_state[state_name]

# Output the Python code
print("\nGenerating Python code...")
output_code = '"""\nUS Locations Database - States, Cities/Towns, Zip Codes\nCovers all 48 contiguous states (Excluding Alaska & Hawaii per business requirement)\nAll incorporated cities\n"""\n\nUS_LOCATIONS = '

# Format the dictionary as Python code
import json

def dict_to_python(d, indent=0):
    """Convert dict to pretty Python dict syntax"""
    result = "{\n"
    items = list(d.items())
    for i, (key, value) in enumerate(items):
        result += " " * (indent + 4) + f'"{key}": ' + "{\n"
        for k, v in value.items():
            if k == "cities":
                result += " " * (indent + 8) + f'"{k}": [\n'
                for j, city in enumerate(v):
                    result += " " * (indent + 12) + "{"
                    result += f'"name": "{city["name"]}", "zip": "{city["zip"]}", "county": "{city["county"]}"'
                    result += "}"
                    if j < len(v) - 1:
                        result += ","
                    result += "\n"
                result += " " * (indent + 8) + "],\n"
            else:
                result += " " * (indent + 8) + f'"{k}": "{v}",\n'
        result = result.rstrip(',\n') + "\n"
        result += " " * (indent + 4) + "}"
        if i < len(items) - 1:
            result += ","
        result += "\n"
    result += " " * indent + "}"
    return result

output_code += dict_to_python(US_LOCATIONS)

# Write to file
output_path = r'c:\Users\Faisal\Downloads\local_seo_tool update\data\locations_new.py'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(output_code)

print(f"Generated code written to {output_path}")
print(f"\nTotal states: {len(US_LOCATIONS)}")
total_cities = sum(len(state['cities']) for state in US_LOCATIONS.values())
print(f"Total cities: {total_cities}")
print(f"Sample state: {list(US_LOCATIONS.keys())[0]}")
print(f"Number of cities in sample state: {len(US_LOCATIONS[list(US_LOCATIONS.keys())[0]]['cities'])}")