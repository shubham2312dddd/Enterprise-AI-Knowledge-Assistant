import { BookOpen, FileText, HelpCircle, LayoutDashboard, Settings } from 'lucide-react'

const navigation = [
  { label: 'Overview', icon: LayoutDashboard, href: '#overview', active: true },
  { label: 'Documents', icon: FileText, href: '#documents' },
  { label: 'AI assistant', icon: BookOpen, href: '#assistant' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <a className="brand" href="#overview" aria-label="Enterprise AI Knowledge Assistant home">
        <span className="brand-mark"><BookOpen size={20} strokeWidth={2.2} /></span>
        <span className="brand-name">Knowledge<span>Assistant</span></span>
      </a>

      <div className="workspace-label">WORKSPACE</div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navigation.map(({ label, icon: Icon, href, active }) => (
          <a className={`nav-link${active ? ' active' : ''}`} href={href} key={label}>
            <Icon size={18} />
            <span>{label}</span>
          </a>
        ))}
      </nav>

      <div className="sidebar-spacer" />
      <div className="sidebar-bottom">
        <a className="nav-link" href="#help"><HelpCircle size={18} /><span>Help center</span></a>
        <a className="nav-link" href="#settings"><Settings size={18} /><span>Settings</span></a>
        <div className="sidebar-divider" />
        <div className="profile">
          <div className="avatar">EA</div>
          <div className="profile-copy"><strong>Enterprise workspace</strong><span>Local environment</span></div>
        </div>
      </div>
    </aside>
  )
}
