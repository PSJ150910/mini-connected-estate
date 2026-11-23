# Mini Connected Estate: a digital twin of a school campus

A learning project where I build a working digital twin of a small school campus (3 buildings), using free, industry-standard tools.

## What it will do
- Connect messy building data: a BIM model (IFC), sensor readings (BMS), repair jobs (CAFM) and compliance documents
- Check the data can be trusted, with a data quality score
- Study classroom temperatures and how rooms are used
- Spot faults early and explain the likely cause
- Track fire and safety certificates (the golden thread)
- Check a BIM model against handover requirements
- Show it all on a dashboard and answer questions with a local AI assistant

## Status
Module 0 of 10 done: tools set up and first script written.

## Tech stack
Python 3.12, uv, Git and GitHub, Docker, VS Code, Ruff

## Try it
Run `uv run python src/hello.py` to print the warmest and coldest rooms from `data/rooms.csv`.

## Author
Sai Jaswanth Palakaviti