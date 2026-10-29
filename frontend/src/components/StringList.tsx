import { Textarea } from './ui'

/** Edits a list of strings as one item per line. */
export function StringList({ value, onChange, rows = 5 }: { value: string[]; onChange: (v: string[]) => void; rows?: number }) {
  return (
    <Textarea
      rows={rows}
      value={value.join('\n')}
      onChange={(e) => onChange(e.target.value.split('\n'))}
      onBlur={() => onChange(value.map((s) => s.trim()).filter(Boolean))}
    />
  )
}
