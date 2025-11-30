# pediacenter_agent/control_tools.py

def check_child_identity(
    child_first_name: str = "",
    child_last_name: str = "",
    child_dob: str = "",
):
    """
    Control / guard tool to enforce identity requirements before
    viewing, cancelling, scheduling or rescheduling bookings

    - child_first_name: required
    - child_last_name: required
    - child_dob: required, expected as a string
      (e.g. '2019-04-15' or 'April 15, 2019')

    Returns:
      {
        "ok": bool,
        "missing": [list of missing fields]
      }
    """

    missing = []
    if not child_first_name.strip():
        missing.append("first_name")
    if not child_last_name.strip():
        missing.append("last_name")
    if not child_dob.strip():
        missing.append("date_of_birth")

    if missing:
        return {
            "ok": False,
            "missing": missing,
        }

    return {
        "ok": True,
        "missing": [],
    }
