# Role & Access Control Policy

**Document ID:** ORG-POL-02
**Category:** Access Control
**Owner:** SecureAI Governance Office
**Version:** 1.0
**Applies to:** All roles provisioned in the organization's identity system

## 1. Purpose

This policy defines the organization's role catalog, the permissions attached to each role, and the principle of least privilege that governs how those permissions are assigned, reviewed, and enforced — including by the SecureAI Assistant.

## 2. Permission Catalog

The following permissions exist across the organization's systems, including the AI governance layer:

| Permission | Description |
|---|---|
| `view_public_information` | View public/non-sensitive company information |
| `view_project_information_limited` | View limited project information relevant to assigned work |
| `view_project_information_full` | View full technical/project information |
| `view_employee_pii` | View authorized employee personal information |
| `view_employee_salary` | View employee compensation/salary information |
| `use_ai_assistant` | Use the SecureAI governance assistant |
| `ai_governance_admin` | View audit logs, risk events, and governance cases |
| `manage_policies` | Upload, re-index, enable/disable policy documents |
| `manage_risk_configuration` | Edit risk engine weights and thresholds |
| `manage_users` | Create users and assign roles |
| `system_configuration_admin` | Change system-wide configuration |

## 3. Role Definitions

3.1. **Guest** — External or unauthenticated-adjacent access. Granted: `view_public_information` only. Guests hold no AI-assistant usage right and no access to any employee, project, or financial data.

3.2. **Intern** — Temporary or early-career staff. Granted: `view_public_information`, `view_project_information_limited`, `use_ai_assistant`. Interns are explicitly **not** granted `view_employee_pii` or `view_employee_salary` under any circumstance, regardless of the project they are assigned to.

3.3. **Software Engineer** — Technical staff. Granted: `view_public_information`, `view_project_information_full`, `use_ai_assistant`. Software Engineers are not granted employee PII or salary access; their scope is technical/project information only.

3.4. **HR** — Human Resources staff. Granted: `view_public_information`, `view_project_information_limited`, `view_employee_pii`, `view_employee_salary`, `use_ai_assistant`. HR is the only non-Admin role authorized for compensation data, reflecting HR's operational need to process payroll, benefits, and personnel matters.

3.5. **Manager** — People and project management staff. Granted: `view_public_information`, `view_project_information_full`, `view_employee_pii`, `use_ai_assistant`. Managers may view PII relevant to their direct reports (e.g., contact details, role history) but are **not** granted `view_employee_salary` — compensation review is an HR function, not a line-management function, under this policy.

3.6. **Supervisor** — Team-level oversight staff, one level below Manager. Granted: `view_public_information`, `view_project_information_full`, `use_ai_assistant`. Supervisors are not granted employee PII or salary access; this reflects a narrower scope than Manager, consistent with fewer direct administrative responsibilities.

3.7. **Admin** — Governance and system administration. Granted: all permissions listed in §2, including `ai_governance_admin`, `manage_policies`, `manage_risk_configuration`, `manage_users`, and `system_configuration_admin`. Admin access is reserved for governance office staff and system owners.

3.8. **Other seeded roles** (e.g., Developer, Finance, Sales, Operations, and related roles not listed in §3.1–3.7) default to the same permission set as Intern (`view_public_information`, `view_project_information_limited`, `use_ai_assistant`) until an explicit role-specific mapping is added to the permission catalog. This default is intentionally conservative: an unmapped role is treated as having no elevated access rather than being assumed trustworthy.

## 4. Principle of Least Privilege

4.1. No role is granted a permission beyond what is required for its defined function. In particular:

  a. Only HR and Admin may view compensation data.

  b. Only HR, Manager, and Admin may view employee PII.

  c. Technical roles (Software Engineer, Supervisor) receive full project/technical visibility but no personnel-data visibility, since project information and personnel information serve different operational needs.

4.2. Any request that falls outside a role's granted permissions is treated as **unauthorized**, not merely "unusual" — the AI governance pipeline (see Data Privacy & Classification Policy, ORG-POL-03) enforces this distinction strictly rather than making a judgment call per request.

## 5. Access Review

5.1. Role-to-permission mappings are reviewed by the Governance Office. Changes to the mapping require an Admin action and are recorded in the audit log.

5.2. A user's effective permissions are always determined by their currently assigned role at the time of the request, not by any role they may have previously held.

## 6. Related Policies

- AI Acceptable Use Policy (ORG-POL-01)
- Data Privacy & Classification Policy (ORG-POL-03)
- AI Security & Incident Response Policy (ORG-POL-04)
