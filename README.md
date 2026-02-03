# Eye Budget

sqlite db:
mymoney.mmdb: C:\Users\Pawel.Swierblewski\Nextcloud\Budżet domowy\MyMoney NET

Activate Python virtual environment:
```
source venv/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt
```

## Docker Usage

Build the Docker image:

```
docker build -t eye-budget .
```

Run the container:

```
docker run -p 8000:8000 -v $(pwd)/input:/app/input -v $(pwd)/sqlite:/app/sqlite eye-budget
```

The FastAPI app will be available at http://localhost:8000
