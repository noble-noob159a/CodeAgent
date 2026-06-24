---
name: Analyzing Research Papers
description: This skill should be used when the user asks to summarize, compare, critique, or extract structured insights from research papers, technical reports, or academic PDFs.
version: 1.0.0
---

# Analyzing Research Papers

## Overview
This skill helps analyze academic papers and technical reports in a structured way.
It is intended for summarization, method comparison, extracting contributions, and identifying limitations.

## When to use
Use this skill when the user:
- asks for a paper summary
- wants the methodology or architecture explained
- wants comparisons across multiple papers
- wants limitations, assumptions, or future work extracted

## Workflow
1. Identify the paper title, domain, and task.
2. Extract the problem statement and main contribution.
3. Summarize the method:
   - input/output
   - architecture or algorithm
   - training/evaluation setup
4. Extract results and compare against baselines if present.
5. List limitations, assumptions, and open questions.
6. Produce the answer in the format requested by the user.

## Output format
Prefer the following structure unless the user asks otherwise:
1. Problem
2. Key idea
3. Method
4. Results
5. Strengths
6. Limitations
7. My takeaways / follow-up questions

## Rules
- Do not claim results that are not stated in the source.
- Distinguish clearly between the paper’s claims and your interpretation.
- Preserve important technical terms, dataset names, and metrics.
- If the paper is incomplete or unreadable, say what information is missing.

## Special cases
### Comparison requests
When comparing multiple papers:
- align them by task, dataset, and evaluation metric
- note whether they are directly comparable
- avoid comparing raw numbers from incompatible setups

### Vision-language papers
For VLM / multimodal papers, explicitly identify:
- visual encoder
- language model / decoder
- fusion strategy
- pretraining objective
- downstream tasks

## Additional resources
- `references/review-checklist.md` for a detailed critique rubric
- `references/common-ml-metrics.md` for metric interpretation
- `examples/paper-summary-example.md` for output examples