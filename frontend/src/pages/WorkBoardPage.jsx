import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { format } from 'date-fns'
import { ChevronDown, ChevronRight, KanbanSquare, RefreshCw } from 'lucide-react'

import api from '../utils/api'

const COLUMNS = [
  { id: 'todo', label: 'To Do' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'blocked', label: 'Blocked' },
  { id: 'completed', label: 'Completed' },
]

const STATUS_STYLES = {
  todo: 'text-warn border-warn/20 bg-warn/10',
  in_progress: 'text-accent border-accent/20 bg-accent/10',
  blocked: 'text-danger border-danger/20 bg-danger/10',
  completed: 'text-success border-success/20 bg-success/10',
}

const RISK_STYLES = {
  low: 'text-success border-success/20 bg-success/10',
  medium: 'text-warn border-warn/20 bg-warn/10',
  high: 'text-danger border-danger/20 bg-danger/10',
}

function formatPercent(value) {
  return `${Math.round((Number(value || 0)) * 100)}%`
}

function BoardColumn({ column, children }) {
  const { isOver, setNodeRef } = useDroppable({
    id: `column:${column.id}`,
    data: { status: column.id },
  })

  return (
    <div
      ref={setNodeRef}
      className={`rounded-2xl border p-4 min-h-[24rem] transition-colors ${
        isOver ? 'border-accent/30 bg-accent/5' : 'border-white/5 bg-white/[0.03]'
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-bold text-white">{column.label}</p>
        <span className="text-[10px] text-slate-500 font-mono">{children.length} items</span>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function AssignmentCard({ item, escalatingId, onEscalate }) {
  const [showChildren, setShowChildren] = useState(false)
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `assignment:${item.id}`,
    data: { assignmentId: item.id, status: item.status },
  })

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.65 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="rounded-2xl border border-white/8 bg-bg-800/80 p-4 cursor-grab active:cursor-grabbing"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">{item.title}</p>
          <p className="text-xs text-slate-400 mt-1">
            {item.assigned_to_user?.username || item.assigned_to_username || 'Unassigned'}
          </p>
        </div>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${RISK_STYLES[item.capacity_risk?.level] || RISK_STYLES.low}`}>
          {item.capacity_risk?.level || 'low'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
        <div className="rounded-xl border border-white/8 bg-white/5 p-2.5">
          <p className="text-slate-500 font-mono uppercase text-[10px]">KPI</p>
          <p className="text-white font-semibold mt-1">{formatPercent(item.kpi?.completion_ratio)}</p>
        </div>
        <div className="rounded-xl border border-white/8 bg-white/5 p-2.5">
          <p className="text-slate-500 font-mono uppercase text-[10px]">Due</p>
          <p className="text-white font-semibold mt-1">
            {item.due_date ? format(new Date(item.due_date), 'MMM dd') : 'Not set'}
          </p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${STATUS_STYLES[item.status] || STATUS_STYLES.todo}`}>
          {item.status.replace('_', ' ')}
        </span>
        <div className="flex items-center gap-2">
          {!!item.child_count && (
            <button
              type="button"
              onPointerDown={event => event.stopPropagation()}
              onMouseDown={event => event.stopPropagation()}
              onClick={event => {
                event.stopPropagation()
                setShowChildren(current => !current)
              }}
              className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono font-bold border border-accent/20 bg-accent/10 text-accent"
            >
              {showChildren ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
              {item.child_count} subtasks
            </button>
          )}
          {item.open_escalation && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border text-danger border-danger/20 bg-danger/10">
              escalated
            </span>
          )}
          <span className="text-[10px] text-slate-500 font-mono">
            {item.kpi?.total_completed_units || 0}/{item.kpi?.expected_units || 0}
          </span>
        </div>
      </div>

      {item.capacity_risk?.level === 'high' && !item.open_escalation && (
        <button
          type="button"
          onPointerDown={event => event.stopPropagation()}
          onMouseDown={event => event.stopPropagation()}
          onClick={event => {
            event.stopPropagation()
            onEscalate(item.id)
          }}
          disabled={escalatingId === item.id}
          className="mt-3 w-full rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs font-semibold text-danger hover:bg-danger/20 disabled:opacity-50"
        >
          {escalatingId === item.id ? 'Escalating...' : 'Escalate'}
        </button>
      )}

      {showChildren && !!item.children?.length && (
        <div className="mt-3 space-y-2 rounded-xl border border-white/8 bg-white/5 p-3">
          {item.children.map(child => (
            <ChildAssignmentPreview key={child.id} item={child} depth={0} />
          ))}
        </div>
      )}
    </div>
  )
}

function ChildAssignmentPreview({ item, depth }) {
  const [expanded, setExpanded] = useState(false)
  const hasChildren = !!item.children?.length

  return (
    <div style={{ paddingLeft: `${depth * 14}px` }}>
      <div className="flex items-center justify-between gap-3 rounded-xl border border-white/8 bg-bg-800/70 px-3 py-2.5">
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold text-white">{item.title}</p>
          <p className="mt-1 text-[10px] font-mono text-slate-500">
            {item.status.replace('_', ' ')} / {formatPercent(item.kpi?.completion_ratio)}
          </p>
        </div>
        {hasChildren && (
          <button type="button" onClick={() => setExpanded(current => !current)} className="text-slate-400 hover:text-white">
            {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </button>
        )}
      </div>
      {hasChildren && expanded && (
        <div className="mt-2 space-y-2">
          {item.children.map(child => (
            <ChildAssignmentPreview key={child.id} item={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function WorkBoardPage() {
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [escalatingId, setEscalatingId] = useState(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  const loadBoard = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/work/board')
      setAssignments(res.data.assignments || [])
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load work board.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadBoard()
  }, [loadBoard])

  const handleDragEnd = async event => {
    const activeId = event.active?.id
    const overId = event.over?.id
    if (!activeId || !overId) {
      return
    }

    const assignmentId = Number(String(activeId).replace('assignment:', ''))
    const activeItem = assignments.find(item => item.id === assignmentId)
    if (!activeItem) {
      return
    }

    let nextStatus = null
    if (String(overId).startsWith('column:')) {
      nextStatus = String(overId).replace('column:', '')
    } else {
      const targetAssignmentId = Number(String(overId).replace('assignment:', ''))
      nextStatus = assignments.find(item => item.id === targetAssignmentId)?.status || null
    }

    if (!nextStatus || nextStatus === activeItem.status) {
      return
    }

    const previousAssignments = assignments
    setAssignments(prev =>
      prev.map(item => (item.id === assignmentId ? { ...item, status: nextStatus } : item)),
    )

    try {
      const res = await api.patch(`/work/assignments/${assignmentId}/status`, { status: nextStatus })
      const updatedAssignment = res.data.assignment
      setAssignments(prev =>
        prev.map(item => (item.id === assignmentId ? updatedAssignment : item)),
      )
    } catch (err) {
      setAssignments(previousAssignments)
      setError(err?.response?.data?.error || 'Failed to update assignment status.')
    }
  }

  const handleEscalate = async assignmentId => {
    setEscalatingId(assignmentId)
    setError('')
    setSuccess('')
    try {
      const res = await api.post('/work/escalations', { assignment_id: assignmentId })
      const escalation = res.data.escalation
      setAssignments(prev =>
        prev.map(item => (
          item.id === assignmentId
            ? { ...item, open_escalation: escalation }
            : item
        )),
      )
      setSuccess('Escalation created.')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create escalation.')
    } finally {
      setEscalatingId(null)
    }
  }

  const groupedAssignments = COLUMNS.reduce((acc, column) => {
    acc[column.id] = assignments.filter(item => item.status === column.id)
    return acc
  }, {})

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Work Board</h1>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">
              Drag assignments between workflow states
            </p>
          </div>
          <button
            onClick={loadBoard}
            className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 hover:text-accent text-xs font-mono"
          >
            <RefreshCw size={13} className="inline mr-1.5" />
            Refresh
          </button>
        </div>

        {error && <p className="text-xs text-danger">{error}</p>}
        {success && <p className="text-xs text-success">{success}</p>}

        {loading ? (
          <div className="glass rounded-2xl border border-white/5 px-5 py-6 text-xs text-slate-500">Loading work board...</div>
        ) : (
          <div className="glass rounded-2xl border border-white/5 p-5">
            <div className="flex items-center gap-2 mb-5">
              <KanbanSquare size={16} className="text-accent" />
              <p className="text-sm font-bold text-white">Assignment Status Board</p>
            </div>

            <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {COLUMNS.map(column => (
                  <BoardColumn key={column.id} column={column}>
                    {groupedAssignments[column.id]?.map(item => (
                      <AssignmentCard
                        key={item.id}
                        item={item}
                        escalatingId={escalatingId}
                        onEscalate={handleEscalate}
                      />
                    )) || []}
                  </BoardColumn>
                ))}
              </div>
            </DndContext>
          </div>
        )}
      </div>
    </motion.div>
  )
}
