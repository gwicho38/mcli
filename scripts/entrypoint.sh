#!/bin/bash
set -e

# ML System Docker Entrypoint Script

# Function to wait for database
wait_for_db() {
    echo "Waiting for database connection..."
    while ! pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-ml_user}; do
        echo "Database not ready, waiting..."
        sleep 2
    done
    echo "Database is ready!"
}

# Function to run migrations
run_migrations() {
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations completed!"
}

# Function to initialize ML models
init_models() {
    echo "Initializing ML models..."
    python -c "
from mcli.ml.models import initialize_models
initialize_models()
print('Models initialized successfully!')
    " || echo "Model initialization skipped (optional)"
}

# Main entrypoint logic
case "$1" in
    serve)
        wait_for_db
        run_migrations
        init_models
        echo "Starting ML API server..."
        exec uvicorn mcli.ml.mlops.model_serving:app \
            --host 0.0.0.0 \
            --port ${API_PORT:-8000} \
            --workers ${API_WORKERS:-4}
        ;;

    train)
        wait_for_db
        echo "Starting model training..."
        exec python -m mcli.ml.cli train "${@:2}"
        ;;

    backtest)
        wait_for_db
        echo "Starting backtesting..."
        exec python -m mcli.ml.cli backtest "${@:2}"
        ;;

    worker)
        wait_for_db
        echo "Starting background worker..."
        exec celery -A mcli.ml.tasks worker \
            --loglevel=${LOG_LEVEL:-info} \
            --concurrency=${WORKER_CONCURRENCY:-4}
        ;;

    scheduler)
        wait_for_db
        echo "Starting task scheduler..."
        exec celery -A mcli.ml.tasks beat \
            --loglevel=${LOG_LEVEL:-info}
        ;;

    migrate)
        wait_for_db
        run_migrations
        ;;

    shell)
        wait_for_db
        echo "Starting Python shell..."
        exec python
        ;;

    bash)
        exec /bin/bash "${@:2}"
        ;;

    *)
        echo "Usage: $0 {serve|train|backtest|worker|scheduler|migrate|shell|bash}"
        exit 1
        ;;
esac