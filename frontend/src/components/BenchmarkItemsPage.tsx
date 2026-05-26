import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  App as AntApp,
  Button,
  Cascader,
  Empty,
  Image,
  Input,
  Modal,
  Pagination,
  Select,
  Space,
  Spin,
  Tag,
} from 'antd'
import type {
  MediaAsset,
  VideoBenchmarkItem,
  VideoBenchmarkListParams,
} from '../types'
import { FIELD_LABELS } from '../types'
import { imageUrl, videoBenchmarkApi } from '../api'
import BenchmarkItemDrawer from './BenchmarkItemDrawer'
import {
  buildCascaderOptionsWithCounts,
  findCascaderLabels,
  type StatsGroup,
} from '../data/questionTypeOptions'

const SCENE_OPTIONS = ['电影 / 预告片', '短剧 / 剧情片段', '动画 / 风格化内容']
const SCREEN_SIZE_OPTIONS = ['16:9', '9:16', '2.39:1']

const DEFAULT_PAGE_SIZE = 20

type FilterKey = 'shot_type' | 'task_type' | 'question_type' | 'scene' | 'screen_size'

// 卡片上展示的 chip 字段：shot_type / question_type 提升到标题，scene / screen_size 留作小标签
const TAG_FIELDS: FilterKey[] = ['scene', 'screen_size']

const MODEL_NAME = 'Seedance'  // v1: 仅一个模型；未来多模型时右侧扩展为多列

// ----- 工具函数 -----

function scoreColor(score: number | null): string {
  if (score === null || score === undefined) return '#9aa0a6'
  if (score >= 4) return '#16a34a'
  if (score >= 2) return '#2563eb'
  return '#ea7700'
}

function formatRelativeTime(iso: string): string {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  if (diff < 30 * 86_400_000) return `${Math.floor(diff / 86_400_000)} 天前`
  return iso.slice(0, 10)
}

function collectAssetMedia(item: VideoBenchmarkItem): MediaAsset[] {
  return [
    ...(item.character_image_media || []),
    ...(item.scene_image_media || []),
    ...(item.prop_image_media || []),
    ...(item.audio_input_media_items || []),
  ]
}

// ----- 子组件 -----

function AssetThumb({ media }: { media: MediaAsset }) {
  // 包一层 stopPropagation：点缩略图触发 Image 自身的预览，不冒泡到卡片
  const wrap = (node: React.ReactNode) => (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{ display: 'inline-block', lineHeight: 0 }}
    >
      {node}
    </div>
  )
  if (media.media_type === 'image') {
    return wrap(
      <Image
        src={imageUrl(media.object_key)}
        width={56}
        height={56}
        style={{ objectFit: 'cover', borderRadius: 4, background: '#f4f5f7' }}
      />,
    )
  }
  if (media.media_type === 'audio') {
    return wrap(
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 4,
          background: '#f4f5f7',
          color: '#6b7280',
          fontSize: 11,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        音频
      </div>,
    )
  }
  return null
}

function AssetRow({ item }: { item: VideoBenchmarkItem }) {
  const all = collectAssetMedia(item)
  if (all.length === 0) {
    return <div style={{ fontSize: 12, color: '#bbb' }}>暂无参考资产</div>
  }
  return (
    <Image.PreviewGroup>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        {all.map((media) => (
          <AssetThumb key={`${media.asset_kind}-${media.id}`} media={media} />
        ))}
      </div>
    </Image.PreviewGroup>
  )
}

// 根据 screen_size 字段返回 CSS aspect-ratio（兼容全角/半角冒号、空格）
function screenAspectRatio(screenSize: string): string {
  const s = (screenSize || '')
    .replace(/[：﹕]/g, ':')
    .replace(/\s+/g, '')
  if (s === '9:16') return '9 / 16'
  if (s.startsWith('2.39')) return '2.39 / 1'
  return '16 / 9'  // 默认及 16:9
}

// 视频长边目标尺寸（点击放大用 controls 已带的 fullscreen）
const VIDEO_LONG_SIDE = 200

function VideoRun({
  media,
  version,
  score,
  screenSize,
}: {
  media: MediaAsset
  version: number
  score: number | null
  screenSize: string
}) {
  const [previewing, setPreviewing] = useState(false)
  const aspect = screenAspectRatio(screenSize)
  // 9:16 走"高占满"；其它走"宽占满"
  const isVertical = aspect === '9 / 16'
  const thumbStyle: React.CSSProperties = isVertical
    ? { height: VIDEO_LONG_SIDE, width: 'auto', aspectRatio: aspect }
    : { width: VIDEO_LONG_SIDE, height: 'auto', aspectRatio: aspect }

  // 放大后视频尺寸：以 viewport 为参考
  const previewVideoStyle: React.CSSProperties = isVertical
    ? { height: '78vh', width: 'auto', aspectRatio: aspect, maxWidth: '90vw' }
    : { width: 'min(80vw, 1080px)', height: 'auto', aspectRatio: aspect, maxHeight: '80vh' }

  // 竖屏弹窗窄一点
  const modalWidth = isVertical ? 'auto' : 'min(80vw, 1100px)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6 }}>
      <div
        onClick={() => setPreviewing(true)}
        style={{ cursor: 'pointer', lineHeight: 0, position: 'relative' }}
      >
        <video
          src={imageUrl(media.object_key)}
          muted
          playsInline
          preload="metadata"
          style={{
            ...thumbStyle,
            objectFit: 'cover',
            background: '#000',
            borderRadius: 4,
            pointerEvents: 'none',  // 让点击事件冒泡给外层 div
            display: 'block',
          }}
        />
        {/* 中央 ▶ 播放按钮 overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
            <circle cx="22" cy="22" r="22" fill="rgba(0,0,0,0.55)" />
            <polygon points="18,13 18,31 33,22" fill="#fff" />
          </svg>
        </div>
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <span style={{ fontSize: 11, color: '#9aa0a6' }}>v{version}</span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: scoreColor(score),
          }}
        >
          {score === null || score === undefined ? '未评分' : `评分 ${score}/5`}
        </span>
      </div>

      <Modal
        open={previewing}
        onCancel={() => setPreviewing(false)}
        footer={null}
        width={modalWidth}
        centered
        destroyOnClose
        styles={{ body: { padding: 0, background: '#000' } }}
      >
        {previewing && (
          <video
            src={imageUrl(media.object_key)}
            controls
            autoPlay
            playsInline
            preload="auto"
            style={{
              ...previewVideoStyle,
              objectFit: 'contain',
              background: '#000',
              display: 'block',
            }}
          />
        )}
      </Modal>
    </div>
  )
}

function OutputColumn({ item }: { item: VideoBenchmarkItem }) {
  const runs = item.video_output_media_items || []
  const score = item.score
  const screenSize = item.screen_size || ''
  const aspect = screenAspectRatio(screenSize)
  const isVertical = aspect === '9 / 16'
  const placeholderStyle: React.CSSProperties = isVertical
    ? { height: VIDEO_LONG_SIDE, width: 'auto', aspectRatio: aspect }
    : { width: VIDEO_LONG_SIDE, height: 'auto', aspectRatio: aspect }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        padding: 16,
        background: '#fafbfc',
        flex: '1 1 40%',
        minWidth: 0,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div
        style={{
          paddingBottom: 6,
          borderBottom: '1px solid #f0f0f0',
          fontSize: 13,
          fontWeight: 600,
          color: '#5a6068',
        }}
      >
        {MODEL_NAME}
        {runs.length > 1 && (
          <span style={{ fontSize: 11, color: '#9aa0a6', marginLeft: 8, fontWeight: 'normal' }}>
            {runs.length} 个版本
          </span>
        )}
      </div>

      {runs.length === 0 ? (
        <div
          style={{
            ...placeholderStyle,
            borderRadius: 4,
            background: '#f0f1f3',
            color: '#9aa0a6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 13,
          }}
        >
          待生成
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: 14 }}>
          {runs.map((media, idx) => (
            <VideoRun
              key={media.id}
              media={media}
              version={idx + 1}
              score={score}
              screenSize={screenSize}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ExpandableText({
  icon,
  text,
  collapsedLines,
  expanded,
  onToggle,
  textStyle,
}: {
  icon: string
  text: string
  collapsedLines: 1 | 2
  expanded: boolean
  onToggle: () => void
  textStyle?: React.CSSProperties
}) {
  return (
    <div
      onClick={(e) => {
        e.stopPropagation()
        onToggle()
      }}
      style={{
        cursor: 'pointer',
        background: '#f6f7f9',
        border: '1px solid #ecedf0',
        borderRadius: 6,
        padding: '8px 10px',
      }}
    >
      <div
        className={expanded ? undefined : `line-clamp-${collapsedLines}`}
        style={{
          ...textStyle,
          whiteSpace: expanded ? 'pre-wrap' : undefined,
          wordBreak: 'break-word',
        }}
      >
        <span style={{ color: '#9aa0a6', marginRight: 4 }}>{icon}</span>
        {text}
      </div>
      <span
        style={{
          fontSize: 12,
          color: '#1f6feb',
          userSelect: 'none',
        }}
      >
        {expanded ? '收起' : '展开'}
      </span>
    </div>
  )
}

function ItemCard({
  item,
  onClick,
}: {
  item: VideoBenchmarkItem
  onClick: () => void
}) {
  const [promptExpanded, setPromptExpanded] = useState(false)
  const [judgingExpanded, setJudgingExpanded] = useState(false)

  // 标题：question_type 命中树时显示带序号的 [L1 label, L2 label, L3 label]，未命中（legacy）则只显示 shot_type
  const shotType = item.shot_type?.trim()
  const questionType = item.question_type?.trim()
  const cascaderLabels = shotType && questionType ? findCascaderLabels(shotType, questionType) : undefined
  const titleParts = cascaderLabels
    ? cascaderLabels
    : ([shotType].filter(Boolean) as string[])

  // 顺序与编辑抽屉一致：测试点人工标注 → 场景 → 屏幕尺寸
  // 当 question_type 已经在标题里时，manual_tag 与之相同则去重；legacy 情况下不去重，让 legacy 文案落到下一行
  const manualTagValue = item.manual_tag?.trim()
  const tags: { field: string; value: string }[] = []
  if (manualTagValue && (!cascaderLabels || manualTagValue !== questionType)) {
    tags.push({ field: 'manual_tag', value: manualTagValue })
  }
  for (const field of TAG_FIELDS) {
    const value = (item[field] as string)?.trim()
    if (value) tags.push({ field: field as string, value })
  }

  return (
    <div
      className="benchmark-card"
      onClick={onClick}
      style={{
        display: 'flex',
        background: '#fff',
        border: '1px solid #e8e8e8',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* 左：题目输入 */}
      <div
        style={{
          flex: '0 0 60%',
          padding: 16,
          borderRight: '1px solid #f0f0f0',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          minWidth: 0,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
            <span style={{ fontSize: 13, color: '#9aa0a6', fontWeight: 600, flexShrink: 0 }}>
              #{item.id}
            </span>
            {titleParts.length > 0 && (
              <span
                title={titleParts.join(' · ')}
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: '#1f2328',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {titleParts.join(' · ')}
              </span>
            )}
          </div>
          <Button
            size="small"
            onClick={(e) => {
              e.stopPropagation()
              onClick()
            }}
          >
            编辑
          </Button>
        </div>

        {tags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {tags.map((t) => (
              <Tag key={t.field} style={{ marginInlineEnd: 0 }}>
                {t.value}
              </Tag>
            ))}
          </div>
        )}

        {item.text_prompt?.trim() ? (
          <ExpandableText
            icon="📝"
            text={item.text_prompt}
            collapsedLines={2}
            expanded={promptExpanded}
            onToggle={() => setPromptExpanded(!promptExpanded)}
            textStyle={{ fontSize: 13, lineHeight: '20px', color: '#3a3f45' }}
          />
        ) : (
          <div style={{ fontSize: 12, color: '#bbb' }}>
            <span style={{ marginRight: 4 }}>📝</span>暂无提示词
          </div>
        )}

        {item.judging_criteria?.trim() ? (
          <ExpandableText
            icon="📋"
            text={item.judging_criteria}
            collapsedLines={1}
            expanded={judgingExpanded}
            onToggle={() => setJudgingExpanded(!judgingExpanded)}
            textStyle={{ fontSize: 12, color: '#5a6068' }}
          />
        ) : null}

        <div style={{ marginTop: 'auto' }}>
          <AssetRow item={item} />
        </div>

        <div style={{ fontSize: 11, color: '#bbb', textAlign: 'right' }}>
          {formatRelativeTime(item.created_at)}
        </div>
      </div>

      {/* 右：Seedance 输出 + 评分 */}
      <OutputColumn item={item} />
    </div>
  )
}

// ----- 主组件 -----

export default function BenchmarkItemsPage() {
  const { message } = AntApp.useApp()
  const [items, setItems] = useState<VideoBenchmarkItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [filters, setFilters] = useState<Record<FilterKey, string | undefined>>({
    shot_type: undefined,
    task_type: undefined,
    question_type: undefined,
    scene: undefined,
    screen_size: undefined,
  })
  const [cascaderPath, setCascaderPath] = useState<string[] | undefined>(undefined)
  const [manualTag, setManualTag] = useState('')
  const [manualTagQuery, setManualTagQuery] = useState('')
  const [score, setScore] = useState<number | null | undefined>(undefined)
  const [statsGroups, setStatsGroups] = useState<StatsGroup[]>([])
  const [todayNew, setTodayNew] = useState(0)
  const cascaderOptions = useMemo(
    () => buildCascaderOptionsWithCounts(statsGroups),
    [statsGroups],
  )
  const totalCount = useMemo(
    () => statsGroups.reduce((sum, g) => sum + g.count, 0),
    [statsGroups],
  )
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<VideoBenchmarkItem | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1)
      setManualTagQuery(manualTag)
    }, 300)
    return () => clearTimeout(timer)
  }, [manualTag])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: VideoBenchmarkListParams = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        score,
        manual_tag: manualTagQuery.trim() || undefined,
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
  }, [filters, manualTagQuery, message, page, pageSize, score])

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
    setCascaderPath(undefined)
    setManualTag('')
    setManualTagQuery('')
    setScore(undefined)
    setPage(1)
  }

  const loadStats = useCallback(async () => {
    try {
      const { groups, today_new } = await videoBenchmarkApi.stats()
      setStatsGroups(groups)
      setTodayNew(today_new)
    } catch (e) {
      // 统计接口失败不阻塞主流程，Cascader 退回到 0 统计展示
      console.warn('failed to load stats', e)
    }
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  const onSaved = async () => {
    await load()
    await loadStats()
  }

  const onDeleted = async () => {
    await load()
    await loadStats()
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* 顶部筛选栏 */}
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
          <Cascader
            allowClear
            placeholder="镜头类型 / 题目类型"
            value={cascaderPath}
            options={cascaderOptions}
            changeOnSelect
            expandTrigger="hover"
            popupClassName="bench-cascader-popup"
            showSearch={{
              filter: (input, path) =>
                path.some((o) => (o.label as string).toLowerCase().includes(input.toLowerCase())),
            }}
            onChange={(value) => {
              const arr = (value ?? []) as string[]
              setCascaderPath(arr.length ? arr : undefined)
              setFilters((current) => ({
                ...current,
                shot_type: arr[0] || undefined,
                question_type: arr.length === 3 ? arr[2] : undefined,
              }))
              setPage(1)
            }}
            style={{ width: 260 }}
          />
          <Select
            allowClear
            placeholder={FIELD_LABELS.scene}
            value={filters.scene}
            options={SCENE_OPTIONS.map((v) => ({ value: v, label: v }))}
            onChange={(value) => {
              setFilters((current) => ({ ...current, scene: value || undefined }))
              setPage(1)
            }}
            style={{ width: 180 }}
          />
          <Select
            allowClear
            placeholder={FIELD_LABELS.screen_size}
            value={filters.screen_size}
            options={SCREEN_SIZE_OPTIONS.map((v) => ({ value: v, label: v }))}
            onChange={(value) => {
              setFilters((current) => ({ ...current, screen_size: value || undefined }))
              setPage(1)
            }}
            style={{ width: 140 }}
          />
          <Select
            allowClear
            placeholder={FIELD_LABELS.score}
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
            style={{ width: 120 }}
          />
          <Input
            allowClear
            placeholder="搜索测试点人工标注"
            value={manualTag}
            onChange={(e) => setManualTag(e.target.value)}
            style={{ width: 200 }}
          />
          <Button onClick={resetFilters}>重置筛选</Button>
        </Space>
        <div style={{ flex: 1, minWidth: 16 }} />
        <div style={{ fontSize: 13, color: '#5a6068', whiteSpace: 'nowrap' }}>
          共 <strong style={{ color: '#1f2328' }}>{totalCount}</strong> 题 · 今日新增{' '}
          <strong style={{ color: todayNew > 0 ? '#16a34a' : '#1f2328' }}>{todayNew}</strong>
        </div>
        <Button type="primary" onClick={openNew}>
          新建题目
        </Button>
      </div>

      {/* 卡片列表 */}
      <main
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: 16,
        }}
      >
        <Spin spinning={loading}>
          {items.length === 0 && !loading ? (
            <Empty description="没有符合条件的题目" style={{ padding: 48 }} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {items.map((item) => (
                <ItemCard
                  key={item.id}
                  item={item}
                  onClick={() => openEdit(item)}
                />
              ))}
            </div>
          )}

          {total > 0 && (
            <div
              style={{
                marginTop: 16,
                display: 'flex',
                justifyContent: 'flex-end',
              }}
            >
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                showSizeChanger
                pageSizeOptions={[10, 20, 50]}
                showTotal={(count) => `共 ${count} 条`}
                onChange={(nextPage, nextSize) => {
                  setPage(nextPage)
                  if (nextSize !== pageSize) {
                    setPageSize(nextSize)
                  }
                }}
              />
            </div>
          )}
        </Spin>
      </main>

      <BenchmarkItemDrawer
        open={drawerOpen}
        item={editing}
        onClose={() => setDrawerOpen(false)}
        onSaved={onSaved}
        onDeleted={onDeleted}
      />
    </div>
  )
}
