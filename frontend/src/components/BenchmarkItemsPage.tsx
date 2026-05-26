import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  App as AntApp,
  Button,
  Empty,
  Image,
  Input,
  Select,
  Space,
  Table,
  Tag,
} from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import type {
  MediaAsset,
  VideoBenchmarkItem,
  VideoBenchmarkItemInput,
  VideoBenchmarkListParams,
} from '../types'
import { FIELD_LABELS } from '../types'
import { imageUrl, videoBenchmarkApi } from '../api'
import BenchmarkItemDrawer from './BenchmarkItemDrawer'

const DEFAULT_PAGE_SIZE = 50

type FilterKey = 'shot_type' | 'task_type' | 'question_type' | 'scene' | 'screen_size'

const FILTER_FIELDS: FilterKey[] = [
  'shot_type',
  'task_type',
  'question_type',
  'scene',
  'screen_size',
]

const DETAIL_FIELDS: (keyof VideoBenchmarkItemInput)[] = [
  'text_prompt',
  'judging_criteria',
]

const MEDIA_DETAIL_FIELDS: {
  label: string
  mediaKey: keyof VideoBenchmarkItem
  mediaListKey: keyof VideoBenchmarkItem
  snapshotKey: keyof VideoBenchmarkItem
}[] = [
  { label: FIELD_LABELS.character_image_id, mediaKey: 'character_image', mediaListKey: 'character_image_media', snapshotKey: 'character_image_asset' },
  { label: FIELD_LABELS.scene_image_id, mediaKey: 'scene_image', mediaListKey: 'scene_image_media', snapshotKey: 'scene_image_asset' },
  { label: FIELD_LABELS.prop_image_id, mediaKey: 'prop_image', mediaListKey: 'prop_image_media', snapshotKey: 'prop_image_asset' },
  { label: FIELD_LABELS.audio_input_id, mediaKey: 'audio_input_media', mediaListKey: 'audio_input_media_items', snapshotKey: 'audio_input' },
  { label: FIELD_LABELS.video_input_id, mediaKey: 'video_input_media', mediaListKey: 'video_input_media_items', snapshotKey: 'video_input' },
  { label: FIELD_LABELS.video_output_id, mediaKey: 'video_output_media', mediaListKey: 'video_output_media_items', snapshotKey: 'video_output' },
]

function compactText(value: string, fallback = '-') {
  const text = value.trim()
  if (!text) return fallback
  return text
}

function TextCell({ value }: { value: string }) {
  const text = compactText(value)
  if (text === '-') return <span style={{ color: '#b8bdc4' }}>-</span>
  return (
    <span
      style={{
        display: 'block',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        lineHeight: '20px',
      }}
    >
      {text}
    </span>
  )
}

function ScoreTag({ score }: { score: number | null }) {
  if (score === null) return <Tag style={{ marginInlineEnd: 0 }}>未评分</Tag>
  const color = score >= 4 ? 'green' : score >= 2 ? 'blue' : 'orange'
  return (
    <Tag color={color} style={{ marginInlineEnd: 0 }}>
      {score} 分
    </Tag>
  )
}

function mediaName(media: MediaAsset) {
  return media.object_key.split('/').pop() || media.object_key
}

function MediaDetail({ media, snapshot }: { media: MediaAsset | null; snapshot: string }) {
  if (media?.media_type === 'image') {
    return (
      <div>
        <Image
          src={imageUrl(media.object_key)}
          width={128}
          height={78}
          style={{ objectFit: 'contain', background: '#f4f5f7', borderRadius: 4 }}
        />
        <div style={{ marginTop: 6, fontSize: 12 }}>
          #{media.id} · {mediaName(media)}
        </div>
      </div>
    )
  }
  if (media?.media_type === 'audio') {
    return (
      <div>
        <audio controls src={imageUrl(media.object_key)} style={{ width: '100%' }} />
        <div style={{ marginTop: 6, fontSize: 12 }}>
          #{media.id} · {mediaName(media)}
        </div>
      </div>
    )
  }
  if (media?.media_type === 'video') {
    return (
      <div>
        <video controls src={imageUrl(media.object_key)} style={{ width: 180, maxWidth: '100%', borderRadius: 4, background: '#f4f5f7' }} />
        <div style={{ marginTop: 6, fontSize: 12 }}>
          #{media.id} · {mediaName(media)}
        </div>
      </div>
    )
  }
  return <>{compactText(snapshot, '暂无')}</>
}

function MediaPreviewStack({ items }: { items: MediaAsset[] }) {
  if (!items.length) return <span style={{ color: '#b8bdc4' }}>-</span>
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      {items.slice(0, 3).map((media) => (
        media.media_type === 'image' ? (
          <Image
            key={media.id}
            src={imageUrl(media.object_key)}
            width={120}
            height={84}
            style={{ objectFit: 'cover', borderRadius: 4, background: '#f4f5f7' }}
          />
        ) : media.media_type === 'video' ? (
          <video
            key={media.id}
            src={imageUrl(media.object_key)}
            width={120}
            height={84}
            muted
            playsInline
            preload="metadata"
            style={{ objectFit: 'cover', borderRadius: 4, background: '#f4f5f7', display: 'block' }}
          />
        ) : (
          <div
            key={media.id}
            style={{ width: 120, height: 84, borderRadius: 4, background: '#f4f5f7', color: '#6b7280', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            音频
          </div>
        )
      ))}
      {items.length > 3 && <Tag style={{ marginInlineEnd: 0 }}>+{items.length - 3}</Tag>}
    </div>
  )
}

export default function BenchmarkItemsPage() {
  const { message } = AntApp.useApp()
  const [items, setItems] = useState<VideoBenchmarkItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [filters, setFilters] = useState<Record<FilterKey, string | undefined>>({
    shot_type: undefined,
    task_type: undefined,
    question_type: undefined,
    scene: undefined,
    screen_size: undefined,
  })
  const [score, setScore] = useState<number | null | undefined>(undefined)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<VideoBenchmarkItem | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1)
      setQuery(search)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: VideoBenchmarkListParams = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        q: query.trim() || undefined,
        score,
        ...filters,
      }
      const data = await videoBenchmarkApi.list(params)
      setItems(data.items)
      setTotal(data.total)
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [filters, message, page, pageSize, query, score])

  useEffect(() => {
    load()
  }, [load])

  const openNew = () => {
    setEditing(null)
    setDrawerOpen(true)
  }

  const openEdit = (item: VideoBenchmarkItem) => {
    setEditing(item)
    setDrawerOpen(true)
  }

  const resetFilters = () => {
    setFilters({
      shot_type: undefined,
      task_type: undefined,
      question_type: undefined,
      scene: undefined,
      screen_size: undefined,
    })
    setScore(undefined)
    setPage(1)
  }

  const onSaved = async () => {
    await load()
  }

  const columns: ColumnsType<VideoBenchmarkItem> = useMemo(
    () => [
      {
        title: 'ID',
        dataIndex: 'id',
        width: 76,
        fixed: 'left',
      },
      {
        title: FIELD_LABELS.shot_type,
        dataIndex: 'shot_type',
        width: 150,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: FIELD_LABELS.task_type,
        dataIndex: 'task_type',
        width: 190,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: FIELD_LABELS.question_type,
        dataIndex: 'question_type',
        width: 190,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: FIELD_LABELS.scene,
        dataIndex: 'scene',
        width: 150,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: FIELD_LABELS.screen_size,
        dataIndex: 'screen_size',
        width: 120,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: FIELD_LABELS.text_prompt,
        dataIndex: 'text_prompt',
        width: 320,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: FIELD_LABELS.judging_criteria,
        dataIndex: 'judging_criteria',
        width: 320,
        render: (value: string) => <TextCell value={value} />,
      },
      {
        title: '人物图',
        dataIndex: 'character_image_media',
        width: 400,
        render: (items: MediaAsset[] = []) => <MediaPreviewStack items={items} />,
      },
      {
        title: '场景图',
        dataIndex: 'scene_image_media',
        width: 400,
        render: (items: MediaAsset[] = []) => <MediaPreviewStack items={items} />,
      },
      {
        title: '道具图',
        dataIndex: 'prop_image_media',
        width: 400,
        render: (items: MediaAsset[] = []) => <MediaPreviewStack items={items} />,
      },
      {
        title: '音频',
        dataIndex: 'audio_input_media_items',
        width: 260,
        render: (items: MediaAsset[] = []) => <MediaPreviewStack items={items} />,
      },
      {
        title: FIELD_LABELS.video_input,
        dataIndex: 'video_input_media_items',
        width: 400,
        render: (items: MediaAsset[] = []) => <MediaPreviewStack items={items} />,
      },
      {
        title: FIELD_LABELS.video_output,
        dataIndex: 'video_output_media_items',
        width: 400,
        render: (items: MediaAsset[] = []) => <MediaPreviewStack items={items} />,
      },
      {
        title: FIELD_LABELS.score,
        dataIndex: 'score',
        width: 130,
        render: (value: number | null) => <ScoreTag score={value} />,
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        width: 170,
        render: (value: string) => value || '-',
      },
      {
        title: '操作',
        key: 'actions',
        width: 96,
        fixed: 'right',
        render: (_, record) => (
          <Button size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
        ),
      },
    ],
    [],
  )

  const pagination: TablePaginationConfig = {
    current: page,
    pageSize,
    total,
    showSizeChanger: true,
    showTotal: (count) => `共 ${count} 条`,
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div
        style={{
          flexShrink: 0,
          background: '#fff',
          borderBottom: '1px solid #e8e8e8',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <Space size={8} wrap>
          {FILTER_FIELDS.map((field) => (
            <Input
              key={field}
              allowClear
              placeholder={FIELD_LABELS[field]}
              value={filters[field]}
              onChange={(event) => {
                const value = event.target.value.trim() || undefined
                setFilters((current) => ({ ...current, [field]: value }))
                setPage(1)
              }}
              style={{ width: 136 }}
            />
          ))}
          <Select
            allowClear
            placeholder="Score"
            value={score}
            onChange={(value) => {
              setScore(value)
              setPage(1)
            }}
            options={[
              { value: 0, label: '0 分' },
              { value: 1, label: '1 分' },
              { value: 2, label: '2 分' },
              { value: 3, label: '3 分' },
              { value: 4, label: '4 分' },
              { value: 5, label: '5 分' },
            ]}
            style={{ width: 128 }}
          />
          <Button onClick={resetFilters}>重置筛选</Button>
        </Space>
        <div style={{ flex: 1, minWidth: 16 }} />
        <Input.Search
          allowClear
          placeholder="搜索镜头 / 任务 / 场景 / 提示词 / 输出"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          style={{ width: 320 }}
        />
        <Button type="primary" onClick={openNew}>
          新建题目
        </Button>
      </div>

      <main style={{ flex: 1, minHeight: 0, padding: 8, overflow: 'hidden' }}>
        <Table<VideoBenchmarkItem>
          className="benchmark-items-table"
          size="small"
          rowKey="id"
          loading={loading}
          dataSource={items}
          columns={columns}
          pagination={pagination}
          scroll={{ x: 3600, y: 'calc(100vh - 196px)' }}
          locale={{
            emptyText: (
              <Empty description="没有符合条件的题目" style={{ padding: 24 }} />
            ),
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: 12,
                }}
              >
                {MEDIA_DETAIL_FIELDS.map((field) => (
                  <div key={field.mediaKey}>
                    <div style={{ fontSize: 12, color: '#8a8f99', marginBottom: 4 }}>
                      {field.label}
                    </div>
                    <div className="prompt-box benchmark-detail-box">
                      {((record[field.mediaListKey] as MediaAsset[]) || []).length ? (
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          {((record[field.mediaListKey] as MediaAsset[]) || []).map((media) => (
                            <MediaDetail key={media.id} media={media} snapshot="" />
                          ))}
                        </div>
                      ) : (
                        <MediaDetail
                          media={(record[field.mediaKey] as MediaAsset | null) || null}
                          snapshot={String(record[field.snapshotKey] ?? '')}
                        />
                      )}
                    </div>
                  </div>
                ))}
                {DETAIL_FIELDS.map((field) => (
                  <div key={field}>
                    <div style={{ fontSize: 12, color: '#8a8f99', marginBottom: 4 }}>
                      {FIELD_LABELS[field]}
                    </div>
                    <div className="prompt-box benchmark-detail-box">
                      {compactText(String(record[field] ?? ''), '暂无')}
                    </div>
                  </div>
                ))}
              </div>
            ),
          }}
          onChange={(nextPagination) => {
            setPage(nextPagination.current || 1)
            setPageSize(nextPagination.pageSize || DEFAULT_PAGE_SIZE)
          }}
        />
      </main>

      <BenchmarkItemDrawer
        open={drawerOpen}
        item={editing}
        onClose={() => setDrawerOpen(false)}
        onSaved={onSaved}
      />
    </div>
  )
}
