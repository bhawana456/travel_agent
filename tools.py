from langchain_core.tools import tool
from dotenv import load_dotenv
import json
import requests
import re
import os


load_dotenv()


serper_key=os.getenv('SERP_API_KEY')

#........................................
# 1st tool flight tool
# .......................................

def extract_flight_info(response_json: dict) -> str:
    summary = []
    link_summary = ''
    organic_results = response_json.get("organic")
    if organic_results:
        for result in organic_results:
            link = result.get("link", "")
            if link_summary == '' and link.startswith("https://www.google.com/travel/flights"):
                  link_summary = f"Get flight details from Google Flights: {link}"

            snippet = result.get("snippet")
            if snippet:
                summary.append(f"{snippet}")
                
    summary.append(link_summary) 
    return "\n\n".join(summary)

def get_flight_data(current_location: str, destination: str) -> dict:
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": f"{current_location} to {destination} prices of flights",
        #"gl": current_country_code,
        "departure_id": current_location,
        "arrival_id": destination,
    })
    headers = {
        'X-API-KEY': serper_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    summary = extract_flight_info(response.json())
    
    return summary
@tool
def flight_information_tool(current_location: str, destination:str)->str:
    """Fetch the flight information for a given route from the search results. 
       This tool should be called EXACTLY ONCE per user request.
       Use ONLY the current_city specified by the user - do not make additional calls with other cities.
       Understand the results and suggest estimated flight prices and provide a google flights link.
       Only summarize information that matches the specified current_city and destination. 
       Ignore summary that does not hold these values.

    Args:
        current_location: The starting city for the flight eg "Delhi, India"
        destination: The destination city for the flight eg "Paris, France"
    """
    flight_info = get_flight_data(current_location, destination)
    return flight_info
                 
#........................................
#2nd tool currency tool
# ....................................... 

def extract_currency_info(response_json: dict)-> str:
   summary = []
   organic_results = response_json.get("organic")
   if organic_results:
        for result in organic_results:
            snippet = result.get("snippet")
            if snippet:
                summary.append(f"{snippet}")

        return "\n\n".join(summary)

def get_currency_data(currency: str, destination_currency: str) -> str:
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": f"1 {currency} to {destination_currency} exchange rate"
    })
    headers = {
        'X-API-KEY': serper_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    summary = extract_currency_info(response.json())
    
    return summary

@tool
def currency_information_tool(currency: str, destination_currency: str) -> str:
    """Fetch the exchange rate from one currency to another.
       This tool should be called EXACTLY ONCE per user request.
       Use ONLY the currency specified by the user - do not make additional calls with other currencies.
       Understand the results and suggest exchange rates
       Only summarize information that matches the specified currency and destination_currency. 
       Ignore summary that does not hold these values.

    Args:
        currency: The user's currency for the exchange rate eg "USD"
        destination_currency: The destination currency for the exchange rate eg "EUR"
    """

    summary = get_currency_data(currency, destination_currency)
    return summary

#........................................
#2nd tool hotel information tool
# ....................................... 
def extract_hotel_info(response_json: dict)-> str:
   summary = []
   organic_results = response_json.get("organic")
   if organic_results:
        for result in organic_results:
            snippet = result.get("snippet")
            if snippet:
                summary.append(f"{snippet}")

        return "\n\n".join(summary)
   
def get_hotel_data(destination: str) -> str:
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": f"Afforfable hotels in {destination} with good ratings"
    })
    headers = {
        'X-API-KEY': serper_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    summary = extract_hotel_info(response.json())
    
    return summary
   
@tool
def hotel_information_tool(destination: str) -> str:
    """Fetch the available hotels from defined destination.
       This tool should be called EXACTLY ONCE per user request.
       Use ONLY the currency specified by the user - do not make additional calls with other currencies.
       Understand the results and suggest good accomodation as per rating 
       Only summarize information that matches the destination. 
       Ignore summary that does not hold these values.

    Args:
        destination: The destination city for the hotel eg "Paris, France".
    """

    summary = get_hotel_data(destination)
    return summary
