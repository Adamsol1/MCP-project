# MCP Threat Intelligence
Bachelors project that explores the integration of AI in threat intelligence (TI) with the usage of Model Context Protocol (MCP). The system supports the user through the first four phases in the TI cycle, being Direction, Collection, Processing, and Analysis.

This project was developed in collaboratin with Telenor ASA and Storebrand Group.

## Library versions
This is the library versions used througout the project:
- Node.JS version 18
- Python version 3.11
- Poetry is used as packet manager in this project.


How to run:

### Create a .env file in the root folder with the following API keys:

GEMINI_API_KEY=<Gemini API key>
SERPER_API_KEY=<Serper API key>
OTX_API_KEY=<AlienVault OTX key>


## 2. Run the .install script to install all libaries and depencecies nessecary to run the project:

**(PowerShell):**
.\install.ps1

**(Bash)**
./install


## 3. Run the application:
Run all necessay systems from root folder with the following command:

- npm run dev

When the terminal prints "BARBOSA" the procjet is running succesfully. Please wait for the text to display.


The application is then avaiable at localhost:5173

Overview of all systems:

Frontend:
- Port: 5173
- Description : User interface

Backend:
- Port 8000
- Description : Application backend

Generation MCP:
- Port 8001
- Description: Server used for AI generation

Review MCP
- Port 8002
- Description: Server used for AI reviewing

Council MCP
- Port 8003
- Description: Server used for AI deliberation.

## Run test

## Backend:
Run the following command from the backend folder: poetry run pytest

## Frontend:
Run the following command from the Frontend folder: npm run test
