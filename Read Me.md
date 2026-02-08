## Quick Communication Support

Phase 1–2: Assistive Communication Prototype and User Study

Overview

This repository presents Quick Communication Support, an assistive communication system designed to support people who experience situational or temporary speech difficulty in academic and social settings.

The project investigates how lightweight, non-intrusive digital tools can help users maintain participation and agency during moments when speech becomes difficult due to cognitive load, anxiety, or contextual pressure.

The work is structured as a two-phase Human–Computer Interaction (HCI) study, covering both prototype development and user evaluation.

Project Motivation

In academic environments such as seminars, supervision meetings, and group discussions, communication breakdowns can occur even among otherwise fluent speakers. These breakdowns are often:

Situational rather than permanent

Triggered by stress, fatigue, or cognitive overload

Poorly addressed by existing assistive technologies

Most augmentative and alternative communication (AAC) systems are designed for long-term or clinical speech impairments, leaving a gap for temporary, context-aware communication support.

This project explores how minimalist interface design and pre-structured linguistic support can reduce communicative friction in such contexts.

Phase 1: Assistive Communication Prototype

Objective:
To design and implement a functional proof-of-concept that demonstrates how assistive communication can be supported through simple, fast, and cognitively lightweight interaction.

Key Features:

Streamlit-based interactive interface

Predefined communication categories (e.g., clarification, pause, assistance)

One-click sentence generation

Low learning cost and immediate usability

Local execution with no data collection

The prototype emphasizes speed, clarity, and accessibility rather than personalization or automation.

Phase 2: User Study and Evaluation

Objective:
To evaluate the perceived usefulness, clarity, and usability of the prototype through a structured user study.

Participants:

Erasmus and international students at UPCT

Academic-context users familiar with high-pressure communication settings

Methodology:

Short guided demo of the prototype

Survey-based evaluation using 5-point Likert-scale questions

Qualitative feedback via open-ended responses

Evaluation Focus:

Ease of use

Communication clarity

Perceived usefulness in academic settings

Likelihood of real-world use

All study materials (consent text, survey questions, and study protocol) are documented in this repository.

Results Summary

Overall feedback indicated that:

The system was easy to understand with minimal explanation

Pre-written phrases reduced cognitive effort during communication

Participants valued the non-clinical, situational framing

The tool was seen as particularly useful in academic and formal settings

The results informed minor refinements and validated the feasibility of the approach for further exploration.

Technology Stack

Python

Streamlit (UI framework)

Markdown-based documentation

The system runs locally and does not rely on external services or data storage.

Repository Structure
.
├── app.py                  # Streamlit demo application
├── requirements.txt        # Python dependencies
├── docs/                   # Phase 2 report, research pitch, future work
├── survey/                 # Consent text and survey instruments
├── results/                # Study summaries and analysis notes
├── .gitignore
└── README.md

Research Contribution

This project contributes:

A lightweight assistive communication prototype for situational speech difficulty

A user-informed evaluation of non-clinical assistive communication tools

Design insights for HCI research at the intersection of communication, cognition, and accessibility

The work positions assistive communication as a continuum, rather than a binary clinical category.

Ethical Considerations

No personal or sensitive data was collected

Participation was voluntary and informed

The system does not store user input

The tool is designed to support, not replace, human interaction

Status and Future Work

✔ Phase 1 – Prototype development completed
✔ Phase 2 – User study completed

Planned future work includes:

Expanded contextual customization

Accessibility refinements

Broader participant studies

Formal academic dissemination

Research Context

This project was developed as part of an HCI-oriented research trajectory exploring assistive technologies for everyday cognitive and communicative challenges, with relevance to accessibility, inclusive design, and human-centered AI.
