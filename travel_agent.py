import asyncio
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph,END,add_messages
from pydantic import BaseModel,Field
from datetime import datetime
from langchain.agents import create_agent
from typing import TypedDict, Annotated, Literal, List, Optional
from tools import currency_information_tool, flight_information_tool, hotel_information_tool
from prompt import PROXEY_AGENT_PROMPT, NOMAD_AGENT_PROMPT
from langgraph.checkpoint.memory import InMemorySaver
from uitlity import build_structured_prompt
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph,Spacer,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4
from pathlib import Path 
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor

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
     pdf_path: Optional[str]
     get_guide: bool = False
    

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
    get_guide: bool = Field(False, description='User wants guide or not')
    
    


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
    state['get_guide']= response.get_guide
    print(response.get_guide)
    return state

guide_agent=create_agent(
    model=llm,
    tools=[
        currency_information_tool,
        flight_information_tool,
        hotel_information_tool
    ],
    system_prompt="""You are a comprehensive travel guide agent.
Your responsibilities:
- Produce accurate, well-structured travel guides
- Decide when to call tools for factual accuracy
- Never expose raw tool output
- Never mention tools explicitly
- FOLLOW THE PROVIDED STRUCTURE STRICTLY
-['●', '☎', '$', '★','◆', '▣', '✈'] these are mendatory as prefix headings e.g [ ● Geography & City Bio ]
""",
    name="Comprehensive Travel Guide Agent"
)

async def travel_guide_node(state: travel_state) -> travel_state:

    # Unpack the dictionary to pass arguments correctly
    prompt = build_structured_prompt(
        destination=state["destination"],
        languages=state["languages"],
        currency=state["currency"],
        current_location=state['current_location'],
        trip_date=state['trip_date']
    )

    response = await guide_agent.ainvoke(
        {
            "messages": [HumanMessage(content=prompt)]
        }
    )
    state["itinerary"] = response["messages"][-1].content
    print(state['itinerary'])
    return state

#...................
#1st router function
#...................
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
        'trip_date': state.get('trip_date'),
        'get_guide': state.get('get_guide')
    }

    # Check if all required fields have values (not None and not empty)
    all_present = all(
        value is not None and value != "" and value != [] and value != False
        for value in required_fields.values()
    )

    if all_present :
        return "generate_guide"
    else:
        return "continue_conversation"

#..................
#pdf node function
#..................

async def pdf_generator(state : travel_state)->travel_state:
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    pdf_path = output_dir / "travel_guide.pdf"

    styles = getSampleStyleSheet()
    story = []

    if "TitleStyle" not in styles.byName:
        styles.add(ParagraphStyle(
            name="TitleStyle",
            fontSize=26,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=HexColor("#003876"),
        ))

    if "SubtitleStyle" not in styles.byName:
            styles.add(ParagraphStyle(
                name="SubtitleStyle",
                fontSize=18,
                leading=22,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=HexColor("#003876"),
                fontName="Helvetica-Bold"
            ))

    if "SectionHeader" not in styles.byName:
        styles.add(ParagraphStyle(
            name="SectionHeader",
            fontSize=16,
            leading=20,
            spaceBefore=20,
            spaceAfter=10,
            textColor=HexColor("#003876"),
            fontName="Helvetica-Bold",
        ))

    if "BodyText" not in styles.byName:
        styles.add(ParagraphStyle(
            name="BodyText",
            fontSize=11,
            leading=16,
            spaceAfter=8,
            textColor=HexColor("#0A0A0A"),
        ))

    # ---- TITLE ----
    story.append(Paragraph(
        f"Compherensive Travel Guide",
        styles["TitleStyle"]
    ))
    story.append(Paragraph(
        f"{state['current_location']}-->{state['destination']}",
        styles["SubtitleStyle"]
    ))
    story.append(Spacer(1, 20))

    # ---- ITINERARY SECTIONS (dynamic formatting) ----
    # List of emojis that indicate a section header
    section_indicators = ['●', '☎', '$', '★','◆', '▣', '✈']

    for line in state['itinerary'].split("\n"):
        if line.strip():
            # Check if the line starts with a section emoji
            is_section_header = False
            for emoji in section_indicators:
                if line.strip().startswith(emoji):
                    is_section_header = True
                    break

            if is_section_header:
                story.append(Paragraph(line, styles["SectionHeader"]))
            else:
                story.append(Paragraph(line, styles["BodyText"]))

    def add_page_number(canvas, doc):
      page_num_text = f"Page {doc.page}"
      canvas.setFont("Helvetica", 9)
      canvas.setFillColor(HexColor("#000000"))
      canvas.drawRightString(200 * 2.95, 20, page_num_text)
      # doc.build(story) was incorrectly placed here, removed to avoid infinite loop

    doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=A4,
    rightMargin=40,
    leftMargin=40,
    topMargin=50,
    bottomMargin=40,
    )

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    state["pdf_path"] = str(pdf_path)

    return state
graph=StateGraph(travel_state)

graph.add_node('nomad', conversation_node)
graph.add_node('proxey', proxey_node)
graph.add_node('travel_guide', travel_guide_node)
graph.add_node('pdf_generator', pdf_generator)

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
graph.add_edge('travel_guide','pdf_generator')
graph.add_edge('pdf_generator', END)

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
        if response.get('pdf_path'):
            print("\n" + "="*50)
            print("TRAVEL GUIDE GENERATED!")
            print("="*50)
            print('PDF Created Successfully!!')
            print("\n" + "="*50)

        else:
        # Continue conversation - show nomad's response
            result = response['messages'][-1]
            print(f"Nomad: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
'''
from IPython.display import Image, display

print(workflow.get_graph().draw_mermaid())
'''