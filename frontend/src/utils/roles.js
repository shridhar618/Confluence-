export const ROLE_CATALOG = [
  { value: 'admin', label: 'Admin', category: 'Leadership', color: 'text-purple-400', badge: 'ADMIN', desc: 'Full system access' },
  { value: 'hr', label: 'HR', category: 'Leadership', color: 'text-warn', badge: 'HR', desc: 'People and compliance workflows' },
  { value: 'intern', label: 'Intern', category: 'Engineering', color: 'text-accent', badge: 'INTERN', desc: 'Starter workspace access' },
  { value: 'employee', label: 'Employee', category: 'General', color: 'text-sky-300', badge: 'EMPLOYEE', desc: 'Standard employee access' },
  { value: 'developer', label: 'Developer', category: 'Engineering', color: 'text-cyan-300', badge: 'DEVELOPER', desc: 'Build and delivery workflows' },
  { value: 'senior developer', label: 'Senior Developer', category: 'Engineering', color: 'text-indigo-300', badge: 'SENIOR DEV', desc: 'Advanced engineering access' },
  { value: 'tech lead', label: 'Tech Lead', category: 'Leadership', color: 'text-violet-300', badge: 'TECH LEAD', desc: 'Technical planning and oversight' },
  { value: 'team lead', label: 'Team Lead', category: 'Leadership', color: 'text-fuchsia-300', badge: 'TEAM LEAD', desc: 'Team coordination and assignments' },
  { value: 'manager', label: 'Manager', category: 'Leadership', color: 'text-emerald-300', badge: 'MANAGER', desc: 'Manager workspace access' },
  { value: 'project manager', label: 'Project Manager', category: 'Leadership', color: 'text-lime-300', badge: 'PROJECT MGR', desc: 'Project planning and approvals' },
  { value: 'product manager', label: 'Product Manager', category: 'Leadership', color: 'text-amber-300', badge: 'PRODUCT MGR', desc: 'Roadmap and delivery coordination' },
  { value: 'qa engineer', label: 'QA Engineer', category: 'Engineering', color: 'text-orange-300', badge: 'QA', desc: 'Quality and validation workflows' },
  { value: 'ui/ux designer', label: 'UI/UX Designer', category: 'Engineering', color: 'text-pink-300', badge: 'DESIGN', desc: 'Design collaboration access' },
  { value: 'devops engineer', label: 'DevOps Engineer', category: 'Engineering', color: 'text-teal-300', badge: 'DEVOPS', desc: 'Infrastructure and release workflows' },
  { value: 'security', label: 'Security', category: 'Operations', color: 'text-rose-300', badge: 'SECURITY', desc: 'Security monitoring access' },
  { value: 'security analyst', label: 'Security Analyst', category: 'Operations', color: 'text-red-300', badge: 'SEC ANALYST', desc: 'Threat and audit workflows' },
  { value: 'finance', label: 'Finance', category: 'Business', color: 'text-yellow-300', badge: 'FINANCE', desc: 'Finance and reimbursement workflows' },
  { value: 'analyst', label: 'Analyst', category: 'Business', color: 'text-blue-300', badge: 'ANALYST', desc: 'Reporting and analysis access' },
  { value: 'operations', label: 'Operations', category: 'Operations', color: 'text-green-300', badge: 'OPERATIONS', desc: 'Operational process access' },
  { value: 'operations manager', label: 'Operations Manager', category: 'Leadership', color: 'text-green-200', badge: 'OPS MGR', desc: 'Operations planning and oversight' },
  { value: 'support engineer', label: 'Support Engineer', category: 'Operations', color: 'text-cyan-200', badge: 'SUPPORT', desc: 'Issue handling and support access' },
  { value: 'sales', label: 'Sales', category: 'Business', color: 'text-orange-200', badge: 'SALES', desc: 'Sales coordination access' },
  { value: 'marketing', label: 'Marketing', category: 'Business', color: 'text-pink-200', badge: 'MARKETING', desc: 'Campaign and content workflows' },
  { value: 'recruiter', label: 'Recruiter', category: 'Business', color: 'text-yellow-200', badge: 'RECRUITER', desc: 'Candidate and hiring coordination' },
  // Added for the AI-governance permission demo (Phase 1/2) — see
  // backend/app/services/permissions.py for the exact permission grants.
  { value: 'guest', label: 'Guest', category: 'General', color: 'text-slate-400', badge: 'GUEST', desc: 'Public information only' },
  { value: 'software engineer', label: 'Software Engineer', category: 'Engineering', color: 'text-cyan-400', badge: 'SW ENGINEER', desc: 'Full technical/project access' },
  { value: 'supervisor', label: 'Supervisor', category: 'Leadership', color: 'text-emerald-200', badge: 'SUPERVISOR', desc: 'Team-level oversight access' },
]

const ROLE_MAP = Object.fromEntries(ROLE_CATALOG.map(role => [role.value, role]))

export const FALLBACK_ROLE_NAMES = ROLE_CATALOG.map(role => role.label)

export function getRoleMeta(role) {
  const normalized = (role || '').toLowerCase()
  return ROLE_MAP[normalized] || {
    value: normalized || 'employee',
    label: normalized ? normalized.replace(/\b\w/g, c => c.toUpperCase()) : 'Employee',
    category: 'General',
    color: 'text-slate-300',
    badge: (normalized || 'employee').toUpperCase(),
    desc: 'Standard workspace access',
  }
}

export function isManagerRole(role) {
  return ['admin', 'hr', 'manager', 'team lead', 'tech lead', 'project manager', 'product manager', 'operations manager'].includes((role || '').toLowerCase())
}

export function getRolePillClass(role) {
  const normalized = (role || '').toLowerCase()
  if (normalized === 'admin') return 'text-purple-400 bg-purple-400/10 border-purple-400/20'
  if (normalized === 'hr') return 'text-warn bg-warn/10 border-warn/20'
  if (normalized === 'intern') return 'text-accent bg-accent/10 border-accent/20'
  return 'text-slate-200 bg-white/5 border-white/10'
}

export function groupRoles(roleNames = FALLBACK_ROLE_NAMES) {
  return roleNames.reduce((acc, roleName) => {
    const meta = getRoleMeta(roleName.toLowerCase())
    const bucket = meta.category || 'General'
    if (!acc[bucket]) acc[bucket] = []
    acc[bucket].push(roleName)
    return acc
  }, {})
}
