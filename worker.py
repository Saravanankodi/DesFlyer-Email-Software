from app import app
from services.campaign_service import run_worker


if __name__ == "__main__":
    run_worker(app)
