import { useState } from 'react'
import { Tag, Button, Image, Spin, Checkbox, App as AntApp } from 'antd'
import type { ReactNode } from 'react'
import type { AssetBase, CharImage } from '../types'
import { imageUrl, downloadImage } from '../api'
import LazyImage from './LazyImage'

interface Props {
  item: AssetBase
  info: ReactNode // 信息区内容（角色/场景各自渲染）
  downloadName: string
  generateImage: (id: number, prompt: string, setCover?: boolean) => Promise<CharImage>
  setCover: (id: number, imgId: number) => Promise<unknown>
  onEdit: () => void
  onRefresh: () => void | Promise<void>
  selectMode?: boolean
  selected?: boolean
  busy?: boolean
  onToggleSelect?: () => void
  renderExtra?: () => ReactNode // 可选的第 4 列（场景用：多视角）
}

export default function AssetCard({
  item, info, downloadName, generateImage, setCover,
  onEdit, onRefresh, selectMode = false, selected = false,
  busy = false, onToggleSelect, renderExtra,
}: Props) {
  const { message } = AntApp.useApp()
  const [generating, setGenerating] = useState(false)
  const loading = generating || busy

  const copyPrompt = () => {
    if (!item.prompt) return
    navigator.clipboard.writeText(item.prompt)
    message.success('提示词已复制')
  }

  const generate = async () => {
    if (!item.prompt.trim()) {
      message.warning('还没有提示词，请先点「编辑」生成')
      return
    }
    setGenerating(true)
    try {
      await generateImage(item.id, item.prompt, true)
      message.success('图片已生成')
      await onRefresh()
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setGenerating(false)
    }
  }

  const download = () => {
    if (item.cover_filename) downloadImage(item.cover_filename, downloadName)
  }

  const setCoverImg = async (imgId: number) => {
    try {
      await setCover(item.id, imgId)
      message.success('已设为默认展示图')
      await onRefresh()
    } catch (e) {
      message.error((e as Error).message)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        background: '#fff',
        border: `1px solid ${selected ? '#1f6feb' : '#e8e8e8'}`,
        borderRadius: 8,
        overflow: 'hidden',
        minHeight: 220,
      }}
    >
      {selectMode && (
        <div
          onClick={onToggleSelect}
          style={{
            width: 44,
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRight: '1px solid #f0f0f0',
            background: selected ? '#eef4ff' : '#fafbfc',
            cursor: 'pointer',
          }}
        >
          <Checkbox checked={selected} style={{ pointerEvents: 'none' }} />
        </div>
      )}

      {/* 信息 */}
      <div
        style={{
          width: 210,
          flexShrink: 0,
          padding: 16,
          borderRight: '1px solid #f0f0f0',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {info}
        <div style={{ flex: 1 }} />
        <Button size="small" onClick={onEdit} style={{ alignSelf: 'flex-start' }}>
          编辑
        </Button>
      </div>

      {/* 提示词 */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          padding: 16,
          borderRight: '1px solid #f0f0f0',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 8,
          }}
        >
          <span style={{ fontSize: 13, fontWeight: 600 }}>提示词</span>
          <Button
            type="link"
            size="small"
            disabled={!item.prompt}
            onClick={copyPrompt}
            style={{ padding: 0 }}
          >
            复制
          </Button>
        </div>
        {item.prompt ? (
          <div className="prompt-box" style={{ maxHeight: 168, flex: 1 }}>
            {item.prompt}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: '#bbb', paddingTop: 8 }}>
            暂无提示词，点「编辑」生成
          </div>
        )}
      </div>

      {/* 图片 */}
      <div
        style={{
          width: 380,
          flexShrink: 0,
          padding: 12,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#fafbfc',
        }}
      >
        {loading ? (
          <div style={{ textAlign: 'center', color: '#999' }}>
            <Spin />
            <div style={{ fontSize: 12, marginTop: 10 }}>生成中，约 1 分钟…</div>
          </div>
        ) : item.cover_filename ? (
          <>
            <Image.PreviewGroup
              items={item.images.map((img) => imageUrl(img.filename))}
              preview={{
                toolbarRender: (node, info2) => {
                  const img = item.images[info2.current]
                  if (!img) return node
                  const isCover = img.filename === item.cover_filename
                  return (
                    <div
                      style={{ display: 'flex', alignItems: 'center', gap: 16 }}
                    >
                      {node}
                      {isCover ? (
                        <Tag color="green" style={{ marginInlineEnd: 0 }}>
                          当前默认图
                        </Tag>
                      ) : (
                        <Button
                          size="small"
                          type="primary"
                          onClick={() => setCoverImg(img.id)}
                        >
                          设为默认图
                        </Button>
                      )}
                    </div>
                  )
                },
              }}
            >
              <LazyImage
                src={imageUrl(item.cover_filename)}
                style={{
                  maxHeight: 196,
                  maxWidth: 356,
                  objectFit: 'contain',
                  borderRadius: 4,
                }}
                placeholderStyle={{ width: 356, height: 196 }}
              />
            </Image.PreviewGroup>
            <div
              style={{
                marginTop: 6,
                display: 'flex',
                gap: 12,
                alignItems: 'center',
              }}
            >
              <Button
                type="link"
                size="small"
                style={{ padding: 0 }}
                onClick={generate}
              >
                重新生成
              </Button>
              <Button
                type="link"
                size="small"
                style={{ padding: 0 }}
                onClick={download}
              >
                下载原图
              </Button>
              {item.images.length > 1 && (
                <span style={{ fontSize: 11, color: '#9aa0a6' }}>
                  共 {item.images.length} 张 · 点图放大左右翻看
                </span>
              )}
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', color: '#bbb' }}>
            <div style={{ fontSize: 13, marginBottom: 10 }}>暂无图片</div>
            <Button size="small" type="primary" ghost onClick={generate}>
              生成图片
            </Button>
          </div>
        )}
      </div>

      {/* 第 4 列：多视角（仅场景） */}
      {renderExtra && (
        <div
          style={{
            width: 212,
            flexShrink: 0,
            padding: 12,
            borderLeft: '1px solid #f0f0f0',
            background: '#fafbfc',
          }}
        >
          {renderExtra()}
        </div>
      )}
    </div>
  )
}
