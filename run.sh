#!/bin/bash
export DATABASE_URL=postgres:///inspection_db?host=/tmp
./venv/bin/python manage.py runserver 0.0.0.0:8000
