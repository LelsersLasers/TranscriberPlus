#!/bin/bash

cd /home/millankumar/code/TranscriberPlus

docker build -t transcriberplus .

docker run -v $(pwd)/backend:/app/backend -p 3004:3004 transcriberplus
