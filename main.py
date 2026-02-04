#!/usr/bin/env python3
import os
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import requests
from dateutil import parser as date_parser
import inquirer
from ics import Calendar, Event

@dataclass
class Assignment:
    course_name: str
    name: str
    due_at: Optional[str]
    html_url: Optional[str]


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {get_env('CANVAS_API_TOKEN')}"})
    return session


def paginate(session: requests.Session, url: str, params: Dict[str, str]) -> Iterable[List[dict]]:
    while url:
        response = session.get(url, params=params)
        response.raise_for_status()
        yield response.json()
        next_link = response.links.get("next", {})
        url = next_link.get("url")
        params = {}


def fetch_courses(session: requests.Session, base_url: str) -> List[dict]:
    url = f"{base_url}/api/v1/courses"
    # get only active courses (canvas hides archived classes)
    params = {
        "enrollment_state": "active",
        "per_page": "100",
        "include[]": "term",
    }
    courses: List[dict] = []
    # i haven't heard of anyone with more than 10 classes at the same time,
    # but in the rare event this happens, we'd want to handle it as best as possible.
    # (if this is you, shoutout!)
    for page in paginate(session, url, params):
        courses.extend(page)
    return courses


def fetch_assignments(session: requests.Session, base_url: str, course_id: int) -> List[dict]:
    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    params = {
        "per_page": "100",
        "include[]": "submission",
        "order_by": "due_at",
    }
    assignments: List[dict] = []
    # there may be a large amount of assignments in a course.
    # so we get as many as possible, being 100 per req.
    for page in paginate(session, url, params):
        assignments.extend(page)
    return assignments


# used for printing
def parse_due_at(due_at: Optional[str]) -> Optional[str]:
    if not due_at:
        return None
    try:
        return date_parser.isoparse(due_at).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    except (ValueError, TypeError):
        return due_at


def collect_assignments(session: requests.Session, base_url: str, selected_course_ids: List[int]) -> List[Assignment]:
    courses = fetch_courses(session, base_url)
    results: List[Assignment] = []
    course_map = {c["id"]: c for c in courses if c.get("id")}

    for course_id in selected_course_ids:
        course = course_map.get(course_id)
        if not course:
            continue
        course_name = course.get("name") or course.get("course_code") or f"Course {course_id}"
        for item in fetch_assignments(session, base_url, course_id):
            results.append(
                Assignment(
                    course_name=course_name,
                    name=item.get("name") or "Untitled", # i've seen an assignment or 2 that (somehow) didn't have a title (?)
                    due_at=parse_due_at(item.get("due_at")),
                    html_url=item.get("html_url"),
                )
            )
    return results



def format_output(assignments: List[Assignment]) -> str:
    if not assignments:
        return "No assignments found."

    lines: List[str] = []
    current_course = None
    for assignment in assignments:
        if assignment.course_name != current_course:
            current_course = assignment.course_name
            lines.append("")
            lines.append(f"{current_course}")
            lines.append("-" * len(current_course))
        due_display = assignment.due_at or "No due date"
        url_display = f" ({assignment.html_url})" if assignment.html_url else ""
        lines.append(f"• {assignment.name} — {due_display}{url_display}")
    return "\n".join(lines).lstrip()


def prompt_course_selection(courses: List[dict]) -> List[int]:
    choices = [
        inquirer.Checkbox(
            'courses',
            message="Select courses to include in calendar",
            choices=[(c.get("name") or c.get("course_code") or f"Course {c.get('id')}", c["id"]) for c in courses if c.get("id")],
        )
    ]
    answers = inquirer.prompt(choices)
    return answers['courses'] if answers and 'courses' in answers else []


def prompt_export_mode() -> str:
    choices = [
        inquirer.List(
            "mode",
            message="Export options",
            # i added this for testing (since i was using my personal access token),
            # but i thought this would actually be a decent idea to keep so users could
            # select which assignments (incase they were only looking for specifics, like an exam.)
            choices=[("All assignments", "all"), ("Select assignments", "select")],
        )
    ]
    answers = inquirer.prompt(choices)
    return answers["mode"] if answers and "mode" in answers else "all"


def prompt_assignment_selection(assignments: List[Assignment]) -> List[Assignment]:
    if not assignments:
        return []
    choices = []
    for idx, a in enumerate(assignments):
        due_display = a.due_at or "No due date"
        label = f"{a.course_name} — {a.name} — {due_display}"
        choices.append((label, idx))
    prompt = [
        inquirer.Checkbox(
            "assignments",
            message="Choose assignments to export",
            choices=choices,
        )
    ]
    answers = inquirer.prompt(prompt)
    if not answers or "assignments" not in answers:
        return []
    return [assignments[i] for i in answers["assignments"]]

def create_ics(assignments: List[Assignment], filename: str = "assignments.ics") -> None:
    cal = Calendar()
    for a in assignments:
        if not a.due_at:
            continue
        try:
            dt = date_parser.parse(a.due_at)
        except Exception:
            continue
        event = Event()
        event.name = a.name
        event.begin = dt
        # ps: not even canvas does this! their export tool provides the course/assignment name,
        # but not a URL to it.. so we're infact making it much easier :)
        event.url = a.html_url or ""
        event.description = f"Course: {a.course_name}"
        cal.events.add(event)
    with open(filename, "w") as f:
        f.writelines(cal)
    print(f"\nCreated calendar file: {filename}")

def main() -> int:
    base_url = get_env("CANVAS_BASE_URL").rstrip("/")

    session = make_session()
    try:
        courses = fetch_courses(session, base_url)
        if not courses:
            print("No courses found.")
            return 1
        selected_course_ids = prompt_course_selection(courses)
        if not selected_course_ids:
            return 0
        assignments = collect_assignments(session, base_url, selected_course_ids)
    except requests.HTTPError as err:
        # canvas try not to blow up infrastructure challenge: impossible
        raise Exception("API request failed: {err}")

    print(format_output(assignments))
    export_mode = prompt_export_mode()
    if export_mode == "select":
        chosen = prompt_assignment_selection(assignments)
        if not chosen:
            print("No assignment selected. Exiting.")
            return 0
        create_ics(chosen)
    else:
        create_ics(assignments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
