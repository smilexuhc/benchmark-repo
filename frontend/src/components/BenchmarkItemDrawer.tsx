import { useEffect, useState } from 'react'
import {
  App as AntApp,
  Button,
  Cascader,
  Drawer,
  Image,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Table,
  Upload,
} from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import type {
  MediaAsset,
  MediaAssetListParams,
  VideoBenchmarkItem,
  VideoBenchmarkItemInput,
} from '../types'
import { emptyVideoBenchmarkItem, FIELD_LABELS } from '../types'
import { characterApi, imageUrl, mediaAssetsApi, sceneApi, videoBenchmarkApi } from '../api'
import { QUESTION_TYPE_OPTIONS, findCascaderValue } from '../data/questionTypeOptions'

const { TextArea } = Input

interface Props {
  open: boolean
  item: VideoBenchmarkItem | null
  onClose: () => void
  onSaved: (item: VideoBenchmarkItem) => void | Promise<void>
  onDeleted?: (id: number) => void | Promise<void>
}

// 镜头类型和题目类型合并到 Cascader 单独渲染，不走通用 BASIC_FIELDS 流程
// task_type 在编辑页隐藏（保留数据库字段）
const BASIC_FIELDS: (keyof VideoBenchmarkItemInput)[] = [
  'scene',
  'screen_size',
]

const ENUM_OPTIONS: Partial<Record<keyof VideoBenchmarkItemInput, string[]>> = {
  screen_size: ['16:9', '9:16', '2.39:1'],
  scene: ['电影 / 预告片', '短剧 / 剧情片段', '动画 / 风格化内容'],
}

// 文字提示词放在素材上方，列表卡片顺序保持一致
const TOP_LONG_FIELDS: (keyof VideoBenchmarkItemInput)[] = [
  'text_prompt',
]
const LONG_FIELDS: (keyof VideoBenchmarkItemInput)[] = [
  'judging_criteria',
]

const MEDIA_FIELDS: {
  idKey: keyof VideoBenchmarkItemInput
  idsKey: keyof VideoBenchmarkItemInput
  snapshotKey: keyof VideoBenchmarkItemInput
  responseKey: keyof VideoBenchmarkItem
  responseListKey: keyof VideoBenchmarkItem
  label: string
  params: MediaAssetListParams
}[] = [
  {
    idKey: 'character_image_id',
    idsKey: 'character_image_ids',
    snapshotKey: 'character_image_asset',
    responseKey: 'character_image',
    responseListKey: 'character_image_media',
    label: FIELD_LABELS.character_image_id,
    params: { media_type: 'image', asset_kind: 'character' },
  },
  {
    idKey: 'scene_image_id',
    idsKey: 'scene_image_ids',
    snapshotKey: 'scene_image_asset',
    responseKey: 'scene_image',
    responseListKey: 'scene_image_media',
    label: FIELD_LABELS.scene_image_id,
    params: { media_type: 'image', asset_kind: 'scene' },
  },
  {
    idKey: 'prop_image_id',
    idsKey: 'prop_image_ids',
    snapshotKey: 'prop_image_asset',
    responseKey: 'prop_image',
    responseListKey: 'prop_image_media',
    label: FIELD_LABELS.prop_image_id,
    params: { media_type: 'image', asset_kind: 'prop' },
  },
  {
    idKey: 'audio_input_id',
    idsKey: 'audio_input_media_ids',
    snapshotKey: 'audio_input',
    responseKey: 'audio_input_media',
    responseListKey: 'audio_input_media_items',
    label: FIELD_LABELS.audio_input_id,
    params: { media_type: 'audio', asset_kind: 'audio' },
  },
  {
    idKey: 'video_input_id',
    idsKey: 'video_input_ids',
    snapshotKey: 'video_input',
    responseKey: 'video_input_media',
    responseListKey: 'video_input_media_items',
    label: FIELD_LABELS.video_input_id,
    params: { media_type: 'video', asset_kind: 'video' },
  },
  {
    idKey: 'video_output_id',
    idsKey: 'video_output_ids',
    snapshotKey: 'video_output',
    responseKey: 'video_output_media',
    responseListKey: 'video_output_media_items',
    label: FIELD_LABELS.video_output_id,
    params: { media_type: 'video', asset_kind: 'video' },
  },
]

function pickInput(item: VideoBenchmarkItem): VideoBenchmarkItemInput {
  return {
    shot_type: item.shot_type,
    task_type: item.task_type,
    question_type: item.question_type,
    manual_tag: item.manual_tag ?? '',
    scene: item.scene,
    screen_size: item.screen_size,
    character_image_asset: item.character_image_asset,
    scene_image_asset: item.scene_image_asset,
    prop_image_asset: item.prop_image_asset,
    audio_input: item.audio_input,
    video_input: item.video_input,
    text_prompt: item.text_prompt,
    judging_criteria: item.judging_criteria,
    video_output: item.video_output,
    score: item.score,
    character_image_id: item.character_image_id,
    scene_image_id: item.scene_image_id,
    prop_image_id: item.prop_image_id,
    audio_input_id: item.audio_input_id,
    video_input_id: item.video_input_id,
    video_output_id: item.video_output_id,
    character_image_ids: item.character_image_ids,
    scene_image_ids: item.scene_image_ids,
    prop_image_ids: item.prop_image_ids,
    audio_input_media_ids: item.audio_input_media_ids,
    video_input_ids: item.video_input_ids,
    video_output_ids: item.video_output_ids,
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 13, color: '#5a6068', marginBottom: 6 }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function mediaLabel(media: MediaAsset) {
  return media.title || media.object_key.split('/').pop() || media.object_key
}

function mediaMeta(media: MediaAsset) {
  const name = media.object_key.split('/').pop() || media.object_key
  return [media.subtitle, `#${media.id}`, name].filter(Boolean).join(' · ')
}

function MediaThumb({ media }: { media: MediaAsset }) {
  if (media.media_type === 'image') {
    return <Image src={imageUrl(media.object_key)} width={80} height={52} style={{ objectFit: 'cover', background: '#f4f5f7', borderRadius: 4 }} />
  }
  if (media.media_type === 'video') {
    return (
      <video
        src={imageUrl(media.object_key)}
        width={80}
        height={52}
        muted
        playsInline
        preload="metadata"
        style={{ objectFit: 'cover', background: '#f4f5f7', borderRadius: 4, display: 'block' }}
      />
    )
  }
  return (
    <div style={{ width: 80, height: 52, borderRadius: 4, background: '#f4f5f7', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7280', fontSize: 12 }}>
      AUDIO
    </div>
  )
}

const FILTER_FIELDS_BY_KIND: Record<string, { field: string; label: string }[]> = {
  character: [
    { field: 'era', label: '时代' },
    { field: 'type', label: '类型' },
    { field: 'gender', label: '性别' },
    { field: 'age', label: '年龄段' },
    { field: 'genre', label: '常见题材' },
  ],
  scene: [
    { field: 'era', label: '时代' },
    { field: 'scene_type', label: '场景类型' },
    { field: 'genre', label: '常见题材' },
    { field: 'mood', label: '氛围时段' },
  ],
}

function MediaPicker({
  label,
  params,
  selected,
  onChange,
}: {
  label: string
  params: MediaAssetListParams
  selected: MediaAsset[]
  onChange: (media: MediaAsset[]) => void
}) {
  const { message } = AntApp.useApp()
  const [open, setOpen] = useState(false)
  const [options, setOptions] = useState<MediaAsset[]>([])
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [filterValues, setFilterValues] = useState<Record<string, string | undefined>>({})
  const [filterOptions, setFilterOptions] = useState<Record<string, string[]>>({})

  const filterFields = FILTER_FIELDS_BY_KIND[params.asset_kind || ''] || []

  const dedup = params.asset_kind === 'character' || params.asset_kind === 'scene'

  const load = async (
    nextPage = page,
    q = query,
    filters: Record<string, string | undefined> = filterValues,
  ) => {
    setLoading(true)
    try {
      const data = await mediaAssetsApi.list({
        ...params,
        ...filters,
        q: q.trim() || undefined,
        limit: 20,
        offset: (nextPage - 1) * 20,
        dedup_by_asset: dedup,
      })
      setOptions(data.items)
      setTotal(data.total)
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    load(1, query, filterValues)
    if (filterFields.length === 0) {
      setFilterOptions({})
      return
    }
    const fetcher = params.asset_kind === 'scene' ? sceneApi.options : characterApi.options
    fetcher()
      .then((opts) => setFilterOptions(opts as Record<string, string[]>))
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, params.asset_kind, params.media_type])

  const columns: ColumnsType<MediaAsset> = [
    {
      title: '预览',
      dataIndex: 'object_key',
      width: 104,
      render: (_, media) => <MediaThumb media={media} />,
    },
    {
      title: '素材',
      dataIndex: 'title',
      render: (_, media) => (
        <div>
          <div style={{ fontWeight: 600 }}>{mediaLabel(media)}</div>
          <div style={{ fontSize: 12, color: '#8a8f99' }}>{mediaMeta(media)}</div>
        </div>
      ),
    },
  ]

  const pagination: TablePaginationConfig = {
    current: page,
    pageSize: 20,
    total,
    showSizeChanger: false,
  }

  const uploadFiles = async (files: File[]) => {
    if (!files.length) return
    setUploading(true)
    try {
      const uploadedItems: MediaAsset[] = []
      for (const file of files) {
        uploadedItems.push(await mediaAssetsApi.upload(params, file))
      }
      setOptions((current) => {
        const uploadedIds = new Set(uploadedItems.map((media) => media.id))
        return [...uploadedItems, ...current.filter((media) => !uploadedIds.has(media.id))]
      })
      const selectedMap = new Map<number, MediaAsset>()
      selected.forEach((media) => selectedMap.set(media.id, media))
      uploadedItems.forEach((media) => selectedMap.set(media.id, media))
      onChange(Array.from(selectedMap.values()))
      message.success(`已上传并选中 ${uploadedItems.length} 个素材`)
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <Field label={label}>
      <Space style={{ marginBottom: 8 }} wrap>
        <Button onClick={() => setOpen(true)}>选择素材</Button>
        <Upload
          multiple
          showUploadList={false}
          accept={params.media_type === 'video' ? 'video/*' : params.media_type === 'audio' ? 'audio/*' : 'image/*'}
          beforeUpload={(file, fileList) => {
            if (file.uid === fileList[fileList.length - 1]?.uid) {
              uploadFiles(fileList as unknown as File[])
            }
            return false
          }}
        >
          <Button loading={uploading}>上传素材</Button>
        </Upload>
      </Space>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {selected.length === 0 && <span style={{ color: '#b8bdc4' }}>未选择</span>}
        {selected.map((media) => (
          <div key={media.id} style={{ width: 126 }}>
            <MediaThumb media={media} />
            <div style={{ marginTop: 4, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {mediaLabel(media)}
            </div>
          </div>
        ))}
      </div>
      <Modal
        open={open}
        title={`选择${label}`}
        width={920}
        onCancel={() => setOpen(false)}
        onOk={() => setOpen(false)}
        okText="完成"
        cancelText="关闭"
      >
        {filterFields.length > 0 && (
          <Space size={8} wrap style={{ marginBottom: 8 }}>
            {filterFields.map(({ field, label: lbl }) => (
              <Select
                key={field}
                allowClear
                placeholder={lbl}
                value={filterValues[field]}
                options={(filterOptions[field] || []).map((v) => ({ value: v, label: v }))}
                onChange={(value) => {
                  const next = { ...filterValues, [field]: value || undefined }
                  setFilterValues(next)
                  setPage(1)
                  load(1, query, next)
                }}
                style={{ width: 140 }}
              />
            ))}
          </Space>
        )}
        <Input.Search
          allowClear
          placeholder={`搜索${label}`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onSearch={(value) => {
            setPage(1)
            load(1, value, filterValues)
          }}
          style={{ marginBottom: 12 }}
        />
        <Table<MediaAsset>
          rowKey={dedup ? 'asset_id' : 'id'}
          loading={loading}
          dataSource={options}
          columns={columns}
          pagination={pagination}
          rowSelection={{
            // 去重模式下用 asset_id 匹配：旧数据里存的可能是非封面 image_id，
            // 仍能让对应角色行显示为已选；新点击会把 selected 替换为封面 image
            selectedRowKeys: selected.map((media) => dedup ? media.asset_id : media.id),
            preserveSelectedRowKeys: true,
            onChange: (_, rows) => onChange(rows),
          }}
          scroll={{ y: 480 }}
          onChange={(nextPagination) => {
            const nextPage = nextPagination.current || 1
            setPage(nextPage)
            load(nextPage, query, filterValues)
          }}
        />
      </Modal>
    </Field>
  )
}

export default function BenchmarkItemDrawer({
  open, item, onClose, onSaved, onDeleted,
}: Props) {
  const { message } = AntApp.useApp()
  const [form, setForm] = useState<VideoBenchmarkItemInput>(emptyVideoBenchmarkItem)
  const [selectedMedia, setSelectedMedia] = useState<Record<string, MediaAsset[]>>({})
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!open) return
    setForm(item ? pickInput(item) : { ...emptyVideoBenchmarkItem })
    setSelectedMedia({
      character_image_ids: item?.character_image_media || [],
      scene_image_ids: item?.scene_image_media || [],
      prop_image_ids: item?.prop_image_media || [],
      audio_input_media_ids: item?.audio_input_media_items || [],
      video_input_ids: item?.video_input_media_items || [],
      video_output_ids: item?.video_output_media_items || [],
    })
  }, [open, item])

  const set = <K extends keyof VideoBenchmarkItemInput>(
    key: K,
    value: VideoBenchmarkItemInput[K],
  ) => setForm((current) => ({ ...current, [key]: value }))

  const save = async () => {
    setSaving(true)
    try {
      const saved = item
        ? await videoBenchmarkApi.update(item.id, form)
        : await videoBenchmarkApi.create(form)
      await onSaved(saved)
      message.success(item ? '题目已保存' : '题目已创建')
      onClose()
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!item) return
    setDeleting(true)
    try {
      await videoBenchmarkApi.remove(item.id)
      message.success('题目已删除')
      await onDeleted?.(item.id)
      onClose()
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setDeleting(false)
    }
  }

  const setMediaList = (
    idKey: keyof VideoBenchmarkItemInput,
    idsKey: keyof VideoBenchmarkItemInput,
    snapshotKey: keyof VideoBenchmarkItemInput,
    media: MediaAsset[],
  ) => {
    set(idKey, (media[0]?.id ?? null) as VideoBenchmarkItemInput[typeof idKey])
    set(idsKey, media.map((item) => item.id) as VideoBenchmarkItemInput[typeof idsKey])
    set(snapshotKey, media.map((item) => item.object_key).join('\n') as VideoBenchmarkItemInput[typeof snapshotKey])
    setSelectedMedia((current) => ({ ...current, [idsKey]: media }))
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={760}
      title={item ? `编辑题目 #${item.id}` : '新建题目'}
      footer={
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={onClose}>关闭</Button>
          <Button type="primary" loading={saving} onClick={save}>
            {item ? '保存' : '创建'}
          </Button>
        </div>
      }
    >
      <div
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 16 }}
      >
        <div style={{ gridColumn: '1 / -1' }}>
          <Field label="镜头类型 / 题目类型">
            <Cascader
              value={findCascaderValue(form.shot_type, form.question_type)}
              onChange={(value) => {
                const [l1 = '', , l3 = ''] = (value ?? []) as string[]
                set('shot_type', l1)
                set('question_type', l3)
              }}
              options={QUESTION_TYPE_OPTIONS}
              placeholder="依次选择 镜头类型 → 能力点 → 题型"
              showSearch={{ filter: (input, path) => path.some((o) => (o.label as string).toLowerCase().includes(input.toLowerCase())) }}
              changeOnSelect={false}
              expandTrigger="hover"
              popupClassName="bench-cascader-popup"
              allowClear
              style={{ width: '100%' }}
            />
          </Field>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <Field label={FIELD_LABELS.manual_tag}>
            <Input
              value={form.manual_tag}
              onChange={(e) => set('manual_tag', e.target.value)}
              placeholder="对该题目的人工补充描述，例如：动作断层跳变 （动作中途突然跳转，无过渡衔接，前后姿态割裂）"
              allowClear
            />
          </Field>
        </div>
        {BASIC_FIELDS.map((key) => {
          const enumOptions = ENUM_OPTIONS[key]
          return (
            <Field key={key} label={FIELD_LABELS[key]}>
              {enumOptions ? (
                <Select
                  value={(form[key] as string) || undefined}
                  onChange={(value) => set(key, (value ?? '') as VideoBenchmarkItemInput[typeof key])}
                  options={enumOptions.map((v) => ({ value: v, label: v }))}
                  placeholder={`选择${FIELD_LABELS[key]}`}
                  allowClear
                  style={{ width: '100%' }}
                />
              ) : (
                <Input
                  value={form[key] as string}
                  onChange={(e) => set(key, e.target.value)}
                  placeholder={`输入${FIELD_LABELS[key]}`}
                  allowClear
                />
              )}
            </Field>
          )
        })}
      </div>

      {TOP_LONG_FIELDS.map((key) => (
        <Field key={key} label={FIELD_LABELS[key]}>
          <TextArea
            value={form[key] as string}
            onChange={(e) => set(key, e.target.value)}
            autoSize={{ minRows: 4, maxRows: 8 }}
            placeholder={`输入${FIELD_LABELS[key]}，可填写 URL、object key、文件名或备注`}
          />
        </Field>
      ))}

      {MEDIA_FIELDS.map((field) => (
        <MediaPicker
          key={field.idsKey}
          label={field.label}
          params={field.params}
          selected={selectedMedia[field.idsKey] || []}
          onChange={(media) => setMediaList(field.idKey, field.idsKey, field.snapshotKey, media)}
        />
      ))}

      <Field label={FIELD_LABELS.score}>
        <Segmented
          value={form.score ?? 'unscored'}
          onChange={(value) => set('score', value === 'unscored' ? null : (value as number))}
          options={[
            { label: '未评分', value: 'unscored' },
            { label: '0', value: 0 },
            { label: '1', value: 1 },
            { label: '2', value: 2 },
            { label: '3', value: 3 },
            { label: '4', value: 4 },
            { label: '5', value: 5 },
          ]}
        />
      </Field>

      {LONG_FIELDS.map((key) => (
        <Field key={key} label={FIELD_LABELS[key]}>
          <TextArea
            value={form[key] as string}
            onChange={(e) => set(key, e.target.value)}
            autoSize={{ minRows: 4, maxRows: 8 }}
            placeholder={`输入${FIELD_LABELS[key]}，可填写 URL、object key、文件名或备注`}
          />
        </Field>
      ))}

      {item && (
        <div
          style={{
            marginTop: 32,
            paddingTop: 16,
            borderTop: '1px dashed #e8e8e8',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <Popconfirm
            title="删除题目"
            description={`确定删除题目 #${item.id}? 删除后可在数据库恢复。`}
            okText="删除"
            okButtonProps={{ danger: true }}
            cancelText="取消"
            onConfirm={handleDelete}
          >
            <Button danger loading={deleting}>
              删除题目
            </Button>
          </Popconfirm>
        </div>
      )}
    </Drawer>
  )
}
