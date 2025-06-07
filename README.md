# Orchids Website Cloning Challenge

A web application that can clone any website by analyzing its design and structure using Browserbase SDK with Playwright for scraping and Gemini 1.5 Pro for HTML generation.

## Features

- Website URL input interface
- Cloud-based website scraping using Browserbase SDK with Playwright
- AI-powered website cloning using Gemini 1.5 Pro
- Live preview of the cloned website
- Status monitoring during the cloning process

## Tech Stack

- **Frontend**: Next.js with TypeScript
- **Backend**: Python FastAPI
- **Web Scraping**: Browserbase SDK with Playwright (cloud-based browser solution)
- **AI Model**: Google's Gemini 1.5 Pro

## Prerequisites

Before running the application, you'll need:

1. A Browserbase API key and project ID (sign up at https://browserbase.io/)
2. A Google API key with access to Gemini 1.5 Pro (https://ai.google.dev/)

## Setup Instructions

### Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```
BROWSERBASE_API_KEY=your_browserbase_api_key_here
BROWSERBASE_PROJECT_ID=your_browserbase_project_id_here
GOOGLE_API_KEY=your_google_api_key_here
```

### Backend

The backend is built with FastAPI and handles website scraping and AI-based cloning.

#### Installation

To install the backend dependencies, run the following command in the backend project directory:

```bash
pip install -r requirements.txt
```

#### Running the Backend

To run the backend development server, use the following command:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Frontend

The frontend is built with Next.js and TypeScript.

#### Installation

To install the frontend dependencies, navigate to the frontend project directory and run:

```bash
npm install
```

#### Running the Frontend

To start the frontend development server, run:

```bash
npm run dev
```

## How It Works

1. **Website Scraping**: The application uses Browserbase SDK with Playwright to capture a website's structure, styles, and visual elements.

2. **Data Processing**: The scraped information is processed and organized to extract design patterns, color schemes, typography, and layout structures.

3. **AI Generation**: Gemini 1.5 Pro generates HTML code that replicates the original website's appearance.

4. **Preview and Download**: The cloned website is displayed in a preview iframe and can be viewed directly.

## Implementation Details

- **Cloud-based Scraping**: Browserbase SDK with Playwright is used instead of local browser instances for better reliability and scalability.
- **Asynchronous Processing**: Background tasks handle the scraping and generation processes to keep the UI responsive.
- **Streaming Updates**: Status updates are provided throughout the cloning process.
