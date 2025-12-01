🏥 Pediatric Scheduling Agent
AI-powered multi-agent scheduling assistant for a pediatric clinic

Built as a Capstone Project for the AI Agents Intensive Course  
________________________________________________________________________________________________________________________________________________

⚠️ Safety Disclaimer

This assistant does not provide medical advice, diagnosis, or treatment.
It only handles scheduling, clinic information, and administrative support.
If your child is experiencing a medical emergency, call your local emergency services immediately.

________________________________________________________________________________________________________________________________________________

📘 Overview

The Pediatric Scheduling Agent is an AI-driven scheduling system designed for a pediatric clinic.
It uses a multi-agent architecture to understand parent messages, enforce clinic rules, and safely book, cancel, or reschedule appointments.

The system runs inside the Agent Development Kit (ADK) and includes:

- A root conversational LLM agent
- A control agent enforcing patient identity requirements
- Tool functions for:
  - Extracting appointment details
  - Validating identity
  - Avoiding double-booking
  - Applying clinic rules
  - Booking, cancelling, rescheduling
  - Listing appointments
  - Structured scheduling data stored in JSON files
  - Safety measures to ensure PII is handled correctly

________________________________________________________________________________________________________________________________________________

🎯 Key Features

🔹 Conversational AI Scheduling
Parents can write in free text:
“Hi, I need to book an appointment for my child tomorrow.”

The agent automatically extracts:
- Child’s first name, last name, DOB
- Reason for visit
- Preferred doctor / time
- Urgency (routine vs. sick visit)


🔹 Control Agent - Identity Verification Required
Before any booking, cancellation, or rescheduling, the user must provide:
- Child’s first name
- Child’s last name
- Child’s date of birth (DOB)

If missing > the assistant politely asks for them.

🔹 Clinic Rules
The system enforces:
- No Sunday appointments
- Urgent visits get same-day preference
- No double-booking
- Doctor-specific availability

🔹 Appointment Management
The assistant can:
- Book appointments
- Cancel appointments (with or without confirmation ID)
- Reschedule appointments
- Show a child's upcoming bookings

If cancellation details are unclear, the agent shows all upcoming appointments and asks the parent to choose.

🔹 Automatic Safety Header
The first response of every session includes the safety disclaimer.

________________________________________________________________________________________________________________________________________________

🧩 Multi-Agent Architecture
This project fulfills the Capstone requirement for 3+ multi-agent concepts:

| Requirement                          | Implemented? | Details                                                             |
| ------------------------------------ | ------------ | ------------------------------------------------------------------- |
| **LLM-powered agent**                | ✔️           | Root agent powered by Gemini 2.5 Flash                              |
| **Sequential agents**                | ✔️           | Control agent validates PII before the main scheduling agent runs   |
| **Loop agents / iterative behavior** | ✔️           | Multi-step clarifications for missing data and ambiguity resolution |
| **Tool agents**                      | ✔️           | Multiple tools for scheduling, validation, and cancellation         |

________________________________________________________________________________________________________________________________________________

🗂 Project Structure

| File / Folder      | Description                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `agent.py`         | Main PediaCenter scheduling agent logic — instructions, LLM orchestration, tool calls, safety disclaimer injection. |
| `control_tools.py` | Identity-verification tool for validating child’s full name + date of birth before any protected action.            |
| `schedule.json`    | Mock clinic schedule containing available appointment slots. Used by the scheduling logic.                          |
| `bookings.json`    | Persistent storage for all created, rescheduled, and canceled appointments.                                         |
| `__init__.py`      | Marks the directory as a Python module.                                                                             |
| `requirements.txt` | Python dependencies required to run the ADK agent locally.                                                          |
| `.gitignore`       | Files and folders excluded from version control.                                                                    |
| `LICENSE`          | MIT license permitting open use and distribution of the project.                                                    |
| `README.md`        | Full documentation for the project (setup, usage, architecture).                                                    |

________________________________________________________________________________________________________________________________________________

🛠 Installation & Setup

1. Clone the repository
git clone https://github.com/salazardanielaf-sketch/pediatric-scheduling-agent.git
cd pediatric-scheduling-agent

2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Run the ADK interface
From inside the project folder: adk web

Then open: http://127.0.0.1:8000/dev-ui/

________________________________________________________________________________________________________________________________________________

🚀 How It Works

🗣 Free-text > Intent extraction
The LLM reads the parent’s input and extracts structured data using the tools.

🔒 Identity validation
The control agent checks for:
- First name
- Last name
- DOB

Missing? > Ask for it.

📅 Rule-based scheduling
The agent:
- Retrieves schedule
- Filters out unavailable days
- Applies urgency logic
- Avoids double-booking
- Books only valid slots returned by tools

🛑 Cancellation logic
Even without a confirmation ID, the agent can cancel based on:
- Child name
- Doctor
- Date/time

If ambiguous → it shows all upcoming appointments for that child.

________________________________________________________________________________________________________________________________________________

🔧 Tools Used

| Tool                          | Purpose                                 |
| ----------------------------- | --------------------------------------- |
| `extract_appointment_details` | Parses user message                     |
| `find_available_slots`        | Finds valid appointment times           |
| `apply_clinic_rules`          | Enforces clinic scheduling policies     |
| `book_appointment`            | Creates a booking                       |
| `cancel_appointment`          | Cancels with ID or with details         |
| `reschedule_appointment`      | Changes an existing booking             |
| `list_child_bookings`         | Lists the child’s upcoming appointments |
| `check_child_identity`        | Confirms first/last name + DOB          |

________________________________________________________________________________________________________________________________________________

📌 Screenshots 

Scheduling an appointmnet 
<img width="1916" height="977" alt="image" src="https://github.com/user-attachments/assets/401404fb-0152-44b9-bc30-1447a99f689b" />

Cancelling an appointment
<img width="1922" height="990" alt="image" src="https://github.com/user-attachments/assets/7e14dd33-ca40-4a51-997b-9d451b6452f8" />

________________________________________________________________________________________________________________________________________________

📜 License

This project is licensed under the MIT License.

________________________________________________________________________________________________________________________________________________

🤝 Credits

Created by Daniela Salazar and Thomas Moerke
Capstone project for the AI Agents Intensive Course





