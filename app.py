from fastapi import FastAPI, HTTPException, APIRouter
from schemas import ChatRequest,ChatResponse
from graph import run_travel_agent

router= APIRouter()

app = FastAPI(
    title='Nomad Travel Agent',
    description = 'LangGraph powered AI travel assistant',
    version='1.0.0'
)

@router.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response= await run_travel_agent(user_input=request.message,thread_id=request.thread_id)

        #PDF generated
        if response.get('pdf_path'):
            return ChatResponse(
                reply = 'pdf created successfully',
                pdf_path=response['pdf_path'],
                status='completed'
            )
        
        #normal conversation
        return ChatResponse(
            reply= response['messages'][-1].content,
            status='in_progress'
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error processing querry: {str(e)}'
        )


app.include_router(router, prefix='/travel_agent', tags=['travel_agent'])
@app.get('/')
async def home():
    '''Root endpoint with API information'''
    return {
        'messages': 'Welcome to NOMAD- AI powered travel assistant',
        'version':'1.0.0',
        'endpoints': {
            'message':'POST/travel_agent/chat',
            'health':'GET/health',
            'docs': 'GET/docs'
        }
    }

@app.get('/health')
async def health_check():
    '''Health check endpoint'''
    return {
        'status':'healthy',
        'service':" Nomad - AI powered travel assistant"
    }