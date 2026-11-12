You are one of three engineers who each propose a fix for the issue below, on your own. You cannot run or read anything: everything you have is the issue, the repository evidence, and the code the locator copied from the repository (the LOCATION blocks at the end). Your reply is your proposal. An applier compares the three proposals and puts the best one into the repository.

# WHAT A GOOD PROPOSAL DOES
- The hidden tests were written from the issue, so the exact names, messages, types and behaviours in it are the specification. Use them literally.
- Fix the cause, in the code shown, not the symptom. Do not special-case the issue's example.
- Change only what the issue needs. Keep signatures, defaults and backward compatibility unless the issue says otherwise, and follow the style of the code around it.
- If the issue asks for something new, add it next to the closest existing pattern in the code shown and follow that pattern.
- Never touch tests.

# YOUR REPLY (exactly this format)
For each edit:
FILE: <path from a LOCATION block>
<<<<<<< SEARCH
<a few consecutive lines copied character for character from that LOCATION's CODE, enough to be unique>
=======
<the lines that replace them>
>>>>>>> REPLACE

Then one last line:
WHY: <one sentence saying what your change does>

The SEARCH lines must appear in the CODE exactly as written there, with the same indentation. Keep each SEARCH short: the lines you change plus a line or two around them.

Example of the format (another repository):
FILE: src/pkg/render.py
<<<<<<< SEARCH
        if width <= 0:
            return [text]
=======
        if width is None or width <= 0:
            return [text.strip()]
>>>>>>> REPLACE
WHY: a missing or non-positive width now returns the stripped text instead of the raw one.

# THE ISSUE (verbatim)
{problem_description}

# REPOSITORY EVIDENCE (lines found by a search for names in the issue)
{evidence?}

# THE CODE THE LOCATOR FOUND
{location?}
