# Project Design Phase

## 1. System Architecture

PocketSmart AI follows a web-based client-server architecture.

The main components are:

1. User Interface
2. FastAPI Backend
3. Gemini AI Service
4. Recommendation History
5. External Shopping and Service Links

## 2. Application Flow

User
→ Registration/Login
→ Dashboard
→ Select Planner
→ Enter Budget and Preferences
→ FastAPI Backend
→ Gemini AI
→ AI Recommendation
→ Display Result
→ Save Recommendation History

## 3. Home Planner Flow

User enters:

- Budget
- Home requirements
- Preferences

The backend sends the relevant information to Gemini AI.

Gemini generates suitable home interior recommendations.

The recommendations are displayed to the user and stored in recommendation history.

## 4. Party Planner Flow

User enters:

- Party budget
- Party type
- Number of people
- Requirements

The backend processes the information using Gemini AI.

The generated party planning recommendations are displayed to the user.

## 5. Jewelry Planner Flow

User enters:

- Jewelry budget
- Jewelry requirements
- Preferences
- Optional image

The uploaded image can be processed as part of the AI request.

Gemini generates jewelry-related recommendations based on the provided information.

## 6. Backend Design

The backend is implemented using FastAPI.

Main responsibilities:

- Routing
- User authentication
- Session management
- Form processing
- File upload handling
- Gemini AI integration
- Recommendation history
- HTML template rendering

## 7. Frontend Design

The frontend uses:

- HTML
- CSS
- Jinja2 templates
- JavaScript where required

The interface provides pages for:

- Home
- Login
- Registration
- Dashboard
- Home Planner
- Party Planner
- Jewelry Planner
- Recommendation Results
- Recommendation History

## 8. AI Integration

Gemini Generative AI is used to process user requirements and generate personalized recommendations.

The backend sends structured user information to the AI model and receives the generated recommendation.

## 9. Data Flow

User Input
→ FastAPI
→ Validation and Processing
→ Gemini AI
→ Generated Recommendation
→ Result Page
→ Recommendation History

## 10. Security Design

The application uses session-based authentication to protect user-specific pages.

Protected features include:

- Dashboard
- Recommendation History
- Full Recommendation Details
- Logout/session management

## 11. Deployment Design

The application can be deployed as a web service using:

- GitHub for source-code management
- Render for application hosting
- Environment variables for sensitive API credentials