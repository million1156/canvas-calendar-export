# canvas-calendar-export

A tool to export select classes assignments from Canvas

## Setup

1. Create a Canvas API token in your Canvas account. To do this, visit your Canvas profile (https://your-school.instructure.com/profile/), go to `Settings`, and click "New Access Token"; the purpose & expiration can be whatever you wish.
2. Set environment variables:

```bash
export CANVAS_BASE_URL="https://your-school.instructure.com"
export CANVAS_API_TOKEN="your_token_here"
```

> [!TIP]
> For `CANVAS_BASE_URL`, your URL may be different than `instructure.com` (for example, `college.edu`). This is okay :)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Why?

I have a lot of memory issues and would always love reminders. Canvas/Instructure provides a way to export assignments as a calendar, but the problem is it exports **every** single class's assignments instead of just the ones you want!

This became very annoying to me, because my college enrolls me in mandatory classes about non-applicable stuff. I didn't want to have unnessecary clutter fill up my calendar, so I created a very quick tool (this repo!) that allowed me to export my assignments for the classes I **actually take**!

Another problem I had is Canvas's export tool does not contain the URL to the assignment, which is fustrating if you're someone who has trouble with searching for assignments. This tool fixes that by using the [iCalendar standard](https://datatracker.ietf.org/doc/html/rfc5545)'s URL property. 

Example:

<img width="378" height="364" alt="Screenshot 2026-02-04 at 10 10 26 AM" src="https://github.com/user-attachments/assets/420d81e6-4b1e-40ef-a92c-51a0aa390920" />



## Options
This tool has 2 options (once you select your courses):
- All assignments
- Select assignments

Selecting "all assignments" will export all assignments for the courses you selected, while "select assignments" will allow you to select individual assignments. This is helpful if you're looking for particular assignment(s), such as Exams or a specfiic Module/Chapter.

