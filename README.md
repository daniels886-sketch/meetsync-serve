services:
  - type: web
    name: meetsync-server
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn main:app
    envVars:
      - key: MONDAY_TOKEN
        sync: false
