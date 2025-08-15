# NEXTCOIN GNN Matchmaking Engine

**Note:** Due to a Non-Disclosure Agreement (NDA) and the fact that this code is currently being deployed and actively used by the startup **NEXTCOIN**, the source code cannot be shared or open-sourced at this time. However, I am happy to demonstrate and walk through the code in person or via a private session.

## Project Overview

The NEXTCOIN GNN Matchmaking Engine is a backend system designed to connect project owners with professionals efficiently and accurately. The engine leverages a **Graph Neural Network (GNN)** to provide personalized matchmaking based on multiple factors, including skills, interests, and reputation.

## Functionality

- **Project Submission:** Project owners submit a project through the web platform, including:
  - Project description
  - Difficulty level
  - Remuneration
  - Due date
  - Required skills (e.g., Python, Excel)

- **User Matching:** The GNN engine processes this input along with data from all registered users in the database, considering:
  - Relevant skills
  - Interests
  - Reputation scores

- **Recommendation Ranking:** Matches are ranked based on compatibility scores calculated by the GNN, providing project owners with the most suitable candidates.

- **Filtering & Scoring:** The system filters out users who do not meet skill requirements and ranks candidates according to their relevance and reliability.

## Technical Details

- **Backend Framework:** Flask API
- **Database:** PostgreSQL hosted on AWS
- **Machine Learning:** Graph Neural Network for matchmaking and recommendation ranking
- **Features Implemented:**
  - Reputation-based scoring
  - Skill and interest-based filtering
  - Real-time recommendation ranking
  - Scalable RESTful API for integration with the web platform

## Role & Contribution

I co-developed the backend of the platform, implementing secure API routes, database interactions, and the integration of the GNN matchmaking algorithm. I was responsible for ensuring reliability, scalability, and accurate matching of users to projects.

## Note on Access

While the code is not publicly available due to deployment and NDA constraints, I am happy to provide a detailed walkthrough of the system, including:
- Backend architecture
- API endpoints
- Database schema
- Matchmaking algorithm logic

---
