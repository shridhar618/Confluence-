import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronRight, ClipboardList, FolderClosed, Plus, RefreshCw, Users } from 'lucide-react'

import KanbanBoard from '../components/KanbanBoard'
import ProjectManagementModal from '../components/ProjectManagementModal'
import api from '../utils/api'

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-[24px] border border-white/8 bg-white/[0.03] p-4">
      <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  )
}

const emptyTaskForm = {
  title: '',
  description: '',
  assigned_to_user_id: '',
  expected_units: '',
  weight: '1',
  due_date: '',
  parent_id: '',
}

const emptyProjectForm = {
  name: '',
  description: '',
}

export default function WorkAssignmentsWorkspacePage() {
  const [projects, setProjects] = useState([])
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [users, setUsers] = useState([])
  const [tasks, setTasks] = useState([])
  const [pendingTasks, setPendingTasks] = useState([])
  const [taskForm, setTaskForm] = useState(emptyTaskForm)
  const [projectForm, setProjectForm] = useState(emptyProjectForm)
  const [memberUserId, setMemberUserId] = useState('')
  const [loading, setLoading] = useState(true)
  const [boardLoading, setBoardLoading] = useState(false)
  const [projectModalOpen, setProjectModalOpen] = useState(false)
  const [submittingTask, setSubmittingTask] = useState(false)
  const [creatingProject, setCreatingProject] = useState(false)
  const [expandedTaskIds, setExpandedTaskIds] = useState({})
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const selectedProject = useMemo(
    () => projects.find(project => String(project.id) === String(selectedProjectId)) || null,
    [projects, selectedProjectId],
  )

  const projectMembers = useMemo(
    () => (selectedProject?.members || []).map(member => member.user).filter(Boolean),
    [selectedProject],
  )

  const assignableUsers = useMemo(
    () => (projectMembers.length ? projectMembers : users),
    [projectMembers, users],
  )

  const memberOptions = useMemo(() => {
    const memberIds = new Set((selectedProject?.members || []).map(member => member.user_id))
    return users.filter(user => !memberIds.has(user.id))
  }, [selectedProject, users])

  const taskTree = useMemo(() => {
    const byId = new Map(tasks.map(task => [task.id, { ...task, children: [] }]))
    const roots = []

    byId.forEach(task => {
      if (task.parent_id && byId.has(task.parent_id)) {
        byId.get(task.parent_id).children.push(task)
      } else {
        roots.push(task)
      }
    })

    const sortNodes = nodes => {
      nodes.sort((left, right) => new Date(right.updated_at) - new Date(left.updated_at))
      nodes.forEach(node => sortNodes(node.children))
      return nodes
    }

    return sortNodes(roots)
  }, [tasks])

  const flatTaskOptions = useMemo(() => {
    const items = []
    const visit = (nodes, depth = 0) => {
      nodes.forEach(node => {
        items.push({ ...node, depth })
        visit(node.children, depth + 1)
      })
    }
    visit(taskTree)
    return items
  }, [taskTree])

  const flattenTaskNodes = useCallback(nodes => {
    const items = []
    const visit = currentNodes => {
      currentNodes.forEach(node => {
        const { children = [], ...task } = node
        items.push(task)
        visit(children)
      })
    }
    visit(nodes)
    return items
  }, [])

  const boardTasks = useMemo(
    () => taskTree.filter(task => ['draft', 'todo', 'in_progress', 'review', 'completed'].includes(task.status)),
    [taskTree],
  )

  const mergeProject = useCallback(project => {
    setProjects(prev => {
      const exists = prev.some(item => item.id === project.id)
      if (!exists) return [project, ...prev]
      return prev.map(item => (item.id === project.id ? project : item))
    })
  }, [])

  const loadWorkspace = useCallback(async preferredProjectId => {
    setLoading(true)
    setError('')
    try {
      const [projectsRes, usersRes] = await Promise.all([api.get('/projects'), api.get('/users')])
      const nextProjects = projectsRes.data.projects || []
      setProjects(nextProjects)
      setUsers(usersRes.data.users || [])

      const nextSelected =
        nextProjects.find(project => String(project.id) === String(preferredProjectId)) ||
        nextProjects.find(project => !project.is_archived) ||
        nextProjects[0] ||
        null
      setSelectedProjectId(nextSelected ? String(nextSelected.id) : '')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load project workspace.')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadProjectTasks = useCallback(async projectId => {
    if (!projectId) {
      setTasks([])
      setPendingTasks([])
      return
    }

    setBoardLoading(true)
    setError('')
    try {
      const [tasksRes, pendingRes] = await Promise.all([
        api.get('/work/assignments', { params: { project_id: projectId } }),
        api.get(`/projects/${projectId}/tasks/pending`),
      ])
      setTasks(tasksRes.data.assignments || [])
      setPendingTasks(pendingRes.data.tasks || [])
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load project tasks.')
    } finally {
      setBoardLoading(false)
    }
  }, [])

  useEffect(() => {
    loadWorkspace()
  }, [loadWorkspace])

  useEffect(() => {
    loadProjectTasks(selectedProjectId)
  }, [loadProjectTasks, selectedProjectId])

  const handleRefresh = async () => {
    await loadWorkspace(selectedProjectId)
    await loadProjectTasks(selectedProjectId)
  }

  const handleTaskFieldChange = event => {
    const { name, value } = event.target
    setTaskForm(prev => ({ ...prev, [name]: value }))
  }

  const toggleTaskExpanded = taskId => {
    setExpandedTaskIds(prev => ({ ...prev, [taskId]: !prev[taskId] }))
  }

  const startSubtask = task => {
    setTaskForm(prev => ({
      ...prev,
      parent_id: String(task.id),
      assigned_to_user_id: prev.assigned_to_user_id || String(task.assigned_to_user_id || ''),
    }))
  }

  const handleBoardTasksChange = useCallback(updatedRootTasks => {
    setTasks(flattenTaskNodes(updatedRootTasks))
  }, [flattenTaskNodes])

  const handleProjectFieldChange = event => {
    const { name, value } = event.target
    setProjectForm(prev => ({ ...prev, [name]: value }))
  }

  const handleCreateTask = async event => {
    event.preventDefault()
    if (!selectedProjectId) {
      setError('Select a project before creating tasks.')
      return
    }

    setSubmittingTask(true)
    setError('')
    setSuccess('')
    try {
      await api.post('/work/assignments', {
        ...taskForm,
        project_id: Number(selectedProjectId),
        assigned_to_user_id: Number(taskForm.assigned_to_user_id),
        expected_units: Number(taskForm.expected_units || 0),
        weight: Number(taskForm.weight || 0),
        parent_id: taskForm.parent_id ? Number(taskForm.parent_id) : null,
      })
      setTaskForm(emptyTaskForm)
      setSuccess('Task added to the active project.')
      await loadProjectTasks(selectedProjectId)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create task.')
    } finally {
      setSubmittingTask(false)
    }
  }

  const handleCreateProject = async event => {
    event.preventDefault()
    setCreatingProject(true)
    setError('')
    setSuccess('')
    try {
      const res = await api.post('/projects', projectForm)
      const nextProjectId = String(res.data.project.id)
      mergeProject(res.data.project)
      setSelectedProjectId(nextProjectId)
      setProjectForm(emptyProjectForm)
      setProjectModalOpen(false)
      setSuccess('Project created.')
      await loadWorkspace(nextProjectId)
      await loadProjectTasks(nextProjectId)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create project.')
    } finally {
      setCreatingProject(false)
    }
  }

  const handleToggleArchive = async project => {
    setError('')
    setSuccess('')
    try {
      const res = await api.patch(`/projects/${project.id}`, { is_archived: !project.is_archived })
      mergeProject(res.data.project)
      setSuccess(project.is_archived ? 'Project unarchived.' : 'Project archived.')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to update project state.')
    }
  }

  const handleAddMember = async () => {
    if (!selectedProjectId || !memberUserId) return
    setError('')
    setSuccess('')
    try {
      const res = await api.post(`/projects/${selectedProjectId}/members`, { user_id: Number(memberUserId) })
      mergeProject(res.data.project)
      setMemberUserId('')
      setSuccess('User added to project.')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to add project member.')
    }
  }

  const handleRemoveMember = async userId => {
    if (!selectedProjectId) return
    setError('')
    setSuccess('')
    try {
      const res = await api.delete(`/projects/${selectedProjectId}/members/${userId}`)
      mergeProject(res.data.project)
      setSuccess('User removed from project.')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to remove project member.')
    }
  }

  return (
    <>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
        <div className="space-y-6 px-6 py-6">
          <div className="rounded-[32px] border border-white/8 bg-[radial-gradient(circle_at_top_left,rgba(0,229,255,0.12),transparent_35%),linear-gradient(135deg,rgba(8,16,31,0.96),rgba(7,12,20,0.92))] p-6 shadow-[0_28px_80px_rgba(4,9,20,0.38)]">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-2xl">
                <p className="text-[10px] font-mono uppercase tracking-[0.24em] text-accent">Project-based Workflow</p>
                <h1 className="mt-3 text-3xl font-semibold text-white">Work Assignments</h1>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">
                  Select a live project, create manual tasks inside it, and move AI-generated work across the Kanban board from Drafts through completion.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button type="button" onClick={() => setProjectModalOpen(true)} className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm font-semibold text-white transition hover:border-accent/30 hover:text-accent">
                  <FolderClosed size={16} />
                  Manage Projects
                </button>
                <button type="button" onClick={handleRefresh} className="inline-flex items-center gap-2 rounded-2xl border border-accent/20 bg-accent/10 px-4 py-3 text-sm font-semibold text-accent transition hover:bg-accent/15">
                  <RefreshCw size={16} />
                  Refresh
                </button>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr_1fr_1fr]">
              <div className="rounded-[24px] border border-white/8 bg-[#08111f]/80 p-4">
                <label className="mb-2 block text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">Active Project</label>
                <select value={selectedProjectId} onChange={event => setSelectedProjectId(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-[#08111f] px-4 py-3 text-sm text-white outline-none transition focus:border-accent/40">
                  <option value="">Select a project</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.name}{project.is_archived ? ' (Archived)' : ''}
                    </option>
                  ))}
                </select>
                <p className="mt-3 text-xs text-slate-500">{selectedProject?.description || 'Choose a project to load its Kanban workspace.'}</p>
              </div>
              <Stat label="Board Tasks" value={boardTasks.length} hint="Visible on the Kanban board" />
              <Stat label="Draft Tasks" value={boardTasks.filter(task => task.status === 'draft').length} hint="Waiting in the Drafts lane" />
              <Stat label="Project Members" value={selectedProject?.member_count || 0} hint={selectedProject?.is_archived ? 'Archived project' : 'Assignable users'} />
            </div>
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}
          {success && <p className="text-sm text-success">{success}</p>}

          {loading ? (
            <div className="glass rounded-[28px] border border-white/8 px-6 py-12 text-sm text-slate-500">Loading workspace...</div>
          ) : !selectedProject ? (
            <div className="glass rounded-[28px] border border-dashed border-white/10 px-6 py-14 text-center">
              <p className="text-base font-semibold text-white">No project selected</p>
              <p className="mt-2 text-sm text-slate-500">Create or select a project to unlock the Kanban workspace.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-[340px_minmax(0,1fr)_360px]">
              <form onSubmit={handleCreateTask} className="glass rounded-[28px] border border-white/8 p-5">
                <div className="mb-5 flex items-center gap-2">
                  <ClipboardList size={16} className="text-accent" />
                  <div>
                    <p className="text-sm font-semibold text-white">Manual Task Creation</p>
                    <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-slate-500">{selectedProject.name}</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <input name="title" value={taskForm.title} onChange={handleTaskFieldChange} required disabled={selectedProject.is_archived} placeholder="Task title" className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50" />
                  <textarea name="description" value={taskForm.description} onChange={handleTaskFieldChange} rows={4} disabled={selectedProject.is_archived} placeholder="Describe the work item" className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50" />
                  <select name="parent_id" value={taskForm.parent_id} onChange={handleTaskFieldChange} disabled={selectedProject.is_archived} className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50">
                    <option value="">Top-level task</option>
                    {flatTaskOptions.map(task => (
                      <option key={task.id} value={task.id}>
                        {'  '.repeat(task.depth)}{task.title}
                      </option>
                    ))}
                  </select>
                  <select name="assigned_to_user_id" value={taskForm.assigned_to_user_id} onChange={handleTaskFieldChange} required disabled={selectedProject.is_archived} className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50">
                    <option value="">Assign to</option>
                    {assignableUsers.map(user => (
                      <option key={user.id} value={user.id}>{user.username} ({user.role})</option>
                    ))}
                  </select>
                  <div className="grid grid-cols-2 gap-3">
                    <input name="expected_units" type="number" min="0" step="0.01" value={taskForm.expected_units} onChange={handleTaskFieldChange} required disabled={selectedProject.is_archived} placeholder="Expected units" className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50" />
                    <input name="weight" type="number" min="0" step="0.01" value={taskForm.weight} onChange={handleTaskFieldChange} required disabled={selectedProject.is_archived} placeholder="Weight" className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50" />
                  </div>
                  <input name="due_date" type="date" value={taskForm.due_date} onChange={handleTaskFieldChange} disabled={selectedProject.is_archived} className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40 disabled:opacity-50" />
                </div>

                <p className="mt-4 rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-xs text-slate-500">
                  {taskForm.parent_id
                    ? `New subtask will be created under ${flatTaskOptions.find(task => String(task.id) === String(taskForm.parent_id))?.title || 'the selected parent'}.`
                    : (projectMembers.length ? 'Assignee dropdown is scoped to project members.' : 'No members added yet, so all users are available here.')}
                </p>

                <button type="submit" disabled={submittingTask || selectedProject.is_archived} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-accent/30 bg-accent/10 px-4 py-3 text-sm font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-50">
                  <Plus size={16} />
                  {submittingTask ? 'Creating...' : 'Create Task'}
                </button>
              </form>

              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
                  <Stat label="Drafts" value={boardTasks.filter(task => task.status === 'draft').length} hint="AI-generated intake" />
                  <Stat label="To Do" value={boardTasks.filter(task => task.status === 'todo').length} hint="Queued work" />
                  <Stat label="In Progress" value={boardTasks.filter(task => task.status === 'in_progress').length} hint="Active execution" />
                  <Stat label="Review" value={boardTasks.filter(task => task.status === 'review').length} hint="Awaiting sign-off" />
                  <Stat label="Completed" value={boardTasks.filter(task => task.status === 'completed').length} hint="Delivered" />
                </div>

                {boardLoading ? (
                  <div className="glass rounded-[28px] border border-white/8 px-6 py-12 text-sm text-slate-500">Loading project board...</div>
                ) : (
                  <KanbanBoard tasks={boardTasks} onTasksChange={handleBoardTasksChange} onError={setError} onSuccess={setSuccess} />
                )}
              </div>

              <div className="space-y-5">
                <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-5">
                  <p className="text-sm font-semibold text-white">AI Intake</p>
                  <p className="mt-2 text-sm text-slate-400">
                    Draft tasks are now part of the Kanban board itself. Drag a task from <span className="font-semibold text-fuchsia-200">Drafts</span> to <span className="font-semibold text-cyan-200">To Do</span> to approve it into active delivery.
                  </p>
                  <div className="mt-4 rounded-2xl border border-white/10 bg-[#08111f] px-4 py-4 text-sm text-slate-400">
                    <p>{pendingTasks.length} draft tasks currently exist for this project.</p>
                    <p className="mt-2 text-xs text-slate-500">The dedicated pending endpoint is still loaded in the background for count verification, but the visual workflow now lives on the board.</p>
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <Users size={16} className="text-accent" />
                    <p className="text-sm font-semibold text-white">Task Tree</p>
                  </div>
                  <div className="space-y-3">
                    {!taskTree.length ? (
                      <div className="rounded-2xl border border-dashed border-white/10 bg-[#08111f] px-4 py-6 text-xs text-slate-500">
                        No tasks in this project yet.
                      </div>
                    ) : (
                      taskTree.map(task => (
                        <TaskTreeNode
                          key={task.id}
                          task={task}
                          depth={0}
                          expandedTaskIds={expandedTaskIds}
                          onToggle={toggleTaskExpanded}
                          onCreateSubtask={startSubtask}
                        />
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>

      <ProjectManagementModal
        open={projectModalOpen}
        onClose={() => setProjectModalOpen(false)}
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={projectId => setSelectedProjectId(String(projectId))}
        createForm={projectForm}
        onCreateFormChange={handleProjectFieldChange}
        onCreateProject={handleCreateProject}
        creatingProject={creatingProject}
        memberUserId={memberUserId}
        onMemberUserIdChange={setMemberUserId}
        onAddMember={handleAddMember}
        memberOptions={memberOptions}
        onRemoveMember={handleRemoveMember}
        onToggleArchive={handleToggleArchive}
      />
    </>
  )
}

function TaskTreeNode({ task, depth, expandedTaskIds, onToggle, onCreateSubtask }) {
  const hasChildren = (task.children || []).length > 0
  const isExpanded = expandedTaskIds[task.id] ?? true

  return (
    <div className="rounded-2xl border border-white/10 bg-[#08111f]">
      <div className="flex items-start justify-between gap-3 px-4 py-3">
        <div className="min-w-0 flex-1" style={{ paddingLeft: `${depth * 14}px` }}>
          <div className="flex items-center gap-2">
            {hasChildren ? (
              <button
                type="button"
                onClick={() => onToggle(task.id)}
                className="rounded-md border border-white/10 p-1 text-slate-400 hover:text-white"
              >
                {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
            ) : (
              <span className="w-6" />
            )}
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{task.title}</p>
              <p className="mt-1 text-[11px] text-slate-500">
                {task.status.replace('_', ' ')} / {Math.round(Number(task.kpi?.completion_ratio || 0) * 100)}% / {task.child_count || 0} children
              </p>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => onCreateSubtask(task)}
          className="rounded-xl border border-accent/20 bg-accent/10 px-2.5 py-1.5 text-[11px] font-semibold text-accent hover:bg-accent/15"
        >
          Subtask
        </button>
      </div>
      {hasChildren && isExpanded && (
        <div className="space-y-3 pb-3">
          {task.children.map(child => (
            <TaskTreeNode
              key={child.id}
              task={child}
              depth={depth + 1}
              expandedTaskIds={expandedTaskIds}
              onToggle={onToggle}
              onCreateSubtask={onCreateSubtask}
            />
          ))}
        </div>
      )}
    </div>
  )
}
