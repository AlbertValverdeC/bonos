import { ReactNode } from 'react'

interface Props {
  sidebar: ReactNode
  children: ReactNode
}

export default function Layout({ sidebar, children }: Props) {
  return (
    <div className="flex h-screen">
      <aside className="w-80 bg-gray-900 border-r border-gray-800 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🎬</span> Bonos
          </h1>
          <p className="text-xs text-gray-500 mt-1">YouTube Pipeline</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sidebar}
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-gray-950">
        {children}
      </main>
    </div>
  )
}
