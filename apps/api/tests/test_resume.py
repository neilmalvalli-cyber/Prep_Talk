from interviewer.resume import experience_claims


def test_wrapped_resume_entries_keep_project_names_and_source_provenance():
    text = (
        "Candidate Name\ncandidate@example.com\nSomewhere, Region, Country\n"
        "STUDENT PROFILE\nA student interested in building software.\n"
        "KEY SKILLS\nPython JavaScript Rust\n"
        "EXPERIENCE\nHackathons\nParticipated in a team hackathon,\n"
        "building a prototype over a weekend.\n"
        "EDUCATION & CERTIFICATIONS\nUniversity name and degree\n"
        "PROJECTS\nCampus app\nBuilt a mobile application that displays\n"
        "class schedules and attendance locally.\n"
        "File tool\nBuilt a tool that processes documents\n"
        "using Python and stores results locally.\n"
        "DISCLOSURE\nI declare that these details are accurate.\n"
    )
    claims = experience_claims([{"page": 1, "text": text}], lambda text: text)
    assert len(claims) == 3
    assert [claim["project"] for claim in claims] == ["Hackathons", "Campus app", "File tool"]
    assert claims[1]["contribution"] == "Built a mobile application that displays class schedules and attendance locally."
    for claim in claims:
        assert text[claim["offset"]:].startswith(claim["source_bullet"])
        assert claim["page"] == 1
        assert claim["technology"] == claim["result"] == claim["measurement"] == ""
    assert "candidate@example.com" not in str(claims)
    assert "University" not in str(claims)


def test_unstructured_text_and_bullets_do_not_require_section_headings():
    pages = [{"page": None, "text": "  Built a service with Python.\nImplemented validation at the API boundary.\n"},
             {"page": 2, "text": "• Built a local client that\nhandles offline updates.\n• Verified retry behavior with tests."}]
    claims = experience_claims(pages, lambda text: text)
    text = "\n".join(page["text"] for page in pages)
    assert len(claims) == 4
    assert claims[2]["contribution"] == "Built a local client that handles offline updates."
    for claim in claims:
        assert text[claim["offset"]:].startswith(claim["source_bullet"])


def test_inline_nonexperience_headings_are_excluded():
    text = "Projects\nBuilt an offline note application.\nTechnical skills: Python, SQL\nEducation: Example University\nProfessional summary: A software student.\n"
    claims = experience_claims([{"page": 1, "text": text}], lambda value: value)
    assert len(claims) == 1
    assert claims[0]["contribution"] == "Built an offline note application."
