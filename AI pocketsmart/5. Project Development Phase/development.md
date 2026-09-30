# Project Development Phase

## Project Title

PocketSmart AI Budget Planner

## Development Overview

PocketSmart AI was developed as a web-based AI budget planning application using Python and FastAPI.

The application combines a FastAPI backend, Jinja2 templates, HTML, CSS, and Gemini Generative AI to provide personalized recommendations.

## Backend Development

The FastAPI backend was developed to handle:

- User registration
- User login
- Session management
- Protected routes
- Planner form processing
- Gemini AI requests
- Image uploads
- Recommendation history
- Dashboard
- Logout functionality

## Frontend Development

The frontend was developed using Jinja2 templates, HTML, and CSS.

Implemented pages include:

- Home page
- Login page
- Registration page
- Dashboard
- Home Planner
- Party Planner
- Jewelry Planner
- Recommendation result pages
- History page
- History detail page

## AI Development

Gemini Generative AI was integrated into the application to generate context-aware recommendations.

The AI processes:

- User budget
- User preferences
- Planning requirements
- Jewelry images when provided

## Home Planner

The Home Planner generates recommendations for home interior requirements based on the user's budget and preferences.

## Party Planner

The Party Planner generates recommendations for party-related requirements based on the user's budget and event details.

## Jewelry Planner

The Jewelry Planner generates jewelry recommendations based on the user's budget and preferences.

It also supports image input for AI-assisted jewelry recommendations.

## Recommendation History

Generated recommendations are stored for the active user session.

Users can view:

- Planner type
- Budget
- Requirements
- Generated recommendation
- Full recommendation details

## External Links

The application can generate relevant external shopping and service links for users where applicable.

## Environment Configuration

Sensitive API credentials are stored using environment variables.

The Gemini API key is not hard-coded into the application source code.

## Deployment

The application was deployed as a web service.

The source code is maintained in GitHub and the application was tested using the deployed public URL.

## Development Result

The main PocketSmart AI modules were successfully implemented and tested:

- Authentication
- Home Planner
- Party Planner
- Jewelry Planner
- Gemini AI integration
- Image-based recommendation
- Recommendation history
- Dashboard
- Deployment