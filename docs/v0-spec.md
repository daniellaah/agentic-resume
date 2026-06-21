# V0 Specification

## Goal

Given an English software engineering resume and an English job
description, produce structured job requirements, map each requirement
to evidence from the resume, and generate evidence-grounded rewrite
suggestions.

## Inputs

- Plain-text English resume
- Plain-text English job description

## Outputs

- Structured job analysis
- Evidence mapping
- Resume rewrite suggestions
- Validation issues

## Core rule

The system must not invent employers, titles, dates, technologies,
metrics, responsibilities, team sizes, or business impact.

Every rewrite suggestion must reference one or more source resume
bullet IDs.

## Non-goals

- Web interface
- User authentication
- PDF or DOCX parsing
- Database storage
- Cloud deployment
- LangGraph orchestration
- Automatic job application
- ATS score prediction

## Definition of done

- All domain objects are represented by Pydantic models
- Sample resume bullets have stable IDs
- Invalid statuses fail schema validation
- Unsupported rewrite suggestions can be detected
- Unit tests pass