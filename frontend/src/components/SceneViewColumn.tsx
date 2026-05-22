import { useState } from 'react'
import { Button, Image, Spin, App as AntApp } from 'antd'
import type { Scene, SceneViewKind } from '../types'
import { sceneApi, imageUrl, downloadImage } from '../api'

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ fontSize: 13, fontWeight: 600 }}>多视角</div>

      {VIEWS.map(({ kind, label }) => {
        const img = scene.views?.[kind] || null
        const loading = busy === kind
        return (
          <div key={kind}>
            <div style={{ fontSize: 12, color: '#5a6068', marginBottom: 4 }}>
              {label}
            </div>
            {loading ? (
              <div
                style={{ textAlign: 'center', padding: '16px 0', color: '#999' }}
              >
                <Spin size="small" />
                <div style={{ fontSize: 11, marginTop: 6 }}>生成中，约 2 分钟…</div>
              </div>
            ) : img ? (
              <>
                <Image
                  src={imageUrl(img.filename)}
                  style={{ width: '100%', borderRadius: 4 }}
                />
                <div style={{ marginTop: 4, display: 'flex', gap: 10 }}>
                  <Button
                    type="link"
                    size="small"
                    style={{ padding: 0 }}
                    onClick={() =>
                      downloadImage(img.filename, `${scene.name || '场景'}-${label}`)
                    }
                  >
                    下载
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    style={{ padding: 0 }}
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
                disabled={!hasCover || !!busy}
                onClick={() => gen(kind)}
              >
                生成{label}
              </Button>
            )}
          </div>
        )
      })}

      {!hasCover && (
        <div style={{ fontSize: 11, color: '#bbb' }}>
          需先有场景图,才能生成多视角
        </div>
      )}
    </div>
  )
}
