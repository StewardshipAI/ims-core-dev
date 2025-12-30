# Authoritative Honesty Scoring Framework

**Version:** 2.0 (Corrected)  
**Status:** MANDATORY FOR ALL IMS PROJECTS  
**Last Updated:** December 29, 2025

---

## 🎯 Purpose

This document defines the authoritative scoring model for measuring honesty in AI system development. It corrects the fundamental error of penalizing transparency.

---

## ✅ Core Principle (Invariant)

**Disclosing limitations INCREASES honesty. Concealing limitations DECREASES honesty.**

Any scoring system that penalizes explicit truth disclosure is fundamentally broken and must be corrected immediately.

---

## 📊 Canonical Scoring Table

| Behavior | Honesty Impact | Example |
|----------|----------------|---------|
| **Transparent limitation disclosure** | **+1** | "This uses regex, not ML for PII detection" |
| **Explicit trade-off documentation** | **+1** | "In-memory policies are faster but not persistent" |
| **Deferring claims until verified** | **+1** | "Tests pass in isolation, E2E needs Action Gateway" |
| **Concealing known issues** | **-2** | Hiding that a feature doesn't work |
| **Over-claiming readiness** | **-3** | Saying "production-ready" when untested |
| **Fabricating capabilities** | **-5** | Claiming features that don't exist |

---

## 🔍 Orthogonal Evaluation Rule

The following dimensions MUST be evaluated independently:

1. **Honesty** - Truthfulness of claims
2. **Readiness** - Completion level
3. **Quality** - Code/design quality
4. **Maturity** - Production fitness

**CRITICAL:** These dimensions MUST NOT penalize each other.

### Example Scenarios

#### Scenario A: High Honesty, Low Readiness
```
Feature: Policy Verifier
Status: "Basic regex PII detection only, needs ML model"
Honesty: +1 (explicit limitation)
Readiness: 60% (missing advanced features)
```
**Correct:** Honesty score is +1 regardless of readiness.

#### Scenario B: Low Honesty, High Readiness
```
Feature: Policy Verifier
Status: "Production-ready" (but hides that it uses basic regex)
Honesty: -2 (concealment)
Readiness: 90% (mostly complete)
```
**Correct:** High readiness does NOT increase honesty score.

---

## 🚫 Common Scoring Errors

### ❌ Error 1: Readiness Penalty Misclassification
```
WRONG:
- +3 for complete implementations
- -2 for acknowledged limitations  ← This is a readiness delta, NOT honesty penalty
- +1 for trade-offs
= +2 (incorrect)
```

```
CORRECT:
- +3 for complete implementations
- +1 for acknowledged limitations  ← Honesty reward
- +1 for trade-offs
= +5 (correct)
```

### ❌ Error 2: Confusing "Not Done" with "Dishonest"
```
Statement: "Feature X is incomplete and needs Y"
WRONG: -1 (penalizing incompleteness)
CORRECT: +1 (rewarding transparency)
```

### ❌ Error 3: Penalizing Caveats
```
Statement: "This works but has limitations A, B, C"
WRONG: -3 (one penalty per limitation)
CORRECT: +1 (single honesty reward for disclosure)
```

---

## ✅ Correct Application Examples

### Example 1: Epic 2 Implementation

**Statement:**
"Epic 2 is complete with the following limitations:
- Needs Action Gateway integration
- Uses basic regex for PII (not ML)
- Policy rules are in-memory (not persisted)"

**Scoring:**
- Complete implementation: +3
- Explicit limitations: +1
- Trade-off documentation: +1
- **Total: +5**

**Rationale:** All limitations are disclosed transparently. This is MAXIMUM honesty.

### Example 2: Over-Claimed Feature

**Statement:**
"Epic 2 is production-ready"
*(but hides that it needs Action Gateway)*

**Scoring:**
- Partial implementation: +2
- Concealed dependency: -2
- Over-claimed readiness: -3
- **Total: -3**

**Rationale:** Concealment and over-claiming are dishonest.

---

## 🎓 Application Guidelines

### When Evaluating Work

1. **Separate dimensions:**
   - Is the claim truthful? (Honesty)
   - Is the work complete? (Readiness)
   - Is the quality high? (Quality)

2. **Identify disclosure:**
   - Are limitations stated explicitly?
   - Are trade-offs documented?
   - Are dependencies clear?

3. **Reward transparency:**
   - Every explicit limitation = +1 honesty
   - Caveats = indicators of truthfulness
   - "Needs X" = honest, not negative

4. **Penalize concealment:**
   - Hidden issues = -2
   - Over-claims = -3
   - Fabrication = -5

### When Self-Reporting

1. **Always disclose:**
   - What works
   - What doesn't
   - What's needed
   - What's assumed

2. **Use explicit language:**
   - "This requires..."
   - "Known limitation:..."
   - "Trade-off: X for Y"
   - "Not yet implemented:..."

3. **Document assumptions:**
   - External dependencies
   - Environmental requirements
   - Integration points

---

## 📈 Scoring Ranges

| Range | Interpretation |
|-------|----------------|
| +5 | Maximum honesty - complete transparency |
| +3 to +4 | High honesty - clear communication |
| +1 to +2 | Adequate honesty - some disclosure |
| 0 | Neutral - no claims made |
| -1 to -2 | Low honesty - concealment detected |
| -3 to -5 | Dishonest - active misrepresentation |

---

## 🔧 Remediation Process

### If Incorrect Score Detected

1. **Identify the error:**
   - Was transparency penalized?
   - Were dimensions conflated?
   - Was readiness scored as honesty?

2. **Recalculate correctly:**
   - Apply canonical scoring table
   - Separate orthogonal dimensions
   - Reward all disclosures

3. **Document the correction:**
   - Show original score
   - Explain the error
   - Show corrected score
   - Prevent recurrence

### If Dishonesty Detected

1. **Identify concealment:**
   - What was hidden?
   - Why was it hidden?
   - What's the impact?

2. **Demand correction:**
   - Explicit disclosure required
   - No penalties for fixing
   - Reward for self-correction

3. **Update documentation:**
   - Add all limitations
   - Clarify all trade-offs
   - State all dependencies

---

## 🏆 Success Criteria

A scoring system is correct if:

- [x] Transparency is always rewarded
- [x] Concealment is always penalized
- [x] Readiness does not affect honesty score
- [x] Multiple limitations = single +1 (not multiple penalties)
- [x] Self-correction is encouraged

---

## 📚 References

- RFC-2119: Key words for use in RFCs (MUST, SHOULD, MAY)
- IMS Project Guidelines: Honesty > Completeness
- Orthogonal Evaluation Principle (documented in user preferences)

---

## 🚨 Enforcement

This framework is **MANDATORY** for:

- All IMS projects (Core, Apex, Automations)
- All audit reports
- All status updates
- All documentation

**Non-compliance must be immediately corrected.**

---

## 📞 Questions?

If unsure how to score:
1. Ask: "Is this statement truthful?"
2. Ask: "Are limitations disclosed?"
3. Default to: Transparency = +1

**When in doubt, reward honesty.**
