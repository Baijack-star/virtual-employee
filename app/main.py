from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from datetime import datetime

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Virtual Employee Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 20px; background: #f0f0f0; border-radius: 5px; margin: 20px 0; }
            .log { background: #000; color: #0f0; padding: 20px; border-radius: 5px; height: 300px; overflow-y: auto; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Virtual Employee Dashboard</h1>
            <div class="status">
                <h2>System Status</h2>
                <p>Status: <span id="status">Connecting...</span></p>
                <p>Last Update: <span id="lastUpdate">-</span></p>
            </div>
            <div class="log" id="log"></div>
        </div>
        
        <script>
            const eventSource = new EventSource('/events');
            const statusElement = document.getElementById('status');
            const lastUpdateElement = document.getElementById('lastUpdate');
            const logElement = document.getElementById('log');
            
            eventSource.onopen = function(event) {
                statusElement.textContent = 'Connected';
                statusElement.style.color = 'green';
                addLog('Connected to server');
            };
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                lastUpdateElement.textContent = new Date().toLocaleTimeString();
                addLog(`Received: ${data.message}`);
            };
            
            eventSource.onerror = function(event) {
                statusElement.textContent = 'Disconnected';
                statusElement.style.color = 'red';
                addLog('Connection error');
            };
            
            function addLog(message) {
                const timestamp = new Date().toLocaleTimeString();
                logElement.innerHTML += `<div>[${timestamp}] ${message}</div>`;
                logElement.scrollTop = logElement.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.get("/events")
async def stream_events():
    async def event_generator():
        counter = 0
        while True:
            counter += 1
            data = {
                "message": f"System heartbeat #{counter}",
                "timestamp": datetime.now().isoformat(),
                "counter": counter
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)