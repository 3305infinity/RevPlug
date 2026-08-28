import uvicorn

if __name__ == "__main__":
    uvicorn.run("payment_recovery.service:app", host="0.0.0.0", port=8000)
