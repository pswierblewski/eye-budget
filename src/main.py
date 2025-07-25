from src.app import App
from fastapi import FastAPI

app = FastAPI()

@app.post("/receipts/process")
def process_receipts():
    my_app = App()
    my_app.run()
    my_app.dispose()