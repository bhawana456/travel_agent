import asyncio
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph,END,add_messages
from pydantic import BaseModel,Field
from datetime import datetime
from langchain.agents import create_agent
from typing import TypedDict, Annotated, Literal, List, Optional
from tools import currency_information_tool, flight_information_tool
from prompt import PROXEY_AGENT_PROMPT, NOMAD_AGENT_PROMPT
from langgraph.checkpoint.memory import InMemorySaver
from uitlity import build_structured_prompt
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()
groq_key = os.getenv('GROQ_API_KEY')
llm= ChatGroq(api_key=groq_key, model="llama-3.3-70b-versatile",temperature=0.5)

memory= InMemorySaver()

#................
#define state
#................
class travel_state(TypedDict):
     messages: Annotated[List[BaseMessage], add_messages]
     name: Optional[str]
     destination: Optional[str]
     current_location: Optional[str]
     languages: Optional[List[str]]
     currency: Optional[str]
     trip_date: Optional[str]
     itinerary: Optional[str]

#.....................
#information collector node
#.....................
nomad_agent=create_agent(
        model=llm,
        system_prompt=NOMAD_AGENT_PROMPT,
        name="Nomad",
        checkpointer=InMemorySaver()
    )

async def conversation_node(state: travel_state)->travel_state:
    messages_history = state['messages']

    response=await nomad_agent.ainvoke(
        {'messages': messages_history},
        config={
            "configurable": {
                "thread_id": "1" 
            }
        }
    )
    state['messages'].append(AIMessage(content=response['messages'][-1].content))
    
    return state

#................
#proxey agent 
#................
class TourRequestData(BaseModel):
    
    name: Optional[str] = Field(None, description="The traveler's name")
    destination: Optional[str] = Field(None,description="The trip destination")
    current_location : Optional[str]=Field(None,description="user's trip destination")
    languages: Optional[List[str]] = Field(None, description="List of languages of the traveler")
    currency: Optional[str] = Field (None, description='The currency of traveler')
    trip_date: Optional[str] = Field(None, description='The trip date')
    


async def proxey_node(state: travel_state)-> travel_state:
    # Correctly concatenate the system prompt with the list of messages
    messages=[
        SystemMessage(content= PROXEY_AGENT_PROMPT),
    ] + state['messages']

    response= await llm.with_structured_output(TourRequestData).ainvoke(messages)
    
    state['name']=response.name
    state['destination']=response.destination
    state['current_location']=response.current_location 
    state['languages']=response.languages
    state['currency']=response.currency
    state['trip_date']=response.trip_date if response.trip_date is not None else datetime.now().strftime("%Y-%m-%d")

    return state

guide_agent=create_agent(
    model=llm,
    tools=[
        currency_information_tool,
        flight_information_tool,
        #hotel_information_tool
    ],
    system_prompt="""You are a comprehensive travel guide agent.
Your responsibilities:
- Produce accurate, well-structured travel guides
- Decide when to call tools for factual accuracy
- Never expose raw tool output
- Never mention tools explicitly
- Follow the provided structure strictly
""",
    name="Comprehensive Travel Guide Agent"
)

async def travel_guide_node(state: travel_state) -> travel_state:

    # Unpack the dictionary to pass arguments correctly
    prompt = build_structured_prompt(
        destination=state["destination"],
        languages=state["languages"],
        currency=state["currency"]
    )

    response = await guide_agent.ainvoke(
        {
            "messages": [HumanMessage(content=prompt)]
        }
    )
    print(response)
    state["itinerary"] = response["messages"][-1].content

    return state

#................
#router function
#................
def should_continue(state: travel_state) -> Literal["continue_conversation", "generate_guide"]:
    """
    Determines if we have all required information to generate the travel guide.
    If any required field is missing, continue the conversation.
    Otherwise, proceed to generate the guide.
    """
    required_fields = {
        'destination': state.get('destination'),
        'languages': state.get('languages'),
        'currency': state.get('currency'),
        'current_location': state.get('current_location'),
        'trip_date': state.get('trip_date')
    }

    # Check if all required fields have values (not None and not empty)
    all_present = all(
        value is not None and value != "" and value != []
        for value in required_fields.values()
    )

    if all_present:
        return "generate_guide"
    else:
        return "continue_conversation"

graph=StateGraph(travel_state)

graph.add_node('nomad', conversation_node)
graph.add_node('proxey', proxey_node)
graph.add_node('travel_guide', travel_guide_node)

graph.set_entry_point('nomad')

# Always extract information after conversation
graph.add_edge('nomad', 'proxey')

# Add conditional routing after information extraction
graph.add_conditional_edges(
    'proxey',
    should_continue,
    {
        "continue_conversation": END,  # Return to user for more input
        "generate_guide": 'travel_guide'     # Proceed to generate guide
    }
)

graph.add_edge('travel_guide', END)

workflow=graph.compile(checkpointer=memory)

async def main():
    print("** Welcome! I'm Nomad, your travel assistant. Let's plan your trip! **\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Nomad: Goodbye! Thanks for chatting.")
            break

        # Invoke the workflow with the user's input
        response = await workflow.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={
                "configurable": {
                    "thread_id": "1"
                }
            }
        )

        # Check if travel guide was generated (all info collected)
        if response.get('itinerary'):
            print("\n" + "="*50)
            print("TRAVEL GUIDE GENERATED!")
            print("="*50)
            print(response['itinerary'])
            print("\n" + "="*50)
            break  # End conversation after guide is generated
        else:
            # Continue conversation - show nomad's response
            result = response['messages'][-1]
            print(f"Nomad: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())