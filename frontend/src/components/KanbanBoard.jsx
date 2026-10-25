import { useEffect, useState } from 'react'
import { DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { format } from 'date-fns'
import { ChevronDown, ChevronRight, GitBranch, Github, TimerReset } from 'lucide-react'

import api from '../utils/api'

const COLUMNS = [
  { id: 'draft', label: 'Drafts' },
  { id: 'todo', label: 'To Do' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'review', label: 'Code Review' },
  { id: 'completed', label: 'Completed' },
]

const STATUS_STYLES = {
  draft: 'border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-200',
  todo: 'border-cyan-500/20 bg-cyan-500/10 text-cyan-200',
  in_progress: 'border-amber-500/20 bg-amber-500/10 text-amber-200',
  review: 'border-sky-500/20 bg-sky-500/10 text-sky-200',
  completed: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200',
}

function formatNumber(value) {
  return Number(value || 0).toFixed(2).replace(/\.00$/, '')
}

function BoardColumn({ column, count, children }) {
  const { isOver, setNodeRef } = useDroppable({
    id: `column:${column.id}`,
    data: { status: column.id },
  })

  return (
    <section
      ref={setNodeRef}
      className={`rounded-[28px] border p-4 transition-colors ${
        isOver ? 'border-cyan-400/40 bg-gray-800/90' : 'border-gray-700 bg-gray-800/75'
      }`}
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-white">{column.label}</p>
          <p className="mt-1 text-[10px] font-mono uppercase tracking-[0.18em] text-gray-500">{count} tasks</p>
        </div>
        <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em] ${STATUS_STYLES[column.id]}`}>
          {column.id.replace('_', ' ')}
        </span>
      </div>
      <div className="min-h-[14rem] space-y-3">{children}</div>
    </section>
  )
}

function TaskCard({ task, busyTaskId }) {
  const [expanded, setExpanded] = useState(false)
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `task:${task.id}`,
    data: { taskId: task.id, status: task.status },
  })

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.55 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="cursor-grab rounded-2xl border border-gray-700 bg-gray-900 p-4 shadow-[0_20px_40px_rgba(0,0,0,0.25)] active:cursor-grabbing"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white">{task.title}</p>
          <p className="mt-1 text-xs text-gray-400">{task.assigned_to_user?.username || task.assigned_to_username || 'Unassigned'}</p>
        </div>
        {busyTaskId === task.id && (
          <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-cyan-300">Saving</span>
        )}
      </div>

      {task.description && <p className="mt-3 text-xs leading-relaxed text-gray-400">{task.description}</p>}

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl border border-gray-700 bg-gray-800 px-3 py-2.5">
          <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-gray-500">Progress</p>
          <p className="mt-1 font-semibold text-white">{Math.round(Number(task.kpi?.completion_ratio || 0) * 100)}%</p>
        </div>
        <div className="rounded-xl border border-gray-700 bg-gray-800 px-3 py-2.5">
          <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-gray-500">Units</p>
          <p className="mt-1 font-semibold text-white">{formatNumber(task.kpi?.total_completed_units)}/{formatNumber(task.kpi?.expected_units)}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-gray-400">
        <span className="inline-flex items-center gap-1 rounded-full border border-gray-700 bg-gray-800 px-2.5 py-1">
          <TimerReset size={12} />
          {task.due_date ? format(new Date(task.due_date), 'MMM dd') : 'No due date'}
        </span>
        {task.github_issue_id && (
          <span className="inline-flex items-center gap-1 rounded-full border border-gray-700 bg-gray-800 px-2.5 py-1">
            <Github size={12} />
            {task.github_issue_id}
          </span>
        )}
        {task.github_branch && (
          <span className="inline-flex items-center gap-1 rounded-full border border-gray-700 bg-gray-800 px-2.5 py-1">
            <GitBranch size={12} />
            {task.github_branch}
          </span>
        )}
        {!!task.child_count && (
          <button
            type="button"
            onPointerDown={event => event.stopPropagation()}
            onMouseDown={event => event.stopPropagation()}
            onClick={event => {
              event.stopPropagation()
              setExpanded(current => !current)
            }}
            className="inline-flex items-center gap-1 rounded-full border border-gray-700 bg-gray-800 px-2.5 py-1 text-cyan-200"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {task.child_count} subtasks
          </button>
        )}
      </div>

      {expanded && !!task.children?.length && (
        <div className="mt-4 space-y-2 rounded-xl border border-gray-700 bg-gray-800/60 p-3">
          {task.children.map(child => (
            <TaskTreePreview key={child.id} task={child} depth={0} />
          ))}
        </div>
      )}
    </div>
  )
}

function TaskTreePreview({ task, depth }) {
  const [expanded, setExpanded] = useState(false)
  const hasChildren = !!task.children?.length

  return (
    <div style={{ paddingLeft: `${depth * 14}px` }}>
      <div className="flex items-center justify-between gap-2 rounded-lg border border-gray-700 bg-gray-900/80 px-3 py-2">
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold text-white">{task.title}</p>
          <p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-gray-500">
            {task.status.replace('_', ' ')} / {Math.round(Number(task.kpi?.completion_ratio || 0) * 100)}%
          </p>
        </div>
        {hasChildren && (
          <button type="button" onClick={() => setExpanded(current => !current)} className="text-gray-400 hover:text-white">
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        )}
      </div>
      {hasChildren && expanded && (
        <div className="mt-2 space-y-2">
          {task.children.map(child => (
            <TaskTreePreview key={child.id} task={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function KanbanBoard({ tasks = [], onTasksChange, onError, onSuccess }) {
  const [localTasks, setLocalTasks] = useState(tasks)
  const [busyTaskId, setBusyTaskId] = useState(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  useEffect(() => {
    setLocalTasks(tasks)
  }, [tasks])

  const handleDragEnd = async event => {
    const activeId = event.active?.id
    const overId = event.over?.id
    if (!activeId || !overId) return

    const taskId = Number(String(activeId).replace('task:', ''))
    const activeTask = localTasks.find(task => task.id === taskId)
    if (!activeTask) return

    let nextStatus = null
    if (String(overId).startsWith('column:')) {
      nextStatus = String(overId).replace('column:', '')
    } else if (String(overId).startsWith('task:')) {
      const targetId = Number(String(overId).replace('task:', ''))
      nextStatus = localTasks.find(task => task.id === targetId)?.status || null
    }
    if (!nextStatus || nextStatus === activeTask.status) return

    const previousTasks = localTasks
    const optimisticTasks = localTasks.map(task => (
      task.id === taskId ? { ...task, status: nextStatus } : task
    ))
    setLocalTasks(optimisticTasks)
    onTasksChange?.(optimisticTasks)
    setBusyTaskId(taskId)

    try {
      const res = await api.patch(`/work/assignments/${taskId}/status`, { status: nextStatus })
      const updatedTask = res.data.assignment
      const confirmedTasks = optimisticTasks.map(task => (task.id === taskId ? updatedTask : task))
      setLocalTasks(confirmedTasks)
      onTasksChange?.(confirmedTasks)
      onSuccess?.(`Task moved to ${nextStatus.replace('_', ' ')}.`)
    } catch (err) {
      setLocalTasks(previousTasks)
      onTasksChange?.(previousTasks)
      onError?.(err?.response?.data?.error || 'Failed to update task status.')
    } finally {
      setBusyTaskId(null)
    }
  }

  if (!localTasks.length) {
    return (
      <div className="rounded-[28px] border border-dashed border-gray-700 bg-gray-900 px-6 py-16 text-center">
        <p className="text-sm font-semibold text-white">No tasks in this project yet.</p>
        <p className="mt-2 text-xs text-gray-500">Generate AI tasks or create one manually to populate the Kanban board.</p>
      </div>
    )
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-5">
        {COLUMNS.map(column => {
          const columnTasks = localTasks.filter(task => task.status === column.id)
          return (
            <BoardColumn key={column.id} column={column} count={columnTasks.length}>
              {columnTasks.length ? (
                columnTasks.map(task => (
                  <TaskCard key={task.id} task={task} busyTaskId={busyTaskId} />
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-gray-700 bg-gray-900/70 px-4 py-8 text-center text-xs text-gray-500">
                  Drop a task here.
                </div>
              )}
            </BoardColumn>
          )
        })}
      </div>
    </DndContext>
  )
}
