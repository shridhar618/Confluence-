import { FolderCog, FolderOpenDot, Plus, UserPlus, X } from 'lucide-react'

function ProjectRow({ project, isSelected, onSelect, onToggleArchive }) {
  return (
    <div className={`rounded-2xl border px-4 py-3 transition ${isSelected ? 'border-accent/40 bg-accent/10' : 'border-white/10 bg-white/[0.03]'}`}>
      <div className="flex items-start justify-between gap-3">
        <button type="button" onClick={() => onSelect(project.id)} className="min-w-0 text-left">
          <p className="text-sm font-semibold text-white">{project.name}</p>
          <p className="mt-1 text-xs text-slate-400">{project.description || 'No description yet.'}</p>
        </button>
        <button
          type="button"
          onClick={() => onToggleArchive(project)}
          className={`rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.16em] ${
            project.is_archived
              ? 'border-amber-300/20 bg-amber-300/10 text-amber-200'
              : 'border-emerald-300/20 bg-emerald-300/10 text-emerald-200'
          }`}
        >
          {project.is_archived ? 'Unarchive' : 'Archive'}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
        <span>{project.member_count || 0} members</span>
        <span>{project.is_archived ? 'Archived' : 'Active'}</span>
      </div>
    </div>
  )
}

export default function ProjectManagementModal({
  open,
  onClose,
  projects,
  selectedProject,
  onSelectProject,
  createForm,
  onCreateFormChange,
  onCreateProject,
  creatingProject,
  memberUserId,
  onMemberUserIdChange,
  onAddMember,
  memberOptions,
  onRemoveMember,
  onToggleArchive,
}) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#02060d]/80 px-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-6xl overflow-hidden rounded-[32px] border border-white/10 bg-[#07111f] shadow-[0_30px_120px_rgba(0,0,0,0.45)]">
        <div className="flex items-center justify-between border-b border-white/8 px-6 py-5">
          <div>
            <p className="text-xs font-mono uppercase tracking-[0.2em] text-accent">Project Operations</p>
            <h2 className="mt-1 text-xl font-semibold text-white">Manage Projects</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-white/10 bg-white/[0.04] p-2 text-slate-400 transition hover:border-white/20 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        <div className="grid max-h-[calc(90vh-90px)] grid-cols-1 gap-0 overflow-y-auto xl:grid-cols-[1.2fr_1fr]">
          <div className="border-b border-white/8 p-6 xl:border-b-0 xl:border-r">
            <div className="mb-5 flex items-center gap-2">
              <FolderCog size={16} className="text-accent" />
              <p className="text-sm font-semibold text-white">Projects</p>
            </div>
            <div className="space-y-3">
              {projects.length ? (
                projects.map(project => (
                  <ProjectRow
                    key={project.id}
                    project={project}
                    isSelected={project.id === selectedProject?.id}
                    onSelect={onSelectProject}
                    onToggleArchive={onToggleArchive}
                  />
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-white/10 px-4 py-10 text-center text-sm text-slate-500">
                  Create your first project to start the Kanban workflow.
                </div>
              )}
            </div>

            <form onSubmit={onCreateProject} className="mt-6 rounded-[28px] border border-white/10 bg-white/[0.03] p-5">
              <div className="mb-4 flex items-center gap-2">
                <Plus size={15} className="text-accent" />
                <p className="text-sm font-semibold text-white">Create Project</p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
                    Name
                  </label>
                  <input
                    name="name"
                    value={createForm.name}
                    onChange={onCreateFormChange}
                    required
                    className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
                    Description
                  </label>
                  <textarea
                    name="description"
                    value={createForm.description}
                    onChange={onCreateFormChange}
                    rows={4}
                    className="w-full rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40"
                  />
                </div>
                <button
                  type="submit"
                  disabled={creatingProject}
                  className="inline-flex items-center gap-2 rounded-xl border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-60"
                >
                  <Plus size={14} />
                  {creatingProject ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>

          <div className="p-6">
            <div className="mb-5 flex items-center gap-2">
              <FolderOpenDot size={16} className="text-accent" />
              <p className="text-sm font-semibold text-white">Project Members</p>
            </div>

            {!selectedProject ? (
              <div className="rounded-2xl border border-dashed border-white/10 px-4 py-10 text-center text-sm text-slate-500">
                Select a project to manage its members.
              </div>
            ) : (
              <div className="space-y-5">
                <div className="rounded-[28px] border border-white/10 bg-white/[0.03] p-5">
                  <p className="text-sm font-semibold text-white">{selectedProject.name}</p>
                  <p className="mt-1 text-xs text-slate-400">{selectedProject.description || 'No description set.'}</p>
                  <p className="mt-3 text-[11px] text-slate-500">
                    {selectedProject.is_archived ? 'Archived projects keep their history but should not accept new tasks.' : 'Project members appear first in the task assignee dropdown.'}
                  </p>
                </div>

                <div className="rounded-[28px] border border-white/10 bg-white/[0.03] p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <UserPlus size={15} className="text-accent" />
                    <p className="text-sm font-semibold text-white">Add Member</p>
                  </div>
                  <div className="flex flex-col gap-3 md:flex-row">
                    <select
                      value={memberUserId}
                      onChange={event => onMemberUserIdChange(event.target.value)}
                      className="min-w-0 flex-1 rounded-xl border border-white/10 bg-[#08111f] px-3 py-2.5 text-sm text-white outline-none transition focus:border-accent/40"
                    >
                      <option value="">Select a user</option>
                      {memberOptions.map(option => (
                        <option key={option.id} value={option.id}>
                          {option.username} ({option.role})
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={onAddMember}
                      disabled={!memberUserId}
                      className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-60"
                    >
                      Add to Project
                    </button>
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/10 bg-white/[0.03] p-5">
                  <p className="text-sm font-semibold text-white">Current Members</p>
                  <div className="mt-4 space-y-3">
                    {selectedProject.members?.length ? (
                      selectedProject.members.map(member => (
                        <div key={member.user_id} className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-[#08111f] px-4 py-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-white">{member.user?.username}</p>
                            <p className="truncate text-xs text-slate-400">{member.user?.email}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => onRemoveMember(member.user_id)}
                            className="rounded-full border border-rose-300/20 bg-rose-300/10 px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.16em] text-rose-200"
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
                        No members added yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
