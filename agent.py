# pediacenter_agent/agent.py
from google.adk.agents import Agent
import json
import os
from datetime import datetime, timedelta, time
import re

# import the control agent tool 
from .control_tools import check_child_identity

# ---------------- SAFETY DISCLAIMER ----------------
SAFETY_HEADER = """
⚠️ **Important Disclaimer**
This assistant cannot provide medical advice and is only for scheduling, clinic information, and administrative support.  
If you believe your child may be experiencing a medical emergency, call your local emergency services or go to the nearest emergency department immediately.
"""


# ------------------ BOOKING HELPER FUNCTIONS ------------------
def _load_bookings():
    """Internal helper to load bookings.json safely."""
    bookings_path = os.path.join(os.path.dirname(__file__), "bookings.json")

    if not os.path.exists(bookings_path):
        return {"bookings": []}, bookings_path

    with open(bookings_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"bookings": []}

    if "bookings" not in data:
        data["bookings"] = []

    return data, bookings_path


def _save_bookings(data, bookings_path: str):
    """Internal helper to save bookings.json."""
    with open(bookings_path, "w") as f:
        json.dump(data, f, indent=2)


# ------------------ TOOL FUNCTIONS ------------------

def extract_appointment_details(message: str):
    """
    Lightweight rule-based parser to extract:
    - visit_type (well_child vs sick_visit)
    - preferred_times (morning / afternoon / any)
    - child_age_years (if mentioned)
    - symptoms (basic)
    - preferred_doctor (if mentioned by name)
    - urgency (routine / urgent)
    """

    text = message.lower()

    # ---- AGE PARSING ----
    age_years = 4  # default if not found
    age_match = re.search(r"(\d+)\s*(year|yr|yo|yrs|years)\b", text)
    if age_match:
        try:
            age_years = int(age_match.group(1))
        except ValueError:
            age_years = 4

    # ---- VISIT TYPE ----
    sick_keywords = [
        "fever", "cough", "vomit", "vomiting", "rash",
        "pain", "ear infection", "sore throat", "sick",
        "diarrhea", "flu", "cold", "ill"
    ]
    well_keywords = [
        "check-up", "check up", "well visit", "well-child",
        "well child", "annual", "routine visit", "physical"
    ]

    visit_type = "well_child"
    if any(word in text for word in sick_keywords):
        visit_type = "sick_visit"
    elif any(word in text for word in well_keywords):
        visit_type = "well_child"

    # ---- TIME OF DAY ----
    if "morning" in text or "early" in text:
        preferred_times = "morning"
    elif "afternoon" in text or "after school" in text or "evening" in text:
        preferred_times = "afternoon"
    else:
        preferred_times = "any"

    # ---- SYMPTOMS ----
    found_symptoms = []
    for word in sick_keywords:
        if word in text:
            found_symptoms.append(word)
    symptoms = ", ".join(sorted(set(found_symptoms)))

    # ---- DOCTOR PREFERENCE ----
    known_doctors = ["bustamante", "smith", "jones"]
    preferred_doctor = ""
    for doc in known_doctors:
        if doc in text:
            preferred_doctor = "Dr. " + doc.capitalize()
            break

    # ---- URGENCY ----
    urgent_keywords = [
        "difficulty breathing", "trouble breathing", "emergency",
        "really bad", "high fever", "can't keep anything down",
        "cant keep anything down", "severe", "urgent"
    ]
    urgency = "routine"
    if any(phrase in text for phrase in urgent_keywords):
        urgency = "urgent"

    return {
        "raw_message": message,
        "child_name": "Example Child",     # placeholder—can improve later
        "child_age_years": age_years,
        "visit_type": visit_type,
        "symptoms": symptoms,
        "preferred_times": preferred_times,
        "preferred_doctor": preferred_doctor,
        "urgency": urgency,
        "language": "en",
    }

import json
import os

def find_available_slots(
    child_age_years: int,
    visit_type: str,
    preferred_times: str,
    preferred_doctor: str = "",
    urgency: str = "routine",
):
    """
    Use schedule.json as a DAILY TEMPLATE and generate real future dates.

    - Ignores the date part in schedule.json and uses only the time + visit_type.
    - Urgency logic:
        * urgent sick_visit  -> look from today to +2 days
        * routine sick_visit -> look from +1 to +5 days
        * well_child         -> look from +2 to +14 days (no same-day)
    - Skips Sundays (clinic closed).
    - Skips slots that are already booked (from bookings.json).
    """

    # Load the schedule template
    schedule_path = os.path.join(os.path.dirname(__file__), "schedule.json")
    with open(schedule_path, "r") as f:
        schedule_data = json.load(f)

    # Load existing bookings to avoid double-booking
    bookings_data, _ = _load_bookings()
    booked_pairs = set()  # (slot_start, provider)
    for b in bookings_data.get("bookings", []):
        if b.get("status") == "cancelled":
            continue
        slot_start = b.get("slot_start")
        provider_name = b.get("provider")
        if slot_start and provider_name:
            booked_pairs.add((slot_start, provider_name))

    results = []

    # Today’s date
    today = datetime.today().date()

    # ----- URGENCY WINDOW -----
    # Decide the range of days to search, based on visit_type + urgency
    if visit_type == "sick_visit":
        if urgency == "urgent":
            start_offset, end_offset = 0, 2   # today, +1, +2
        else:
            start_offset, end_offset = 1, 5   # +1 to +5 days
    elif visit_type == "well_child":
        # Well visits: no same-day; book further out
        start_offset, end_offset = 2, 14       # +2 to +14 days
    else:
        # Default fallback
        start_offset, end_offset = 1, 7

    # Generate slots within that window
    for day_offset in range(start_offset, end_offset + 1):
        day = today + timedelta(days=day_offset)

        # Skip Sundays (weekday() == 6)
        if day.weekday() == 6:
            continue

        for provider in schedule_data["providers"]:
            if preferred_doctor and provider["name"] != preferred_doctor:
                continue

            for slot in provider["schedule"]:
                # Match visit type (well vs sick)
                if slot["visit_type"] != visit_type:
                    continue

                # Extract hour and minute from the template start time
                # Assumes schedule.json times like "YYYY-MM-DDTHH:MM:SS"
                start_str = slot["start"]
                hour = int(start_str[11:13])
                minute = int(start_str[14:16])

                # Build a real datetime for this day
                dt = datetime.combine(day, time(hour=hour, minute=minute))

                # Filter by preferred time of day
                if preferred_times == "morning" and dt.hour >= 12:
                    continue
                if preferred_times == "afternoon" and dt.hour < 12:
                    continue
                # If preferred_times == "any", accept both

                # Build ISO datetime string (must match what we store in bookings)
                start_iso = dt.isoformat(timespec="minutes")

                # Skip if this slot is already booked
                if (start_iso, provider["name"]) in booked_pairs:
                    continue

                results.append({
                    "start": start_iso,
                    "provider": provider["name"],
                })

    return {"slots": results}

def apply_clinic_rules(visit_type: str, slots_json: str):
    """
    ADK-safe: take a JSON string instead of complex types.
    For now, simply return it as the recommended result.
    """
    return {"recommended_slots_json": slots_json}


def book_appointment(slot_start: str, provider: str, child_name: str):
    """
    Save the booking to bookings.json and return a confirmation.
    """

    # Path to bookings.json in the same folder as this file
    bookings_path = os.path.join(os.path.dirname(__file__), "bookings.json")

    # If bookings.json doesn't exist or is broken, start fresh
    if not os.path.exists(bookings_path):
        data = {"bookings": []}
    else:
        with open(bookings_path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"bookings": []}

    # Make sure there's a 'bookings' list
    if "bookings" not in data:
        data["bookings"] = []

    # Build a booking record
    booking = {
        "slot_start": slot_start,
        "provider": provider,
        "child_name": child_name,
        "status": "booked",
    }

    # Add booking to the list
    data["bookings"].append(booking)

    # Save back to bookings.json
    with open(bookings_path, "w") as f:
        json.dump(data, f, indent=2)

    # Add a simple confirmation_id and return to the agent
    booking["confirmation_id"] = f"{provider}-{slot_start}"
    return booking


def reschedule_appointment(
    old_confirmation_id: str,
    new_slot_start: str,
    new_provider: str,
    child_name: str,
):
    """
    Reschedule an appointment for a child.

    Behavior:
      1) If old_confirmation_id is provided and matches a booking,
         cancel that booking.
      2) Otherwise, try to find the most relevant upcoming booking for
         this child (and provider if given) and cancel that.
      3) Then book a new appointment at the requested time/provider.
    """

    data, bookings_path = _load_bookings()

    # Normalize inputs
    cid = (old_confirmation_id or "").strip().lower()
    child_lower = (child_name or "").strip().lower()

    booking_to_cancel = None

    # ---- 1) Try to cancel by confirmation ID ----
    if cid:
        for b in data.get("bookings", []):
            if b.get("confirmation_id", "").strip().lower() == cid:
                booking_to_cancel = b
                break

    # ---- 2) Fallback: find an upcoming booking for this child ----
    if booking_to_cancel is None and child_lower:
        from datetime import datetime

        now = datetime.now()
        candidates = []

        for b in data.get("bookings", []):
            if b.get("status") != "booked":
                continue

            # Match child name (substring, case-insensitive)
            if child_lower not in b.get("child_name", "").lower():
                continue

            # If a provider is specified, match it as well
            if new_provider and b.get("provider") != new_provider:
                continue

            # Only consider future appointments
            try:
                dt = datetime.fromisoformat(b["slot_start"])
            except Exception:
                continue

            if dt >= now:
                candidates.append((dt, b))

        # Pick the soonest upcoming appointment
        if candidates:
            candidates.sort(key=lambda x: x[0])
            booking_to_cancel = candidates[0][1]

    # ---- If we still have nothing, fail gracefully ----
    if booking_to_cancel is None:
        return {
            "status": "not_rescheduled",
            "message": (
                "Could not find an existing appointment to reschedule. "
                "Please provide the confirmation ID or more details."
            ),
        }

    # Mark the old booking as cancelled
    booking_to_cancel["status"] = "cancelled"
    _save_bookings(data, bookings_path)

    # Book the new appointment
    new_booking = book_appointment(
        slot_start=new_slot_start,
        provider=new_provider,
        child_name=child_name,
    )

    return {
        "status": "rescheduled",
        "old_confirmation_id": booking_to_cancel.get("confirmation_id"),
        "new_confirmation_id": new_booking["confirmation_id"],
        "new_slot_start": new_booking["slot_start"],
        "new_provider": new_booking["provider"],
        "message": (
            f"Your appointment has been rescheduled. "
            f"New time: {new_booking['slot_start']} with {new_booking['provider']}."
        ),
    }


def cancel_appointment(
    confirmation_id: str = "",
    child_name: str = "",
    slot_start: str = "",
    provider: str = "",
):
    """
    Cancel an existing appointment.

    The tool will try, in order:
      1) Exact confirmation_id match (if provided)
      2) Match by child_name + provider + slot_start (date/time)
      3) Match by child_name + provider + same date (if time not exact)

    If it cannot uniquely identify a booking, it will return:
      - status: "not_found" or "ambiguous"
      - bookings_for_child: list of that child's upcoming bookings (if child_name given)

    Arguments (all optional):
      confirmation_id: confirmation ID string
      child_name: child/patient name
      slot_start: ISO datetime or date string for the appointment (e.g. "2025-12-02T15:30" or "2025-12-02")
      provider: provider name (e.g., "Dr. Majjul")
    """

    from datetime import datetime

    data, bookings_path = _load_bookings()

    cid = (confirmation_id or "").strip().lower()
    child_lower = (child_name or "").strip().lower()
    provider_name = (provider or "").strip()

    # --- Parse requested date/time if provided ---
    req_dt = None
    req_date = None
    if slot_start:
        try:
            req_dt = datetime.fromisoformat(slot_start)
            req_date = req_dt.date()
        except Exception:
            req_dt = None
            req_date = None

    candidates = []

    # ---- 1) Try by confirmation ID if provided ----
    if cid:
        for b in data.get("bookings", []):
            if b.get("status") == "cancelled":
                continue
            bid = (b.get("confirmation_id") or "").strip().lower()
            if bid == cid:
                candidates = [b]
                break
    else:
        # ---- 2) Match by child / provider / date/time ----
        for b in data.get("bookings", []):
            if b.get("status") == "cancelled":
                continue

            # Child match (substring, case-insensitive)
            if child_lower and child_lower not in (b.get("child_name") or "").lower():
                continue

            # Provider match (if specified)
            if provider_name and provider_name != b.get("provider"):
                continue

            # Date/time match (if specified)
            if req_dt or req_date:
                try:
                    b_dt = datetime.fromisoformat(b["slot_start"])
                except Exception:
                    continue

                # If exact datetime given, require exact match
                if req_dt and req_dt.time() != datetime.min.time():
                    if b_dt != req_dt:
                        continue
                # If only date effectively given, allow any time on that date
                elif req_date and b_dt.date() != req_date:
                    continue

            candidates.append(b)

    # ---- Helper: gather upcoming bookings for this child ----
    bookings_for_child = []
    if child_lower:
        now = datetime.now()
        for b in data.get("bookings", []):
            if b.get("status") == "cancelled":
                continue
            if child_lower not in (b.get("child_name") or "").lower():
                continue
            try:
                b_dt = datetime.fromisoformat(b["slot_start"])
            except Exception:
                continue
            if b_dt >= now:
                bookings_for_child.append(
                    {
                        "child_name": b.get("child_name"),
                        "provider": b.get("provider"),
                        "slot_start": b.get("slot_start"),
                        "confirmation_id": b.get("confirmation_id"),
                        "status": b.get("status"),
                    }
                )

    # ---- No matches ----
    if not candidates:
        return {
            "status": "not_found",
            "message": (
                "I couldn't find an appointment that matches those details to cancel."
            ),
            "bookings_for_child": bookings_for_child,
        }

    # ---- Multiple matches -> ambiguous ----
    if len(candidates) > 1:
        # Don't cancel anything yet; let the user choose.
        return {
            "status": "ambiguous",
            "message": (
                "I found multiple matching appointments. "
                "Please tell me which one to cancel."
            ),
            "candidates": [
                {
                    "child_name": b.get("child_name"),
                    "provider": b.get("provider"),
                    "slot_start": b.get("slot_start"),
                    "confirmation_id": b.get("confirmation_id"),
                    "status": b.get("status"),
                }
                for b in candidates
            ],
            "bookings_for_child": bookings_for_child,
        }

    # ---- Exactly one match -> cancel it ----
    booking = candidates[0]
    booking["status"] = "cancelled"
    _save_bookings(data, bookings_path)

    return {
        "status": "cancelled",
        "message": (
            f"Appointment for {booking.get('child_name', 'the child')} "
            f"with {booking.get('provider', 'the provider')} at "
            f"{booking.get('slot_start')} has been cancelled."
        ),
        "bookings_for_child": bookings_for_child,
    }


def list_child_bookings(child_name: str):
    """
    List upcoming (non-cancelled) bookings for a given child name.

    Matching is case-insensitive and will match partial names
    (e.g., "bru" will match "Bruno").
    """
    from datetime import datetime

    data, _ = _load_bookings()
    now = datetime.now()
    name_lower = child_name.strip().lower()

    upcoming = []

    for booking in data.get("bookings", []):
        # Skip cancelled
        if booking.get("status") == "cancelled":
            continue

        # Match child name (case-insensitive, substring match)
        if name_lower not in booking.get("child_name", "").lower():
            continue

        # Parse datetime; if broken, skip
        try:
            dt = datetime.fromisoformat(booking["slot_start"])
        except Exception:
            continue

        # Only show future appointments
        if dt < now:
            continue

        upcoming.append(booking)

    return {"bookings": upcoming}

# ------------------ ROOT AGENT ------------------

root_agent = Agent(
    name="pediacenter_scheduler",
    model="gemini-2.5-flash",
    description=(
        "AI scheduling assistant for a pediatric clinic. "
        "Understands parent messages, extracts visit details, "
        "checks provider schedules, applies clinic rules, "
        "and books appointments."
    ),
    instruction= SAFETY_HEADER + """
Behavior for the disclaimer:
- In your VERY FIRST reply in a new conversation, start by showing the
  disclaimer text above, then a blank line, then your normal greeting.
- In all later replies in the same conversation, DO NOT repeat the disclaimer.


You are PediaCenter, an AI scheduling assistant for a pediatric clinic.

Your responsibilities:
- Understand free-text messages from parents in English.
- When needed, use tools to:
  1) extract appointment details,
  2) find available appointment slots,
  3) apply clinic rules,
  4) book appointments,
  5) list existing bookings,
  6) cancel appointments,
  7) reschedule appointments,
  8) verify patient identity (check_child_identity).

GENERAL RULES:
- If important details are missing for NEW appointments, you MUST first ask for:
    • the child's FIRST and LAST name
    • the child's DATE OF BIRTH (DOB)
    • the reason for the visit (e.g., sick visit, well-child check)
    • any preferred day or time of day
  Example wording:
  "To schedule the appointment, please tell me your child's first and last name,
   date of birth, the reason for the visit, and any preferred day or time of day."
  You may optionally also ask for the child's age, but DO NOT skip asking for
  date of birth.
- Only book slots provided by the tools — never invent times.
- Keep responses clear, concise, and friendly.

PRIVACY & IDENTITY VERIFICATION (MANDATORY):
- Before you **VIEW**, **LIST**, **CANCEL**, or **RESCHEDULE** any existing appointment, you MUST verify the child’s identity.
- Ask the user EXACTLY for:
    • Child’s FIRST name  
    • Child’s LAST name  
    • Child’s DATE OF BIRTH (DOB)
- Use the check_child_identity tool to verify the provided information.
- If check_child_identity returns ok = False:
    • Ask ONLY for the missing or incorrect fields.  
    • Do NOT call any booking-related tool until ok = True.
- If the user refuses to provide name + DOB:
    • Explain that for privacy reasons you cannot access or change any appointments.

CANCEL APPOINTMENTS:
- When a user asks to cancel:
  - First try to understand which appointment they mean based on free text
    (child name, provider, date/time, or confirmation ID).
  - After successful identity verification, call cancel_appointment.
    You may pass a confirmation_id, OR child_name + provider + date/time.
  - If cancel_appointment returns "not_found" or "ambiguous":
      • Show the user the list of the child’s upcoming appointments.
      • Ask which one they want to cancel.
      • Then call cancel_appointment again with the specific confirmation_id.

RESCHEDULE APPOINTMENTS:
- When a user asks to reschedule:
  - First require identity verification (first + last name + DOB).
  - If the user provides a confirmation ID, pass it directly.
  - If not, pass an empty old_confirmation_id but include child_name,
    new slot, and provider; the tool will choose the most relevant booking.
  - If the tool cannot determine the correct appointment:
      • Show the list of upcoming visits.
      • Ask which one the parent wants to reschedule.

LIST BOOKINGS:
- When a user asks: “What appointments does <child> have?”
  - First require identity verification.
  - Then call list_child_bookings with the REDACTED child search name.
  - Summarize date, time, provider, and confirmation ID.

IMPORTANT:
- NEVER reveal appointment details or booking history without full identity verification.
- NEVER skip the check_child_identity step before viewing/canceling/rescheduling/listing.
""",
       tools=[
        extract_appointment_details,
        find_available_slots,
        apply_clinic_rules,
        book_appointment,
        cancel_appointment,
        reschedule_appointment,
        list_child_bookings,
        check_child_identity,
    ],
)

