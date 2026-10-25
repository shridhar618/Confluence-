# AI Security & Incident Response Policy

**Document ID:** ORG-POL-04
**Category:** Security
**Owner:** SecureAI Governance Office
**Version:** 1.0
**Applies to:** All AI Assistant requests, security events, and governance case handling

## 1. Purpose

This policy defines how the organization detects, scores, and responds to security-relevant AI usage — from a single risky request to a pattern of repeated risky behavior — and what actions administrators may take.

## 2. Recognized Threat Categories

The risk engine evaluates every AI Assistant request against the following categories. Each category contributes to a request's risk score; an admin may adjust the weight of each category (see §6) but may not disable §2(c) or §2(e) scoring entirely, as these map to the absolute prohibitions in the Data Privacy & Classification Policy (ORG-POL-03 §5).

  a. **Cybersecurity threat language** — requests referencing exploitation, vulnerability probing, or attack planning against organizational systems.

  b. **Malware / attack tooling references** — requests for or about malicious code, exploit development, or offensive security tooling.

  c. **Data exfiltration signals** — requests structured to extract bulk data, credentials, or restricted records, including attempts phrased to appear incidental (e.g., "just for a summary").

  d. **Sensitive PII disclosure requests** — requests for personal or compensation data the requester's role does not authorize (see Role & Access Control Policy, ORG-POL-02).

  e. **Insider threat indicators** — repeated attempts to access information or systems outside the requester's role, particularly following a prior warning.

## 3. Risk Scoring and Decisioning

3.1. Each request receives a risk score and is classified as LOW, MEDIUM, or HIGH based on configurable thresholds (see §6). The resulting governance decision is one of: **ALLOWED**, **WARNING**, or **RESTRICTED**.

3.2. A single HIGH-risk request results in RESTRICTED by default and is logged as a security event.

3.3. Risk from multiple requests accumulates for a given user over time. When a user's cumulative risk score exceeds the configured cumulative threshold, a **Governance Case** is automatically opened for administrator review — the system does not restrict or warn the user beyond the individual request's own decision without a case being reviewed by a human administrator.

## 4. Security Events

4.1. A **Security Event** is recorded for: a HIGH-risk request, a detected policy bypass attempt, a simulated attack scenario run by an administrator for training/demo purposes, or a Ghost Mode intervention.

4.2. Security events from the organization's Attack Simulation console are clearly labeled as simulated and never represent real attacker activity; the same scoring and alerting pipeline is used deliberately so that administrators train on realistic signals.

## 5. Governance Case Handling

5.1. A Governance Case moves through the following statuses: **Open → Under Review → Warned / Restricted → Resolved**, with **Escalated** available at any point for cases requiring senior review.

5.2. Available administrator actions on a case are: **Review**, **Warn**, **Restrict**, **Restore**, **Escalate**, **Resolve**, and **Note**. Every action is recorded against the case with the acting administrator's identity and timestamp.

5.3. Restriction is temporary and reversible via the **Restore** action. The system does not permanently disable an account or terminate employment as an automated consequence of any risk score — that determination remains a human HR/management decision outside the scope of this policy.

5.4. All case activity, including risk events, retrieved policy evidence, and administrator notes, must remain visible in the case detail view to support explainable, auditable decisions.

## 6. Configuration Authority

6.1. Risk category weights and the LOW/MEDIUM/HIGH and cumulative-risk thresholds are configurable by Admin users holding `manage_risk_configuration`.

6.2. Configuration changes are logged. A change to thresholds does not retroactively alter the classification of past requests — historical audit records reflect the configuration in effect at the time of the original decision.

## 7. Incident Reporting

7.1. High-risk security events generate a real-time alert to Admin users. Administrators are expected to review new alerts and either resolve or escalate the associated case within a reasonable operational timeframe.

7.2. If a genuine (non-simulated) security concern is identified that this policy does not clearly address, it should be escalated to the Governance Office directly rather than left in an unresolved case.

## 8. Related Policies

- AI Acceptable Use Policy (ORG-POL-01)
- Role & Access Control Policy (ORG-POL-02)
- Data Privacy & Classification Policy (ORG-POL-03)
