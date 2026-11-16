@echo off
echo ===================================================
echo Starting Automated Multi-Platform Posting System...
echo ===================================================
echo Swagger Documentation: http://localhost:4000/docs
echo ===================================================
python -m uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
pause

