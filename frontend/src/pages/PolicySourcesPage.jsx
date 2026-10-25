import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { format } from 'date-fns'
import {
  Database, X, RefreshCw, Trash2, Eye, Ban, CheckCircle2, BookOpen,
} from 'lucide-react'
import api from '../utils/api'

const CATEGORY_COLORS = {
  'AI Governance':  'text-accent bg-accent/10 border-accent/20',
  'Privacy':        'text-purple bg-purple/10 border-purple/20',
  'Security':       'text-danger bg-danger/10 border-danger/20',
  'Access Control': 'text-warn bg-warn/10 border-warn/20',
  'Acceptable Use': 'text-success bg-success/10 border-success/20',
}

function CategoryBadge({ category }) {
  const cls = CATEGORY_COLORS[category] || 'text-slate-400 bg-white/5 border-white/10'
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${cls}`}>{category}</span>
}

export default function PolicySourcesPage() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [ragStatus, setRagStatus] = useState(null)
  const [viewing, setViewing] = useState(null)
  const [viewingChunks, setViewingChunks] = useState([])
  const [pending, setPending] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [docsRes, statusRes] = await Promise.all([
        api.get('/policies'),
        api.get('/policies/rag-status'),
      ])
      setDocuments(docsRes.data.documents || [])
      setRagStatus(statusRes.data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const viewChunks = async (doc) => {
    setViewing(doc)
    setViewingChunks([])
    try {
      const res = await api.get(`/policies/${doc.id}/chunks`)
      setViewingChunks(res.data.chunks || [])
    } catch {
      setViewingChunks([])
    }
  }

  const toggleStatus = async (doc) => {
    setPending(doc.id)
    try {
      const newStatus = doc.status === 'active' ? 'disabled' : 'active'
      await api.put(`/policies/${doc.id}/status`, { status: newStatus })
      load()
    } finally {
      setPending(null)
    }
  }

  const reindex = async (doc) => {
    setPending(doc.id)
    try {
      await api.post(`/policies/${doc.id}/reindex`)
      load()
    } catch {
      // surfaced via ragStatus.ready check below; a 503 here usually means
      // sentence-transformers/qdrant-client aren't installed in this env
    } finally {
      setPending(null)
    }
  }

  const remove = async (doc) => {
    if (!window.confirm(`Delete "${doc.name}" and all its indexed chunks? This cannot be undone.`)) return
    setPending(doc.id)
    try {
      await api.delete(`/policies/${doc.id}`)
      load()
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Policy Sources</h1>
          <p className="text-xs text-slate-500 mt-0.5">Governance corpus — NIST/OWASP/DPDP frameworks and organization policies</p>
        </div>
        <button onClick={load} className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-accent transition-colors">
          <RefreshCw size={14} />
        </button>
      </motion.div>

      {ragStatus && !ragStatus.ready && (
        <div className="glass rounded-xl p-3 border border-warn/20 bg-warn/5 text-xs text-warn/90">
          RAG pipeline not fully set up in this environment
          {!ragStatus.sentence_transformers_installed && ' — sentence-transformers not installed'}
          {!ragStatus.qdrant_client_installed && ' — qdrant-client not installed'}
          {!ragStatus.index_exists && ' — index not yet built (run scripts/ingest_policies.py)'}.
          Documents can still be viewed/disabled/deleted; re-indexing requires the dependencies above.
        </div>
      )}

      <div className="glass rounded-2xl border border-white/5 overflow-hidden">
        {loading && <div className="p-10 text-center text-xs text-slate-500">Loading policy sources...</div>}
        {!loading && error && <div className="p-10 text-center text-xs text-danger">Couldn't load policy documents.</div>}
        {!loading && !error && documents.length === 0 && (
          <div className="p-10 text-center">
            <Database size={28} className="mx-auto text-slate-700 mb-2" />
            <p className="text-sm text-slate-400">No policy documents indexed yet</p>
            <p className="text-[11px] text-slate-600 mt-1">Run scripts/ingest_policies.py to build the corpus</p>
          </div>
        )}
        {!loading && !error && documents.length > 0 && (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5 text-slate-500 uppercase text-[10px] tracking-wider">
                <th className="text-left px-4 py-3 font-semibold">Document</th>
                <th className="text-left px-4 py-3 font-semibold">Category</th>
                <th className="text-left px-4 py-3 font-semibold">Version</th>
                <th className="text-left px-4 py-3 font-semibold">Status</th>
                <th className="text-left px-4 py-3 font-semibold">Chunks</th>
                <th className="text-left px-4 py-3 font-semibold">Last Indexed</th>
                <th className="text-right px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 text-slate-200 font-medium">{doc.name}</td>
                  <td className="px-4 py-3"><CategoryBadge category={doc.category} /></td>
                  <td className="px-4 py-3 text-slate-500 font-mono">{doc.version}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${doc.status === 'active' ? 'text-success bg-success/10 border-success/20' : 'text-slate-500 bg-white/5 border-white/10'}`}>
                      {doc.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{doc.chunk_count}</td>
                  <td className="px-4 py-3 text-slate-500">{doc.last_indexed_at ? format(new Date(doc.last_indexed_at), 'MMM d, HH:mm') : 'Never'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1.5">
                      <button title="View chunks" onClick={() => viewChunks(doc)} className="w-7 h-7 rounded-lg bg-white/5 hover:bg-accent/10 flex items-center justify-center text-slate-400 hover:text-accent transition-colors">
                        <Eye size={13} />
                      </button>
                      <button title="Re-index" disabled={pending === doc.id} onClick={() => reindex(doc)} className="w-7 h-7 rounded-lg bg-white/5 hover:bg-accent/10 flex items-center justify-center text-slate-400 hover:text-accent transition-colors disabled:opacity-30">
                        <RefreshCw size={13} className={pending === doc.id ? 'animate-spin' : ''} />
                      </button>
                      <button title={doc.status === 'active' ? 'Disable' : 'Enable'} disabled={pending === doc.id} onClick={() => toggleStatus(doc)} className="w-7 h-7 rounded-lg bg-white/5 hover:bg-warn/10 flex items-center justify-center text-slate-400 hover:text-warn transition-colors disabled:opacity-30">
                        {doc.status === 'active' ? <Ban size={13} /> : <CheckCircle2 size={13} />}
                      </button>
                      <button title="Delete" disabled={pending === doc.id} onClick={() => remove(doc)} className="w-7 h-7 rounded-lg bg-white/5 hover:bg-danger/10 flex items-center justify-center text-slate-400 hover:text-danger transition-colors disabled:opacity-30">
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <AnimatePresence>
        {viewing && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setViewing(null)} className="fixed inset-0 bg-black/60 z-40" />
            <motion.div
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ duration: 0.25, ease: 'easeOut' }}
              className="fixed top-0 right-0 bottom-0 w-full max-w-lg glass border-l border-white/10 z-50 overflow-y-auto"
            >
              <div className="p-5 border-b border-white/5 flex items-center justify-between sticky top-0 glass z-10">
                <div>
                  <h2 className="text-sm font-bold text-white">{viewing.name}</h2>
                  <p className="text-[11px] text-slate-500">{viewingChunks.length} chunks indexed</p>
                </div>
                <button onClick={() => setViewing(null)} className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-slate-400 hover:text-white">
                  <X size={14} />
                </button>
              </div>
              <div className="p-5 space-y-2">
                {viewingChunks.length === 0 && (
                  <p className="text-xs text-slate-600 text-center py-8">No chunks found — this document may not have been indexed yet.</p>
                )}
                {viewingChunks.map((chunk) => (
                  <div key={chunk.id} className="glass-light rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-1.5 text-[10px] font-mono text-slate-500">
                      <BookOpen size={11} />
                      {chunk.section || `Chunk ${chunk.chunk_index}`}
                      {chunk.page && ` · Page ${chunk.page}`}
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-4">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
