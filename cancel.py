import requests

def cancel_transcription(job_id, base_url="https://transcriber-api-goao.onrender.com/"):
    url = f"{base_url}/cancel_transcription/{job_id}"
    response = requests.post(url)
    
    if response.status_code == 200:
        print(f"Cancellation request sent for job {job_id}")
        print(response.json())
    else:
        print(f"Failed to cancel job {job_id}")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    job_id = input("Enter the job ID to cancel: ")
    cancel_transcription(job_id)