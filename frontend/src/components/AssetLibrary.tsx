import { useCallback, useEffect, useRef, useState } from 'react'
import type { ComponentType, ReactNode } from 'react'
import { Input, Button, Spin, Empty, Progress, App as AntApp } from 'antd'
import type { AssetBase, CharImage, Filters, Options } from '../types'
import FilterPanel from './FilterPanel'
import AssetCard from './AssetCard'

export interface DrawerProps<T> {
  open: boolean
  item: T | null
  options: Options
  onClose: () => void
  onRefresh: () => void | Promise<void>
}

/** AssetLibrary 实际用到的 API 子集（不涉及输入类型） */
interface LibraryApi<T> {
  options: (deletedOnly?: boolean) => Promise<Options>
  list: (filters: Filters, q: string, deletedOnly?: boolean) => Promise<T[]>
  generateImage: (id: number, prompt: string, setCover?: boolean) => Promise<CharImage>
  setCover: (id: number, imgId: number) => Promise<T>
  exportUrl: (filters: Filters, q: string) => string
}

interface Props<T extends AssetBase> {
  api: LibraryApi<T>
  filterFields: string[]
  filterLabels: Record<string, string>
  renderInfo: (item: T) => ReactNode
  nameOf: (item: T) => string
  searchPlaceholder: string
  newLabel: string
  Drawer: ComponentType<DrawerProps<T>>
  renderExtra?: (item: T, onRefresh: () => void | Promise<void>) => ReactNode
}

interface BatchState {
  done: number
  total: number
  current: string
  currentId: number
}

export default function AssetLibrary<T extends AssetBase>({
  api, filterFields, filterLabels, renderInfo, nameOf,
  searchPlaceholder, newLabel, Drawer, renderExtra,
}: Props<T>) {
  const { message, modal } = AntApp.useApp()
  const emptyFilters = () => {
    const f: Filters = {}
    filterFields.forEach((k) => (f[k] = []))
    return f
  }

  const [options, setOptions] = useState<Options>({})
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [deletedOnly, setDeletedOnly] = useState(false)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<T | null>(null)

  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [batch, setBatch] = useState<BatchState | null>(null)
  const stopRef = useRef(false)

  useEffect(() => {
    const t = setTimeout(() => setQuery(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await api.list(filters, query, deletedOnly))
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [api, filters, query, deletedOnly, message])

  useEffect(() => {
    api.options(deletedOnly).then(setOptions).catch(() => {})
  }, [api, deletedOnly])

  useEffect(() => {
    load()
  }, [load])

  const openNew = () => {
    setEditing(null)
    setDrawerOpen(true)
  }
  const openEdit = (item: T) => {
    setEditing(item)
    setDrawerOpen(true)
  }

  const exitSelect = () => {
    setSelectMode(false)
    setSelected(new Set())
  }
  const toggleSelect = (id: number) =>
    setSelected((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })

  const runBatch = () => {
    const jobs = items
      .filter((c) => selected.has(c.id))
      .map((c) => ({ id: c.id, name: nameOf(c), prompt: c.prompt }))
    const valid = jobs.filter((j) => j.prompt.trim())
    const noPrompt = jobs.length - valid.length
    if (valid.length === 0) {
      message.warning('选中的项都没有提示词，无法生成')
      return
    }
    modal.confirm({
      title: `批量重新生成 ${valid.length} 项？`,
      content:
        `将依次生成，每个约 1 分钟，共约 ${valid.length} 分钟。` +
        (noPrompt ? `另有 ${noPrompt} 个无提示词将跳过。` : '') +
        '生成期间请保持页面打开。',
      okText: '开始',
      cancelText: '取消',
      onOk: async () => {
        stopRef.current = false
        let done = 0
        let failed = ''
        for (const job of valid) {
          if (stopRef.current) break
          setBatch({ done, total: valid.length, current: job.name, currentId: job.id })
          try {
            await api.generateImage(job.id, job.prompt, true)
            done += 1
            await load()
          } catch (e) {
            failed = `「${job.name}」失败：${(e as Error).message}`
            break
          }
        }
        setBatch(null)
        await load()
        exitSelect()
        if (failed) {
          modal.error({ title: '批量生成中断', content: `已完成 ${done} 个。${failed}` })
        } else if (stopRef.current) {
          message.info(`已停止，完成 ${done} 个`)
        } else {
          message.success(`批量生成完成：${done} 个`)
        }
      },
    })
  }

  const exportExcel = () => {
    const a = document.createElement('a')
    a.href = api.exportUrl(filters, query)
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  const allSelected = items.length > 0 && items.every((c) => selected.has(c.id))

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* 工具行 */}
      <div
        style={{
          flexShrink: 0,
          background: '#fff',
          borderBottom: '1px solid #e8e8e8',
          display: 'flex',
          alignItems: 'center',
          padding: '10px 20px',
          gap: 12,
        }}
      >
        <div style={{ flex: 1 }} />
        <Input.Search
          allowClear
          placeholder={searchPlaceholder}
          style={{ width: 280 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          disabled={!!batch}
        />
        {!selectMode && (
          <>
            <Button onClick={exportExcel} disabled={items.length === 0}>
              导出资产包
            </Button>
            <Button onClick={() => setSelectMode(true)}>批量生成</Button>
          </>
        )}
        <Button type="primary" onClick={openNew} disabled={selectMode}>
          {newLabel}
        </Button>
      </div>

      {/* 批量操作条 */}
      {selectMode && (
        <div
          style={{
            flexShrink: 0,
            background: '#f0f6ff',
            borderBottom: '1px solid #d6e4ff',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '10px 20px',
          }}
        >
          {batch ? (
            <>
              <span style={{ fontWeight: 600 }}>
                批量重新生成 {batch.done} / {batch.total}
              </span>
              <Progress
                percent={Math.round((batch.done / batch.total) * 100)}
                style={{ width: 220, marginBottom: 0 }}
                size="small"
              />
              <span style={{ color: '#5a6068' }}>当前：{batch.current}</span>
              <div style={{ flex: 1 }} />
              <Button danger onClick={() => (stopRef.current = true)}>
                停止
              </Button>
            </>
          ) : (
            <>
              <span style={{ fontWeight: 600 }}>
                已选 {selected.size} / {items.length} 个
              </span>
              <Button
                size="small"
                onClick={() =>
                  setSelected(
                    allSelected ? new Set() : new Set(items.map((c) => c.id)),
                  )
                }
              >
                {allSelected ? '取消全选' : '全选当前'}
              </Button>
              <Button
                size="small"
                disabled={selected.size === 0}
                onClick={() => setSelected(new Set())}
              >
                清空
              </Button>
              <div style={{ flex: 1 }} />
              <Button
                type="primary"
                disabled={selected.size === 0}
                onClick={runBatch}
              >
                开始重新生成
              </Button>
              <Button onClick={exitSelect}>退出</Button>
            </>
          )}
        </div>
      )}

      {/* 左筛选 + 右列表 */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <FilterPanel
          fields={filterFields}
          labels={filterLabels}
          options={options}
          filters={filters}
          count={items.length}
          onChange={setFilters}
          deletedOnly={deletedOnly}
          onDeletedOnlyChange={setDeletedOnly}
        />
        <main style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {loading && items.length === 0 ? (
            <div style={{ textAlign: 'center', paddingTop: 80 }}>
              <Spin />
            </div>
          ) : items.length === 0 ? (
            <Empty description="没有符合条件的项" style={{ paddingTop: 80 }} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {items.map((item) => (
                <AssetCard
                  key={item.id}
                  item={item}
                  info={renderInfo(item)}
                  downloadName={nameOf(item)}
                  generateImage={api.generateImage}
                  setCover={api.setCover}
                  onEdit={() => openEdit(item)}
                  onRefresh={load}
                  selectMode={selectMode && !batch}
                  selected={selected.has(item.id)}
                  busy={batch?.currentId === item.id}
                  onToggleSelect={() => toggleSelect(item.id)}
                  renderExtra={
                    renderExtra ? () => renderExtra(item, load) : undefined
                  }
                />
              ))}
            </div>
          )}
        </main>
      </div>

      <Drawer
        open={drawerOpen}
        item={editing}
        options={options}
        onClose={() => setDrawerOpen(false)}
        onRefresh={load}
      />
    </div>
  )
}
