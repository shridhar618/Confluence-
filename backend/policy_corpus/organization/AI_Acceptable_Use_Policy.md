# AI Acceptable Use Policy

**Document ID:** ORG-POL-01
**Category:** Acceptable Use
**Owner:** SecureAI Governance Office
**Version:** 1.0
**Applies to:** All employees and contractors with access to the SecureAI governance assistant

## 1. Purpose

This policy defines how employees may use the organization's internal AI assistant ("SecureAI Assistant"). It exists so that AI use accelerates work without creating unauthorized disclosure of sensitive information, unsafe system access, or organizational liability.

## 2. Scope

This policy applies to every interaction with the SecureAI Assistant, regardless of the requester's role, department, or seniority. It applies whether the request is made through the chat interface, the API, or any integration built on top of it.

## 3. Permitted Uses

3.1. Employees may use the SecureAI Assistant for any task within the scope of their assigned role and the information their role is authorized to access, as defined in the Role & Access Control Policy (ORG-POL-02).

3.2. Permitted uses include, without limitation: drafting and editing internal documents, writing and debugging code within the employee's own project scope, summarizing publicly available or role-appropriate internal material, and answering general workplace questions (benefits, policies, processes).

3.3. Employees holding the `use_ai_assistant` permission (see ORG-POL-02 §2) may use the assistant for any purpose consistent with §3.1–3.2.

## 4. Prohibited Uses

4.1. Employees must not use the SecureAI Assistant to request, generate, or attempt to extract:

  a. Compensation, payroll, or benefits data for any employee other than themselves, unless the requester holds the `view_employee_salary` permission;

  b. Personally identifiable information (PII) of colleagues, customers, or third parties, unless the requester holds the `view_employee_pii` permission and the request is for a legitimate work purpose;

  c. Credentials, API keys, private keys, passwords, or any other authentication material, under any circumstance, regardless of role;

  d. Content that would require bypassing, disabling, or evading the assistant's governance controls (for example, prompt injection attempts, "ignore previous instructions" framings, or requests to roleplay as an unrestricted system).

4.2. Employees must not use the assistant to circumvent access restrictions that would otherwise apply if the same information were requested through a standard system (e.g., asking the assistant to "summarize" a report the employee is not authorized to view directly).

4.3. Employees must not submit organizational confidential or proprietary material to any AI system outside the organization's approved tooling (see AI Security & Incident Response Policy, ORG-POL-04, §4).

## 5. Role-Based Usage Expectations

5.1. **Guest** accounts may only request publicly available information (`view_public_information`). Any other request will be treated as unauthorized under this policy.

5.2. **Intern** accounts may request general workplace guidance and limited project information (`view_project_information_limited`). Interns must not request compensation, credential, or classified information; such requests are blocked automatically and logged (see ORG-POL-04 §2).

5.3. **Software Engineer**, **Manager**, and **Supervisor** accounts may request full technical/project information (`view_project_information_full`) relevant to their work.

5.4. **HR** accounts may request authorized employee PII and compensation information (`view_employee_pii`, `view_employee_salary`) strictly for HR business purposes. Responses containing such data are automatically masked for any field not directly relevant to the request (see ORG-POL-03 §4).

5.5. **Admin** accounts are authorized for governance and audit administration and may access aggregate, de-identified usage data across all roles for oversight purposes.

## 6. Consequences of Violations

6.1. A single attempted violation of §4 results in the request being blocked and logged, with an explanation returned to the employee.

6.2. Repeated attempted violations accumulate risk under the organization's risk scoring model. Once an employee's cumulative risk score crosses the configured threshold, a Governance Case is opened for administrator review (see ORG-POL-04 §5).

6.3. Consequential actions — warnings, temporary restriction, or escalation — are always decided by a human administrator reviewing the case. The system does not autonomously terminate access or employment.

## 7. Related Policies

- Role & Access Control Policy (ORG-POL-02)
- Data Privacy & Classification Policy (ORG-POL-03)
- AI Security & Incident Response Policy (ORG-POL-04)
