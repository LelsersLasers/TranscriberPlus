#!/bin/bash

ffmpeg -i input.mp4 -q:a 0 -map a audio.wav
