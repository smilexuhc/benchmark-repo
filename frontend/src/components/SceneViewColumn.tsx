import { useState } from 'react'
import { Button, Image, Spin, App as AntApp } from 'antd'
import type { Scene, SceneViewKind } from '../types'
import { sceneApi, imageUrl, downloadImage } from '../api'
import LazyImage from './LazyImage'

const VIEWS: { kind: SceneViewKind; label: string }[] = [
  { kind: 'reverse', label: '正反打' },
  { kind: 'multiview', label: '4视图' },
]

interface Props {
  scene: Scene
  onRefresh: () => void | Promise<void>
}

export default function SceneViewColumn({ scene, onRefresh }: Props) {
  const { message } = AntApp.useApp()
  const [busy, setBusy] = useState<SceneViewKind | null>(null)
  const hasCover = !!scene.cover_filename

  const gen = async (kind: SceneViewKind) => {
    setBusy(kind)
    try {
      await sceneApi.generateView(scene.id, kind)
      message.success('已生成')
      await onRefresh()
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 13, fontWeight: 600 }}>多视角</div>

      <div
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}
      >
        <Image.PreviewGroup>
          {VIEWS.map(({ kind, label }) => {
            const img = scene.views?.[kind] || null
            const loading = busy === kind
            return (
              <div
                key={kind}
                style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
              >
                <div style={{ fontSize: 12, color: '#5a6068' }}>{label}</div>
                {loading ? (
                  <div
                    style={{
                      height: 96,
                      borderRadius: 4,
                      background: '#f4f5f7',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#999',
                    }}
                  >
                    <Spin size="small" />
                    <div style={{ fontSize: 10, marginTop: 4 }}>约 2 分钟…</div>
                  </div>
                ) : img ? (
                  <>
                    <LazyImage
                      src={imageUrl(img.filename)}
                      style={{
                        width: '100%',
                        height: 96,
                        objectFit: 'contain',
                        borderRadius: 4,
                        background: '#f4f5f7',
                      }}
                      placeholderStyle={{ width: '100%', height: 96 }}
                    />
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <Button
                        type="link"
                        size="small"
                        style={{ padding: 0, height: 'auto', fontSize: 12 }}
                        onClick={() =>
                          downloadImage(
                            img.filename,
                            `${scene.name || '场景'}-${label}`,
                          )
                        }
                      >
                        下载
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        style={{ padding: 0, height: 'auto', fontSize: 12 }}
                        disabled={!hasCover || !!busy}
                        onClick={() => gen(kind)}
                      >
                        重新生成
                      </Button>
                    </div>
                  </>
                ) : (
                  <Button
                    size="small"
                    block
                    style={{ height: 96, fontSize: 12 }}
                    disabled={!hasCover || !!busy}
                    onClick={() => gen(kind)}
                  >
                    生成
                  </Button>
                )}
              </div>
            )
          })}
        </Image.PreviewGroup>
      </div>

      {!hasCover && (
        <div style={{ fontSize: 11, color: '#bbb' }}>
          需先有场景图,才能生成多视角
        </div>
      )}
    </div>
  )
}
