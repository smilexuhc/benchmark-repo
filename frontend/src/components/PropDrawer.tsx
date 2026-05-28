import { useEffect, useState } from 'react'
import {
  Drawer, Input, AutoComplete, Button, Image, Upload,
  Popconfirm, Tag, App as AntApp, Empty, Spin,
} from 'antd'
import type { Prop, PropInput } from '../types'
import { emptyProp } from '../types'
import { propApi, imageUrl, downloadImage } from '../api'
import type { DrawerProps } from './AssetLibrary'

const { TextArea } = Input

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 13, color: '#5a6068', marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}

export default function PropDrawer({
  open, item, options, onClose, onRefresh,
}: DrawerProps<Prop>) {
  const { message, modal } = AntApp.useApp()
  const [cur, setCur] = useState<Prop | null>(null)
  const [form, setForm] = useState<PropInput>(emptyProp)
  const [saving, setSaving] = useState(false)
  const [genPromptLoading, setGenPromptLoading] = useState(false)
  const [genImageLoading, setGenImageLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (!open) return
    setCur(item)
    setForm(item ? pickInput(item) : { ...emptyProp })
  }, [open, item])

  const set = (k: keyof PropInput, v: string) =>
    setForm((f) => ({ ...f, [k]: v }))

  const reloadCur = async (id: number) => {
    setCur(await propApi.get(id))
    onRefresh()
  }

  const save = async () => {
    if (!form.name.trim()) {
      message.warning('请填写名称')
      return
    }
    setSaving(true)
    try {
      const saved = cur
        ? await propApi.update(cur.id, form)
        : await propApi.create(form)
      setCur(saved)
      onRefresh()
      message.success(cur ? '已保存' : '道具已创建')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const del = () => {
    if (!cur) return
    modal.confirm({
      title: '删除该道具？',
      content: '道具及其图片将从列表中移除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await propApi.remove(cur.id)
        onRefresh()
        onClose()
        message.success('已删除')
      },
    })
  }

  const restore = async () => {
    if (!cur) return
    try {
      const saved = await propApi.restore(cur.id)
      setCur(saved)
      onRefresh()
      message.success('已恢复')
    } catch (e) {
      message.error((e as Error).message)
    }
  }

  const genPrompt = async () => {
    setGenPromptLoading(true)
    try {
      const { prompt } = await propApi.generatePrompt(form)
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
      await propApi.generateImage(cur.id, form.prompt)
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
      await propApi.uploadImage(cur.id, file)
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
    await propApi.deleteImage(imgId)
    await reloadCur(cur.id)
  }

  const setCover = async (imgId: number) => {
    if (!cur) return
    setCur(await propApi.setCover(cur.id, imgId))
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
      title={cur ? cur.name || '编辑道具' : '新建道具'}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>
            {cur && (
              cur.deleted_at ? (
                <Button type="primary" onClick={restore}>
                  恢复
                </Button>
              ) : (
                <Button danger onClick={del}>
                  删除
                </Button>
              )
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
      <div
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 16 }}
      >
        <Field label="名称">
          <Input
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="输入道具名称"
          />
        </Field>
        <Field label="类别">
          <AutoComplete
            style={{ width: '100%' }}
            value={form.category}
            onChange={(v) => set('category', v)}
            options={(options.category || []).map((v) => ({ value: v }))}
            filterOption={(input, opt) =>
              (opt?.value as string).toLowerCase().includes(input.toLowerCase())
            }
            placeholder="选择或输入类别"
            allowClear
          />
        </Field>
      </div>

      <Field label="自由描述（可选，用于 AI 写提示词）">
        <TextArea
          value={form.description}
          onChange={(e) => set('description', e.target.value)}
          autoSize={{ minRows: 2, maxRows: 5 }}
          placeholder="例：一个棕色真皮公文包，黄铜锁扣……写完点「AI 生成提示词」"
        />
      </Field>

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
        placeholder="可手动填写，或点「AI 生成提示词」。有自由描述时按描述生成，否则按名称 / 类别生成。"
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
            保存道具后即可生成 / 上传图片。
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
                              `${form.name || '道具'}-${idx + 1}`,
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

function pickInput(p: Prop): PropInput {
  return {
    name: p.name, category: p.category,
    prompt: p.prompt, description: p.description,
  }
}
