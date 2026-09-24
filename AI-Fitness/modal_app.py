import modal 
from backend.main import app as web_app 
 
app = modal.App("fitquest-backend") 
 
image = modal.Image.debian_slim(python_version="3.12").pip_install_from_requirements("requirements.txt") 
 
@app.function(image=image) 
@modal.asgi_app() 
def serve(): 
    return web_app 
