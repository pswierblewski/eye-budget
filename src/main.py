from app import App
from fastapi import FastAPI

fapp = FastAPI()

@fapp.post("/receipts/process")
def process_receipts():
    app = App()
    app.run()
    app.dispose()