import { useEffect, useState } from 'react'
import {
  Drawer, Input, AutoComplete, Button, Image, Upload,
  Popconfirm, Tag, App as AntApp, Empty, Spin,
} from 'antd'
import type { Character, CharacterInput } from '../types'
import { FIELD_LABELS, emptyCharacter } from '../types'
import { characterApi, imageUrl, downloadImage } from '../api'
import type { DrawerProps } from './AssetLibrary'

const { TextArea } = Input
const SELECT_FIELDS: (keyof CharacterInput)[] = ['era', 'type', 'gender', 'age', 'genre']
const TEXT_FIELDS: { key: keyof CharacterInput; label: string }[] = [
  { key: 'persona', label: '人设/服装造型' },
  { key: 'body', label: '身材' },
  { key: 'features', label: '特征' },
]

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 13, color: '#5a6068', marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}

export default function CharacterDrawer({
  open, item, options, onClose, onRefresh,
}: DrawerProps<Character>) {
  const { message, modal } = AntApp.useApp()
  const [cur, setCur] = useState<Character | null>(null)
  const [form, setForm] = useState<CharacterInput>(emptyCharacter)
  const [saving, setSaving] = useState(false)
  const [genPromptLoading, setGenPromptLoading] = useState(false)
  const [genImageLoading, setGenImageLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [extractLoading, setExtractLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setCur(item)
    setForm(item ? pickInput(item) : { ...emptyCharacter })
  }, [open, item])

  const set = (k: keyof CharacterInput, v: string) =>
    setForm((f) => ({ ...f, [k]: v }))

  const reloadCur = async (id: number) => {
    setCur(await characterApi.get(id))
    onRefresh()
  }

  const save = async () => {
    if (!form.persona.trim()) {
      message.warning('请填写人设')
      return
    }
    setSaving(true)
    try {
      const saved = cur
        ? await characterApi.update(cur.id, form)
        : await characterApi.create(form)
      setCur(saved)
      onRefresh()
      message.success(cur ? '已保存' : '角色已创建')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const del = () => {
    if (!cur) return
    modal.confirm({
      title: '删除该角色？',
      content: '角色及其图片将从列表中移除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await characterApi.remove(cur.id)
        onRefresh()
        onClose()
        message.success('已删除')
      },
    })
  }

  const extractFields = async () => {
    if (!form.description.trim()) {
      message.warning('请先填写自由描述')
      return
    }
    setExtractLoading(true)
    try {
      const fields = await characterApi.extractFields(form.description)
      setForm((f) => ({ ...f, ...fields }))
      message.success('已根据描述填入字段，可手动调整')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setExtractLoading(false)
    }
  }

  const genPrompt = async () => {
    setGenPromptLoading(true)
    try {
      const { prompt } = await characterApi.generatePrompt(form)
      set('prompt', prompt)
      message.success('提示词已生成，可继续编辑')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setGenPromptLoading(false)
    }
  }

  const genImage = async () => {
    if (!cur) return
    if (!form.prompt.trim()) {
      message.warning('请先填写或生成提示词')
      return
    }
    setGenImageLoading(true)
    try {
      await characterApi.generateImage(cur.id, form.prompt)
      await reloadCur(cur.id)
      message.success('图片已生成')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setGenImageLoading(false)
    }
  }

  const upload = async (file: File) => {
    if (!cur) return
    setUploading(true)
    try {
      await characterApi.uploadImage(cur.id, file)
      await reloadCur(cur.id)
      message.success('已上传')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setUploading(false)
    }
  }

  const removeImage = async (imgId: number) => {
    if (!cur) return
    await characterApi.deleteImage(imgId)
    await reloadCur(cur.id)
  }

  const setCover = async (imgId: number) => {
    if (!cur) return
    setCur(await characterApi.setCover(cur.id, imgId))
    onRefresh()
  }

  const copyPrompt = () => {
    if (!form.prompt) return
    navigator.clipboard.writeText(form.prompt)
    message.success('已复制')
  }

  const dirty = cur ? JSON.stringify(pickInput(cur)) !== JSON.stringify(form) : true

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={760}
      title={cur ? cur.persona || '编辑角色' : '新建角色'}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>
            {cur && (
              <Button danger onClick={del}>
                删除
              </Button>
            )}
          </span>
          <span>
            <Button onClick={onClose} style={{ marginRight: 8 }}>
              关闭
            </Button>
            <Button type="primary" loading={saving} onClick={save}>
              {cur ? '保存' : '创建'}
            </Button>
          </span>
        </div>
      }
    >
      {/* 自由描述（置顶，可 AI 解析填字段） */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 6,
        }}
      >
        <span style={{ fontSize: 13, color: '#5a6068' }}>
          自由描述（用一段话描述角色）
        </span>
        <Button
          type="link"
          size="small"
          loading={extractLoading}
          onClick={extractFields}
        >
          AI 填入字段
        </Button>
      </div>
      <TextArea
        value={form.description}
        onChange={(e) => set('description', e.target.value)}
        autoSize={{ minRows: 3, maxRows: 6 }}
        placeholder="例：一个高冷的禁欲系霸总，西装、冷脸……写完点「AI 填入字段」自动填下方各项"
      />
      <div style={{ height: 16 }} />

      {/* 结构化字段 */}
      <div
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 16 }}
      >
        {SELECT_FIELDS.map((key) => (
          <Field key={key} label={FIELD_LABELS[key]}>
            <AutoComplete
              style={{ width: '100%' }}
              value={form[key]}
              onChange={(v) => set(key, v)}
              options={(options[key] || []).map((v) => ({ value: v }))}
              filterOption={(input, opt) =>
                (opt?.value as string).toLowerCase().includes(input.toLowerCase())
              }
              placeholder={`选择或输入${FIELD_LABELS[key]}`}
              allowClear
            />
          </Field>
        ))}
      </div>
      {TEXT_FIELDS.map(({ key, label }) => (
        <Field key={key} label={label}>
          <Input
            value={form[key]}
            onChange={(e) => set(key, e.target.value)}
            placeholder={`输入${label}`}
          />
        </Field>
      ))}

      {/* 提示词 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 6,
        }}
      >
        <span style={{ fontSize: 13, color: '#5a6068' }}>英文生成提示词</span>
        <span>
          <Button
            type="link"
            size="small"
            loading={genPromptLoading}
            onClick={genPrompt}
          >
            AI 生成提示词
          </Button>
          <Button type="link" size="small" disabled={!form.prompt} onClick={copyPrompt}>
            复制
          </Button>
        </span>
      </div>
      <TextArea
        value={form.prompt}
        onChange={(e) => set('prompt', e.target.value)}
        autoSize={{ minRows: 4, maxRows: 12 }}
        placeholder="可手动填写，或点「AI 生成提示词」。有自由描述时按描述生成，否则按上方字段生成。"
        style={{ fontFamily: 'SF Mono, Menlo, monospace', fontSize: 12 }}
      />

      {/* 图集 */}
      <div style={{ marginTop: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 10,
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 600 }}>图集</span>
          <span>
            <Button
              type="primary"
              size="small"
              loading={genImageLoading}
              disabled={!cur}
              onClick={genImage}
              style={{ marginRight: 8 }}
            >
              生成图片
            </Button>
            <Upload
              showUploadList={false}
              accept="image/*"
              beforeUpload={(file) => {
                upload(file as unknown as File)
                return false
              }}
            >
              <Button size="small" loading={uploading} disabled={!cur}>
                上传图片
              </Button>
            </Upload>
          </span>
        </div>

        {!cur && (
          <div style={{ fontSize: 12, color: '#bbb' }}>
            保存角色后即可生成 / 上传图片。
          </div>
        )}

        {cur && cur.images.length === 0 && !genImageLoading && (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="还没有图片"
            style={{ margin: '12px 0' }}
          />
        )}

        {cur && (genImageLoading || cur.images.length > 0) && (
          <Spin spinning={genImageLoading} tip="生成中…">
            <Image.PreviewGroup>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                {cur.images.map((img, idx) => {
                  const isCover = img.id === cur.cover_image_id
                  return (
                    <div
                      key={img.id}
                      style={{
                        width: 332,
                        border: isCover
                          ? '2px solid #1f6feb'
                          : '1px solid #e8e8e8',
                        borderRadius: 6,
                        overflow: 'hidden',
                      }}
                    >
                      <Image
                        src={imageUrl(img.filename)}
                        style={{
                          width: 332,
                          height: 200,
                          objectFit: 'contain',
                          background: '#fafbfc',
                        }}
                      />
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '6px 8px',
                        }}
                      >
                        {isCover ? (
                          <Tag color="blue" style={{ marginInlineEnd: 0 }}>
                            封面
                          </Tag>
                        ) : (
                          <Button
                            type="link"
                            size="small"
                            style={{ padding: 0 }}
                            onClick={() => setCover(img.id)}
                          >
                            设为封面
                          </Button>
                        )}
                        <span style={{ fontSize: 11, color: '#bbb' }}>
                          {img.source === 'generated' ? 'AI 生成' : '上传'}
                        </span>
                        <Button
                          type="link"
                          size="small"
                          style={{ padding: 0 }}
                          onClick={() =>
                            downloadImage(
                              img.filename,
                              `${form.persona || '角色'}-${idx + 1}`,
                            )
                          }
                        >
                          下载
                        </Button>
                        <Popconfirm
                          title="删除这张图片？"
                          okText="删除"
                          cancelText="取消"
                          onConfirm={() => removeImage(img.id)}
                        >
                          <Button
                            type="link"
                            size="small"
                            danger
                            style={{ padding: 0 }}
                          >
                            删除
                          </Button>
                        </Popconfirm>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Image.PreviewGroup>
          </Spin>
        )}
      </div>

      {dirty && cur && (
        <div style={{ marginTop: 16, fontSize: 12, color: '#e08600' }}>
          字段有改动尚未保存，记得点「保存」。
        </div>
      )}
    </Drawer>
  )
}

function pickInput(c: Character): CharacterInput {
  return {
    era: c.era, type: c.type, gender: c.gender, age: c.age,
    persona: c.persona, body: c.body, features: c.features,
    genre: c.genre, prompt: c.prompt, description: c.description,
  }
}
