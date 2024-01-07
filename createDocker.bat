pip freeze > requirements.txt
docker build -t wetter2mqtt -f Dockerfile .
docker tag wetter2mqtt:latest docker.diskstation/wetter2mqtt
docker push docker.diskstation/wetter2mqtt:latest