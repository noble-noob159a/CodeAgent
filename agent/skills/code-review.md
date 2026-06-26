---
name: Code Review and Bug Analysis
description: Review a single source code file to identify bugs, correctness issues, performance bottlenecks, security risks, maintainability concerns.
version: 1.0.0
---

# Code Review and Bug Analysis

## Overview

This skill helps analyze a single source code file for correctness, reliability, maintainability, performance, and security issues.

It is intended for:

* bug hunting
* code review
* root cause analysis
* performance analysis
* security review
* refactoring recommendations

## When to use

Use this skill when the user:

* asks for a code review
* asks "find bugs in this file"
* asks why code is failing
* wants performance bottlenecks identified
* wants code quality feedback
* wants security issues identified
* wants suggestions for improvement
* wants an explanation of how a file works

## Workflow

### 1. Understand the file

First determine:

* programming language
* purpose of the file
* inputs and outputs
* major classes, functions, and modules
* external dependencies

Briefly summarize the file before reviewing it.


### 2. Review for correctness

Look for:

* logical errors
* off-by-one errors
* invalid assumptions
* missing edge cases
* incorrect conditions
* incorrect data handling
* race conditions
* concurrency issues

### 3. Review for runtime failures

Look for:

* null / None dereferences
* index out-of-range access
* type mismatches
* exception handling issues
* resource leaks
* infinite loops
* recursion risks
* deadlocks

### 4. Review for performance

Look for:

* unnecessary loops
* repeated computations
* inefficient algorithms
* excessive memory allocations
* unnecessary I/O
* poor scaling behavior

Estimate:

* time complexity
* space complexity

when relevant.

### 5. Classify findings

Assign one severity level:

#### Critical

Likely to cause crashes, security vulnerabilities, data corruption, or major failures.

#### High

Likely to produce incorrect behavior or major maintenance problems.

#### Medium

Potential reliability, performance, or maintainability concerns.

#### Low

Minor issues, code smells, or stylistic improvements.

## Output Format

### File Summary

* Purpose
* Language
* Key Components

### Execution Flow

Brief explanation of how the file works.

### Findings

