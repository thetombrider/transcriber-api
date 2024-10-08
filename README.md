# Transcriber API

This is a simple transcriber API that accepts audio files or URLs and returns transcriptions.

## Deployment on Render

1. Fork this repository to your GitHub account.
2. Create a new Web Service on Render.
3. Connect your GitHub repository to Render.
4. Select the branch you want to deploy.
5. Set the Environment to "Docker".
6. Click "Create Web Service".

The API will be deployed and accessible via the URL provided by Render.

Note: The OpenAI API key should be provided by the client in each request to the API.

## API Endpoints

- POST /transcribe/file: Upload an audio file for transcription
- POST /transcribe/url: Provide a URL to an audio file for transcription

For more details, refer to the API documentation.#   t r a n s c r i b e r - a p i 
 
 
