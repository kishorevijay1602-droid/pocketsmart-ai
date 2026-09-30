# Project Documentation

## Project Title

PocketSmart AI Budget Planner

## Project Overview

PocketSmart AI is an AI-powered budget planning application designed to help users make informed decisions for everyday lifestyle requirements.

The application provides personalized recommendations for:

- Home interiors
- Party planning
- Jewelry selection

## Problem

Users often spend significant time searching for suitable products and services within a fixed budget.

PocketSmart AI simplifies this process by using generative AI to understand user requirements and provide personalized recommendations.

## Solution

The application accepts user requirements such as budget, preferences, and images where applicable.

The backend processes the information and uses Gemini Generative AI to generate context-aware recommendations.

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn

### Frontend

- HTML
- CSS
- Jinja2

### AI

- Gemini Generative AI

### Development Tools

- Visual Studio Code
- Git
- GitHub

### Deployment

- Render

## Main Features

### User Authentication

Users can register, log in, maintain a session, and log out.

### Home Planner

Generates budget-based home interior recommendations.

### Party Planner

Generates budget-based party planning recommendations.

### Jewelry Planner

Generates budget-based jewelry recommendations and supports image input.

### Recommendation History

Users can view their previously generated recommendations.

### Dashboard

Provides access to the application's main planning features.

## Application Workflow

1. User opens PocketSmart AI.
2. User registers or logs in.
3. User accesses the dashboard.
4. User selects a planner.
5. User enters budget and requirements.
6. The backend sends the relevant information to Gemini AI.
7. Gemini generates recommendations.
8. Recommendations are displayed to the user.
9. The recommendation can be stored in history.
10. The user can view the full recommendation later.

## Security

Sensitive API credentials are stored using environment variables.

Authentication and session handling are implemented in the FastAPI backend.

## Testing

The application was tested for:

- Registration
- Login
- Session handling
- Home Planner
- Party Planner
- Jewelry Planner
- Image upload
- Gemini AI integration
- Recommendation history
- Full recommendation viewing
- Logout
- Deployment

## Deployment

The application was deployed as a web service and tested through its public URL.

## Future Enhancements

Possible future improvements include:

- Permanent database storage
- More planning categories
- Advanced recommendation filtering
- User preference profiles
- Improved analytics
- Additional external service integrations

## Conclusion

PocketSmart AI demonstrates how generative AI and modern web technologies can be combined to create a practical budget planning assistant.

The application provides users with fast, personalized recommendations while simplifying everyday planning and decision-making.