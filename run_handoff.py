"""Run the marketplace handoff API locally."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("marketplace_cost.handoff_service:app", host="127.0.0.1", port=8000)

