@echo off

echo Mock server baslatiliyor...
start cmd /k "cd /d C:\Users\user\Downloads\YGA\ai-plant-health-system\ai-plant-health-system\mock-server && npm run dev"

echo Frontend baslatiliyor...
start cmd /k "cd /d C:\Users\user\Downloads\YGA\ai-plant-health-system\ai-plant-health-system\frontend && npm run dev"

echo Tum servisler baslatildi.
pause