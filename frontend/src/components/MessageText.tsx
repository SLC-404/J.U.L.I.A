import type { ReactNode } from 'react'

// Muestra el Markdown sencillo que escribe el agente (# titulos, **negritas**,
// listas). Mismo subconjunto que backend/app/docx_export.py, para que lo que
// se ve en pantalla sea lo que sale en el Word.

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*.+?\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  )
}

export function MessageText({ text }: { text: string }) {
  return (
    <div className="grid gap-2 leading-relaxed">
      {text.split('\n').map((raw, i) => {
        const line = raw.trimEnd()
        if (!line.trim()) return null
        const heading = line.match(/^(#{1,6})\s+(.*)$/)
        if (heading) {
          return (
            <p key={i} className={heading[1].length === 1 ? 'text-base font-semibold' : 'font-semibold'}>
              {inline(heading[2])}
            </p>
          )
        }
        const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
        if (bullet) {
          return (
            <p key={i} className="flex gap-2 pl-2">
              <span>•</span>
              <span>{inline(bullet[1])}</span>
            </p>
          )
        }
        return <p key={i}>{inline(line)}</p>
      })}
    </div>
  )
}
