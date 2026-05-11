# Boilerplate App

A minimal full-stack starter with a React frontend, a Python FastAPI backend, and MongoDB connectivity.

## What it shows
- Frontend active
- Backend connected
- Database connected

## Structure
- `frontend/` - React + Vite UI
- `backend/` - FastAPI API and MongoDB health check

## Environment
- `FRONTEND_PORT` controls the Vite dev server port
- `BACKEND_PORT` controls the FastAPI server port
- `MONGODB_URI` controls the database connection

## Setup
1. Run `setup.bat` from the repository root.
2. Make sure `.env` contains `MONGODB_URI`, `FRONTEND_PORT`, and `BACKEND_PORT`.

## Run
Run `start.bat` from the repository root.

The frontend proxy automatically points to the backend port from `.env`.
