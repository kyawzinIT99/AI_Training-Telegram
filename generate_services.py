import json
import os

# Define the structure of your services and pricing here.
# You can easily edit this list anytime you want to update prices.
SERVICES = [
    {
        "service_name": "AI Consultation (1 Hour Google Meet)",
        "price_usd": 150,
        "description": "A deep dive into your business to identify AI automation opportunities."
    },
    {
        "service_name": "Custom AI Telegram/Discord Bot",
        "price_usd": 500,
        "description": "A fully autonomous, cost-optimized AI bot integrated with your data."
    },
    {
        "service_name": "Cloud Infrastructure Setup",
        "price_usd": 800,
        "description": "Scalable cloud architecture deployment (AWS, GCP, or Modal)."
    },
    {
        "service_name": "Enterprise Network Automation",
        "price_usd": 1200,
        "description": "Automated network provisioning and monitoring solutions."
    }
]

def generate_json():
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    file_path = "data/services.json"
    
    # Write the Python list to a JSON file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(SERVICES, f, indent=4)
        
    print(f"✅ Successfully generated {file_path}")
    print("You can edit 'generate_services.py' anytime and run it again to update your prices.")

if __name__ == "__main__":
    generate_json()
