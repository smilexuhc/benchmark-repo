import { Checkbox, Button } from 'antd'
import type { Options, Filters } from '../types'

interface Props {
  fields: string[]
  labels: Record<string, string>
  options: Options
  filters: Filters
  count: number
  onChange: (f: Filters) => void
}

export default function FilterPanel({
  fields, labels, options, filters, count, onChange,
}: Props) {
  const active = fields.reduce((n, f) => n + (filters[f]?.length || 0), 0)

  const reset = () => {
    const cleared: Filters = {}
    fields.forEach((f) => (cleared[f] = []))
    onChange(cleared)
  }

  return (
    <aside
      style={{
        width: 220,
        flexShrink: 0,
        background: '#fff',
        borderRight: '1px solid #e8e8e8',
        height: '100%',
        overflowY: 'auto',
        padding: '16px 16px 32px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        <span style={{ fontWeight: 600 }}>筛选</span>
        <Button
          type="link"
          size="small"
          disabled={active === 0}
          onClick={reset}
          style={{ padding: 0 }}
        >
          重置{active ? ` (${active})` : ''}
        </Button>
      </div>
      <div style={{ fontSize: 12, color: '#8a8f99', marginBottom: 16 }}>
        命中 {count} 个
      </div>

      {fields.map((field) => (
        <div key={field} style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            {labels[field] || field}
          </div>
          <Checkbox.Group
            value={filters[field] || []}
            onChange={(vals) =>
              onChange({ ...filters, [field]: vals as string[] })
            }
            style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
          >
            {(options[field] || []).map((v) => (
              <Checkbox key={v} value={v}>
                {v}
              </Checkbox>
            ))}
          </Checkbox.Group>
        </div>
      ))}
    </aside>
  )
}
