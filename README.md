

## Install dependencies

```bash
pip install flask psycopg2-binary python-dotenv
```

## Run PostgreSQL with Docker

```bash
docker run --name quiz-postgres -e POSTGRES_DB=quizdb -e POSTGRES_USER=quizuser -e POSTGRES_PASSWORD=quizpass -p 5432:5432 -d postgres:16
```

## Run the app

```bash
python app.py
```

Open http://127.0.0.1:5000

## View saved results in PostgreSQL


```bash
docker exec -it quiz-postgres psql -U quizuser -d quizdb
```

Then run:

```sql
SELECT * FROM quiz_results ORDER BY submitted_at DESC;
```
