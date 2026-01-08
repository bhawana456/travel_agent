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

def get_flight_data(current_country_code: str, current_city: str, destination: str) -> dict:
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": f"{current_city} to {destination} prices of flights",
        "gl": current_country_code,
        "departure_id": current_city,
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
def flight_information_tool(querry: str)->str:
    """Fetch the flight information for a given route from the search results. 
       This tool should be called EXACTLY ONCE per user request.
       Use ONLY the current_city specified by the user - do not make additional calls with other cities.
       Understand the results and suggest estimated flight prices and provide a google flights link.
       Only summarize information that matches the specified current_city and destination. 
       Ignore summary that does not hold these values.

    Args:
        current_country_code: The ISO country code of the starting location eg "IND"
        current_city: The starting city for the flight eg "Delhi, India"
        destination: The destination city for the flight eg "Paris, France"
    """
    flight_info = get_flight_data(current_country_code, current_city, destination)
    return flight_info
                 
#........................................
# 2nd tool currency_conversion tool
# .......................................
@tool
def exchange_rate(query: str) -> str:
  '''This tool is for getting exchange rates.'''
  pattern = re.search(r"(\d+\.?\d*)\s*([A-Z]{3})\s*(to|in)\s*([A-Z]{3})", query.upper())
  if pattern:
    amount, from_curr, _, to_curr = pattern.groups()
    url=f'https://v6.exchangerate-api.com/v6/4c8ecbac6f1c77d3acc5c706/pair/{from_curr}/{to_curr}'
    response=requests.get(url)
    data=response.json()
    rate=data['conversion_rate']
    if rate:
      converted=round(float(amount)*rate,2)
      return f'{amount} {from_curr} ≈ {converted} {to_curr}'
    return 'Currency not supported.'
  else:
      return 'Could not parse the currency exchange request. Please provide the amount and currencies in the format "AMOUNT CURRENCY_FROM to CURRENCY_TO".'

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