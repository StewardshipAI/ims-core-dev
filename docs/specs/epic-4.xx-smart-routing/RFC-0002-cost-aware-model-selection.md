# RFC-0002: Cost-Aware Model Selection

Status: Draft  
Target Release: v0.4.0  

## Problem

Selecting the most capable model by default is economically inefficient
and causes avoidable quota exhaustion.

## Solution

Introduce an Expected Cost of Successful Completion (ECSC) metric:

ECSC = Expected Token Cost / P(success)

The router selects the model with the lowest ECSC within policy constraints.

## Non-Goals
- Perfect success prediction
- Quality maximization without budget awareness

## Dependencies
- Policy Engine output
- Model Registry metadata
- Telemetry feedback loop
