#!/bin/bash

cd /home/millankumar/code/TranscriberPlus

cd frontend
npm install
npm run build

cd ../backend
python3 main.py